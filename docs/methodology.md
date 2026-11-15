# Geospatial methodology and data quality

## Processed segment features

The process in `src/geospatial/process.py` reads the validated raw snapshot, repairs geometry where possible, rejects empty or invalid input, and converts spatial data to EPSG:25833 before measuring distance. It retains the OSM directed multi-edge identity as `u`, `v`, `key` and a derived `segment_id`; a street can therefore appear as two directed edges. Persisted GeoParquet geometry is converted back to WGS84 for display and AWS/Athena interoperability.

For each walking edge, `length_m` is the geometric length in EPSG:25833. A mapped-light feature contributes when its 20 m buffer intersects the edge. `mapped_light_covered_length_m` is the length of the edge inside the union of its intersecting light buffers, clipped to the edge length to guard against floating-point precision. `mapped_light_coverage_pct` is that length divided by edge length. `nearby_light_count` counts mapped-light points within 20 m of the edge.

`nearest_transit_stop_m` is the straight-line distance from the edge geometry to the closest GTFS stop point. It does not represent walking access, station accessibility, scheduled service or night-time availability. The current GTFS data may contain platforms and entrances as separate stop records.

## Missing data and limitations

When a lighting or stop input is unavailable, the corresponding metric remains null and `data_quality_status` is `source_missing`; it is never changed to zero. For the validated snapshot both inputs are present, so features are labeled `source_snapshot_available_inventory_completeness_unknown`. This means the source was available, while completeness of the public inventory remains unknown.

Mapped-light proximity is not a measurement of illumination, lamp condition, lighting quality, pedestrian visibility or personal safety. The 20 m radius is a transparent geometric proxy and has not been presented as a validated illumination radius. The feature layer retains disconnected network components; routing must later reject endpoints without a connected path.

## Snapshot results: 15 November 2026

The processed buffered snapshot contains 7,860 nodes and 19,516 directed edges. The largest weakly connected component contains 7,591 nodes; 346 edges lie outside it. The directed-edge total is 531.2 km, so it must not be interpreted as unique physical street length. The source snapshot includes 4,759 mapped-light points and 912 GTFS stop records.

At a 20 m buffer, the median segment mapped-light coverage is 100%, the mean is 76.24%, 3,230 edges have zero mapped-light coverage and 12,348 are fully covered by the proxy. The median nearest-stop distance is 89.13 m and the maximum is 364.8 m. These are descriptive results for this snapshot, not claims about safety or network-wide service quality.

## Sensitivity check

The same raw snapshot was processed at 10 m, 20 m and 30 m buffers by passing `--light-buffer-m` and a separate `--output` path.

| Buffer | Mean segment coverage | Median segment coverage | Zero-coverage edges | Fully covered edges |
|---:|---:|---:|---:|---:|
| 10 m | 40.52% | 36.54% | 7,368 | 2,803 |
| 20 m | 76.24% | 100.00% | 3,230 | 12,348 |
| 30 m | 84.56% | 100.00% | 2,278 | 14,770 |

The buffer materially changes the proxy, so 20 m remains an initial, documented routing parameter. The routing prototype will compare route outcomes at alternative parameters before treating this choice as useful for route comparison.
