"""Evaluate a fixed set of pilot-area journeys against one local route snapshot."""

from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.routing.run import compare_points, load_routing_snapshot


REQUIRED_COLUMNS = {
    "journey_id",
    "journey_type",
    "origin_lon",
    "origin_lat",
    "destination_lon",
    "destination_lat",
}


def load_journeys(path: Path) -> pd.DataFrame:
    """Load and validate the deliberately fixed 20-30 journey evaluation set."""
    journeys = pd.read_csv(path)
    missing = REQUIRED_COLUMNS.difference(journeys.columns)
    if missing:
        raise ValueError(f"Journey file is missing required columns: {', '.join(sorted(missing))}")
    if not 20 <= len(journeys) <= 30:
        raise ValueError("Evaluation needs 20-30 journeys so its scope matches the roadmap")
    if journeys["journey_id"].duplicated().any():
        raise ValueError("Each evaluation journey_id must be unique")
    return journeys


def _metric(route: Any, name: str) -> float | None:
    value = getattr(route.metrics, name)
    return None if value is None else float(value)


def record_comparison(
    journey: dict[str, Any], comparison: Any, runtime_ms: float
) -> dict[str, Any]:
    """Flatten one route comparison while retaining valid no-alternative outcomes."""
    shortest = comparison.shortest
    alternative = comparison.lighting_aware
    record: dict[str, Any] = {
        **journey,
        "status": "completed",
        "error": None,
        "runtime_ms": round(runtime_ms, 2),
        "shortest_distance_m": _metric(shortest, "distance_m"),
        "shortest_estimated_minutes": _metric(shortest, "estimated_minutes"),
        "shortest_mapped_light_coverage_pct": _metric(shortest, "mapped_light_coverage_pct"),
        "shortest_mean_nearest_transit_stop_m": _metric(shortest, "mean_nearest_transit_stop_m"),
        "alternative_available": alternative is not None,
        "alternative_unavailable_reason": comparison.alternative_unavailable_reason,
    }
    if alternative is None:
        record.update(
            {
                "lighting_aware_distance_m": None,
                "lighting_aware_estimated_minutes": None,
                "lighting_aware_mapped_light_coverage_pct": None,
                "lighting_aware_mean_nearest_transit_stop_m": None,
                "extra_distance_m": None,
                "extra_distance_pct": None,
                "mapped_light_coverage_change_pp": None,
            }
        )
        return record

    extra_distance_m = alternative.metrics.distance_m - shortest.metrics.distance_m
    baseline_coverage = shortest.metrics.mapped_light_coverage_pct
    alternative_coverage = alternative.metrics.mapped_light_coverage_pct
    record.update(
        {
            "lighting_aware_distance_m": _metric(alternative, "distance_m"),
            "lighting_aware_estimated_minutes": _metric(alternative, "estimated_minutes"),
            "lighting_aware_mapped_light_coverage_pct": _metric(
                alternative, "mapped_light_coverage_pct"
            ),
            "lighting_aware_mean_nearest_transit_stop_m": _metric(
                alternative, "mean_nearest_transit_stop_m"
            ),
            "extra_distance_m": round(extra_distance_m, 2),
            "extra_distance_pct": round(extra_distance_m / shortest.metrics.distance_m * 100, 2),
            "mapped_light_coverage_change_pp": (
                round(alternative_coverage - baseline_coverage, 2)
                if baseline_coverage is not None and alternative_coverage is not None
                else None
            ),
        }
    )
    return record


def _distribution(values: pd.Series) -> dict[str, float | None]:
    cleaned = pd.to_numeric(values, errors="coerce").dropna()
    if cleaned.empty:
        return {"count": 0, "min": None, "p25": None, "median": None, "p75": None, "max": None}
    return {
        "count": int(len(cleaned)),
        "min": round(float(cleaned.min()), 2),
        "p25": round(float(cleaned.quantile(0.25)), 2),
        "median": round(float(cleaned.median()), 2),
        "p75": round(float(cleaned.quantile(0.75)), 2),
        "max": round(float(cleaned.max()), 2),
    }


