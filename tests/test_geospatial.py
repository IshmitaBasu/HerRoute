import geopandas as gpd
import numpy as np
import pytest
from shapely.geometry import LineString, Point

from src.geospatial.process import METRIC_CRS, calculate_features, validate_features


def frame(geometries, **columns):
    return gpd.GeoDataFrame(columns, geometry=geometries, crs=METRIC_CRS)


def test_calculates_length_coverage_light_count_and_stop_distance():
    edges = frame([LineString([(0, 0), (100, 0)])], segment_id=["edge-1"])
    lights = frame([Point(50, 10)])
    stops = frame([Point(50, 30)])

    result = calculate_features(edges, lights, stops, light_buffer_m=20)

    row = result.iloc[0]
    assert row["length_m"] == 100
    assert row["nearby_light_count"] == 1
    assert 34 < row["mapped_light_covered_length_m"] < 35
    assert 34 < row["mapped_light_coverage_pct"] < 35
    assert row["nearest_transit_stop_m"] == 30
    assert row["data_quality_status"] == "source_snapshot_available_inventory_completeness_unknown"


def test_missing_sources_remain_unknown_not_zero():
    edges = frame([LineString([(0, 0), (10, 0)])], segment_id=["edge-1"])

    result = calculate_features(edges, None, None)

    row = result.iloc[0]
    assert np.isnan(row["mapped_light_coverage_pct"])
    assert np.isnan(row["nearest_transit_stop_m"])
    assert row["data_quality_status"] == "source_missing"


def test_feature_validation_rejects_coverage_outside_range():
    features = frame([LineString([(0, 0), (10, 0)])], segment_id=["edge-1"], length_m=[10], mapped_light_coverage_pct=[101], nearest_transit_stop_m=[1])

    with pytest.raises(ValueError, match="outside"):
        validate_features(features)


def test_coverage_is_capped_at_100_for_numeric_precision():
    edges = frame([LineString([(0, 0), (1, 0)])], segment_id=["edge-1"])
    lights = frame([Point(0.5, 0)])
    stops = frame([Point(0, 0)])

    result = calculate_features(edges, lights, stops, light_buffer_m=20)

    assert result.iloc[0]["mapped_light_coverage_pct"] == 100
