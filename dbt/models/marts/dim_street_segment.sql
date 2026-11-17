select
    segment_id,
    source_snapshot_date,
    osm_way_id,
    from_node_id,
    to_node_id,
    edge_key,
    length_m,
    geometry_wkt
from {{ ref('stg_segment_features') }}
