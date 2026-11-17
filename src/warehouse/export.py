"""Export processed geospatial features in a plain Parquet format for Athena."""

import argparse
import json
from datetime import date
from pathlib import Path

import geopandas as gpd
import pandas as pd


WGS84 = "EPSG:4326"
REQUIRED_COLUMNS = [
    "segment_id",
    "u",
    "v",
    "key",
    "osm_way_id",
    "length_m",
    "nearby_light_count",
    "mapped_light_covered_length_m",
    "mapped_light_coverage_pct",
    "nearest_transit_stop_m",
    "lighting_data_status",
    "transit_data_status",
    "data_quality_status",
    "weak_component_id",
    "weak_component_size",
    "is_largest_weak_component",
    "geometry",
]


def snapshot_date(manifest: dict) -> date:
    """Extract an ISO calendar date from a validated source retrieval timestamp."""
    value = manifest.get("source_retrieved_utc")
    if not value:
        raise ValueError("Processed manifest is missing source_retrieved_utc")
    try:
        return date.fromisoformat(value[:10])
    except ValueError as error:
        raise ValueError("source_retrieved_utc does not start with an ISO date") from error


def export_segment_features(source: Path, manifest_path: Path, destination: Path) -> pd.DataFrame:
    """Write a non-GeoParquet segment table with WGS84 WKT geometry for Athena."""
    features = gpd.read_parquet(source)
    missing = [column for column in REQUIRED_COLUMNS if column not in features.columns]
    if missing:
        raise ValueError("Segment features are missing columns: " + ", ".join(missing))
    if features.empty or features["segment_id"].isna().any() or features["segment_id"].duplicated().any():
        raise ValueError("Segment features must have non-null unique segment_id values")
    if features.crs is None:
        raise ValueError("Segment features have no CRS")
    if not features.geometry.notna().all() or not features.geometry.is_valid.all():
        raise ValueError("Segment features contain missing or invalid geometry")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    result = features.to_crs(WGS84).copy()
    result["source_snapshot_date"] = snapshot_date(manifest)
    result["geometry_wkt"] = result.geometry.to_wkt(rounding_precision=7)
    result = pd.DataFrame(result.drop(columns="geometry"))
    result["u"] = result["u"].astype("string")
    result["v"] = result["v"].astype("string")
    result["key"] = result["key"].astype("string")
    result["osm_way_id"] = result["osm_way_id"].astype("string")
    if not result["mapped_light_coverage_pct"].dropna().between(0, 100).all():
        raise ValueError("Mapped-light coverage must be within 0 and 100")
    if not result["nearest_transit_stop_m"].dropna().ge(0).all():
        raise ValueError("Transit-stop distance cannot be negative")

    destination.parent.mkdir(parents=True, exist_ok=True)
    result.to_parquet(destination, index=False)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("data/processed/segment_features.parquet"))
    parser.add_argument("--manifest", type=Path, default=Path("data/processed/manifest.json"))
    parser.add_argument("--destination", type=Path, default=Path("data/warehouse/segment_features.parquet"))
    arguments = parser.parse_args()
    features = export_segment_features(arguments.source, arguments.manifest, arguments.destination)
    print(f"Exported {len(features)} Athena-ready segment features to {arguments.destination}")


if __name__ == "__main__":
    main()
