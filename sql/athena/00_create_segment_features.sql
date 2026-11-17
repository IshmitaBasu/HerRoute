CREATE EXTERNAL TABLE IF NOT EXISTS herroute.segment_features (
    segment_id string,
    u string,
    v string,
    key string,
    osm_way_id string,
    length_m double,
    nearby_light_count bigint,
    mapped_light_covered_length_m double,
    mapped_light_coverage_pct double,
    nearest_transit_stop_m double,
    lighting_data_status string,
    transit_data_status string,
    data_quality_status string,
    weak_component_id bigint,
    weak_component_size bigint,
    is_largest_weak_component boolean,
    source_snapshot_date date,
    geometry_wkt string
)
STORED AS PARQUET
LOCATION 's3://herroute-627511992462-eu-central-1/staging/segment_features/snapshot=2026-11-17/data/'
TBLPROPERTIES ('parquet.compression' = 'SNAPPY');
