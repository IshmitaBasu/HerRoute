"""Validate a downloaded S3 candidate before it can be promoted to Athena."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd

from src.warehouse.export import snapshot_date


CANDIDATE_KEY_PATTERN = re.compile(r"run-\d+-\d+")
REQUIRED_COLUMNS = {
    "segment_id",
    "length_m",
    "mapped_light_coverage_pct",
    "nearest_transit_stop_m",
    "source_snapshot_date",
    "geometry_wkt",
}


def validate_candidate(manifest_path: Path, warehouse_path: Path, candidate_key: str) -> dict:
    """Return promotion metadata after checking the re-downloaded candidate artifacts."""
    if not CANDIDATE_KEY_PATTERN.fullmatch(candidate_key):
        raise ValueError("Candidate key must use the form run-<GitHub-run-id>-<attempt>")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_segments = manifest.get("segments_exported")
    if not isinstance(expected_segments, int) or expected_segments <= 0:
        raise ValueError("Candidate manifest is missing a positive segments_exported value")

    snapshot = snapshot_date(manifest).isoformat()
    features = pd.read_parquet(warehouse_path)
    missing = REQUIRED_COLUMNS.difference(features.columns)
    if missing:
        raise ValueError("Candidate warehouse file is missing columns: " + ", ".join(sorted(missing)))
    if len(features) != expected_segments:
        raise ValueError("Candidate segment count does not match its processed manifest")
    if features["segment_id"].isna().any() or features["segment_id"].duplicated().any():
        raise ValueError("Candidate warehouse file contains null or duplicate segment IDs")
    if not features["length_m"].gt(0).all():
        raise ValueError("Candidate warehouse file contains non-positive segment lengths")
    coverage = features["mapped_light_coverage_pct"].dropna()
    if not coverage.between(0, 100).all():
        raise ValueError("Candidate mapped-light coverage is outside 0-100")
    stop_distance = features["nearest_transit_stop_m"].dropna()
    if not stop_distance.ge(0).all():
        raise ValueError("Candidate contains a negative transit-stop distance")
    dates = pd.to_datetime(features["source_snapshot_date"], errors="coerce").dt.date
    if dates.isna().any() or {value.isoformat() for value in dates} != {snapshot}:
        raise ValueError("Candidate warehouse source_snapshot_date does not match its manifest")

    return {
        "candidate_key": candidate_key,
        "snapshot_date": snapshot,
        "segments_exported": expected_segments,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--warehouse", type=Path, required=True)
    parser.add_argument("--candidate-key", required=True)
    arguments = parser.parse_args()
    print(json.dumps(validate_candidate(arguments.manifest, arguments.warehouse, arguments.candidate_key)))


if __name__ == "__main__":
    main()
