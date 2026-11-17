import json

import pandas as pd
import pytest

from src.warehouse.promote import validate_candidate


def write_candidate(tmp_path, *, segment_count=1, snapshot_date="2026-11-17"):
    manifest = tmp_path / "manifest.json"
    warehouse = tmp_path / "segment_features.parquet"
    manifest.write_text(json.dumps({"source_retrieved_utc": f"{snapshot_date}T12:00:00+00:00", "segments_exported": segment_count}))
    pd.DataFrame(
        {
            "segment_id": [f"edge-{index}" for index in range(segment_count)],
            "length_m": [100.0] * segment_count,
            "mapped_light_coverage_pct": [50.0] * segment_count,
            "nearest_transit_stop_m": [10.0] * segment_count,
            "source_snapshot_date": [snapshot_date] * segment_count,
            "geometry_wkt": ["LINESTRING (13.4 52.5, 13.401 52.501)"] * segment_count,
        }
    ).to_parquet(warehouse, index=False)
    return manifest, warehouse


def test_validates_matching_candidate_manifest_and_warehouse_file(tmp_path):
    manifest, warehouse = write_candidate(tmp_path, segment_count=2)

    result = validate_candidate(manifest, warehouse, "run-44127441145-1")

    assert result["snapshot_date"] == "2026-11-17"
    assert result["segments_exported"] == 2


def test_rejects_candidate_when_manifest_count_does_not_match_file(tmp_path):
    manifest, warehouse = write_candidate(tmp_path, segment_count=2)
    manifest.write_text(json.dumps({"source_retrieved_utc": "2026-11-17T12:00:00+00:00", "segments_exported": 3}))

    with pytest.raises(ValueError, match="does not match"):
        validate_candidate(manifest, warehouse, "run-44127441145-1")