def build_summary(results: pd.DataFrame, settings: dict[str, float]) -> dict[str, Any]:
    """Summarise outcomes without treating an unavailable alternative as an error."""
    completed = results.loc[results["status"] == "completed"]
    # Error rows omit alternative_available, which can make pandas infer an
    # object column. Convert explicitly so boolean negation never becomes the
    # integer bitwise operation (~True == -2).
    alternative_available = completed["alternative_available"].fillna(False).astype(bool)
    alternatives = completed.loc[alternative_available]
    unavailable = completed.loc[
        ~alternative_available, "alternative_unavailable_reason"
    ]
    reasons = {str(reason): int(count) for reason, count in Counter(unavailable.dropna()).items()}
    return {
        "created_utc": datetime.now(UTC).isoformat(),
        "routing_settings": settings,
        "journeys_requested": int(len(results)),
        "journeys_completed": int(len(completed)),
        "journey_errors": int(len(results) - len(completed)),
        "distinct_alternatives": int(len(alternatives)),
        "distinct_alternative_rate_pct": round(
            len(alternatives) / len(completed) * 100, 2
        ) if len(completed) else None,
        "alternative_unavailable_reasons": reasons,
        "extra_distance_m": _distribution(alternatives["extra_distance_m"]),
        "extra_distance_pct": _distribution(alternatives["extra_distance_pct"]),
        "mapped_light_coverage_change_pp": _distribution(
            alternatives["mapped_light_coverage_change_pp"]
        ),
        "route_runtime_ms": _distribution(completed["runtime_ms"]),
    }


def evaluate(
    journeys: pd.DataFrame,
    *,
    lighting_penalty: float,
    max_detour_ratio: float,
    transit_proximity_penalty: float,
) -> pd.DataFrame:
    """Run every journey after loading the graph and features once."""
    graph, features = load_routing_snapshot()
    results: list[dict[str, Any]] = []
    for journey in journeys.to_dict("records"):
        started = time.perf_counter()
        try:
            comparison = compare_points(
                graph,
                features,
                journey["origin_lon"],
                journey["origin_lat"],
                journey["destination_lon"],
                journey["destination_lat"],
                lighting_penalty=lighting_penalty,
                max_detour_ratio=max_detour_ratio,
                transit_proximity_penalty=transit_proximity_penalty,
            )
            results.append(record_comparison(journey, comparison, (time.perf_counter() - started) * 1000))
        except (ValueError, KeyError) as error:
            results.append(
                {
                    **journey,
                    "status": "error",
                    "error": str(error),
                    "runtime_ms": round((time.perf_counter() - started) * 1000, 2),
                }
            )
    return pd.DataFrame(results)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--journeys", type=Path, default=Path("data/evaluation/pilot_journeys.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/evaluation/results"))
    parser.add_argument("--lighting-penalty", type=float, default=2.0)
    parser.add_argument("--max-detour-ratio", type=float, default=0.20)
    parser.add_argument("--transit-proximity-penalty", type=float, default=0.0)
    arguments = parser.parse_args()

    journeys = load_journeys(arguments.journeys)
    results = evaluate(
        journeys,
        lighting_penalty=arguments.lighting_penalty,
        max_detour_ratio=arguments.max_detour_ratio,
        transit_proximity_penalty=arguments.transit_proximity_penalty,
    )
    settings = {
        "lighting_penalty": arguments.lighting_penalty,
        "max_detour_ratio": arguments.max_detour_ratio,
        "transit_proximity_penalty": arguments.transit_proximity_penalty,
    }
    summary = build_summary(results, settings)
    arguments.output_dir.mkdir(parents=True, exist_ok=True)
    results.to_csv(arguments.output_dir / "journey_results.csv", index=False)
    (arguments.output_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Wrote {arguments.output_dir / 'journey_results.csv'}")
    print(f"Wrote {arguments.output_dir / 'summary.json'}")


if __name__ == "__main__":
    main()
