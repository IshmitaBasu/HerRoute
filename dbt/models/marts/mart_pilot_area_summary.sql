select
    source_snapshot_date,
    count(*) as segment_count,
    sum(length_m) as total_length_m,
    sum(mapped_light_covered_length_m) as mapped_light_covered_length_m,
    100.0 * sum(mapped_light_covered_length_m) / nullif(sum(length_m), 0) as mapped_light_coverage_pct,
    avg(nearest_transit_stop_m) as mean_nearest_transit_stop_m,
    sum(case when data_quality_status = 'source_snapshot_available_inventory_completeness_unknown' then 1 else 0 end) as source_available_segment_count
from {{ ref('dim_street_segment') }} as segment
inner join {{ ref('fct_segment_infrastructure') }} as infrastructure
    using (segment_id, source_snapshot_date)
group by 1
