from types import SimpleNamespace

import pandas as pd

from src.evaluation.run import build_summary, record_comparison


def route(distance, coverage):
    return SimpleNamespace(
        metrics=SimpleNamespace(
            distance_m=distance,
            estimated_minutes=distance / 75,
            mapped_light_coverage_pct=coverage,
            mean_nearest_transit_stop_m=25.0,
        )
    )


def test_record_comparison_keeps_distance_and_coverage_changes():
    comparison = SimpleNamespace(
        shortest=route(1000, 70),
        lighting_aware=route(1100, 90),
        alternative_unavailable_reason=None,
    )

    record = record_comparison({"journey_id": "J01"}, comparison, 45.678)

    assert record["alternative_available"] is True
    assert record["extra_distance_m"] == 100
    assert record["extra_distance_pct"] == 10
    assert record["mapped_light_coverage_change_pp"] == 20
    assert record["runtime_ms"] == 45.68


def test_summary_distinguishes_valid_no_alternative_from_error():
    results = pd.DataFrame(
        [
            {
                "status": "completed", "alternative_available": True,
                "extra_distance_m": 100, "extra_distance_pct": 10,
                "mapped_light_coverage_change_pp": 20, "runtime_ms": 20,
                "alternative_unavailable_reason": None,
            },
            {
                "status": "completed", "alternative_available": False,
                "extra_distance_m": None, "extra_distance_pct": None,
                "mapped_light_coverage_change_pp": None, "runtime_ms": 30,
                "alternative_unavailable_reason": "No distinct lighting-aware alternative was found.",
            },
            {
                "status": "error", "alternative_available": None,
                "extra_distance_m": None, "extra_distance_pct": None,
                "mapped_light_coverage_change_pp": None, "runtime_ms": 5,
                "alternative_unavailable_reason": None,
            },
        ]
    )

    summary = build_summary(results, {"lighting_penalty": 2.0})

    assert summary["journeys_completed"] == 2
    assert summary["journey_errors"] == 1
    assert summary["distinct_alternatives"] == 1
    assert summary["distinct_alternative_rate_pct"] == 50
    assert summary["extra_distance_m"]["median"] == 100
    assert summary["alternative_unavailable_reasons"] == {
        "No distinct lighting-aware alternative was found.": 1
    }
