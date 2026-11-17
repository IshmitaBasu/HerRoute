select
    segment_id,
    source_snapshot_date,
    nearby_light_count,
    mapped_light_covered_length_m,
    mapped_light_coverage_pct,
    nearest_transit_stop_m,
    lighting_data_status,
    transit_data_status,
    data_quality_status,
    weak_component_id,
    weak_component_size,
    is_largest_weak_component
from {{ ref('stg_segment_features') }}
