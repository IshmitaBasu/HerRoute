import json

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import LineString

from src.warehouse.export import export_segment_features, snapshot_date


def test_export_writes_wgs84_wkt_and_snapshot_date(tmp_path):
    source = tmp_path / "features.parquet"
    manifest = tmp_path / "manifest.json"
    destination = tmp_path / "warehouse" / "segments.parquet"
    frame = gpd.GeoDataFrame(
        {
            "segment_id": ["edge-1"], "u": [1], "v": [2], "key": [0], "osm_way_id": ["12"],
            "length_m": [100.0], "nearby_light_count": [1], "mapped_light_covered_length_m": [30.0],
            "mapped_light_coverage_pct": [30.0], "nearest_transit_stop_m": [10.0],
            "lighting_data_status": ["source_snapshot_available"], "transit_data_status": ["source_snapshot_available"],
            "data_quality_status": ["source_snapshot_available_inventory_completeness_unknown"],
            "weak_component_id": [0], "weak_component_size": [2], "is_largest_weak_component": [True],
        },
        geometry=[LineString([(13.4, 52.5), (13.401, 52.5)])],
        crs="EPSG:4326",
    )
    frame.to_parquet(source, index=False)
    manifest.write_text(json.dumps({"source_retrieved_utc": "2026-11-15T10:26:43+00:00"}), encoding="utf-8")

    result = export_segment_features(source, manifest, destination)

    persisted = pd.read_parquet(destination)
    assert destination.exists()
    assert result.loc[0, "source_snapshot_date"].isoformat() == "2026-11-15"
    assert persisted.loc[0, "geometry_wkt"].startswith("LINESTRING")
    assert persisted.loc[0, "segment_id"] == "edge-1"


def test_snapshot_date_requires_timestamp():
    with pytest.raises(ValueError, match="source_retrieved_utc"):
        snapshot_date({})
