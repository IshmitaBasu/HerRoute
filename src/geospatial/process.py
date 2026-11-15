"""Create validated street-segment infrastructure features from a raw snapshot."""

import argparse
import hashlib
import json
from pathlib import Path

import geopandas as gpd
import networkx as nx
import numpy as np
import osmnx as ox
import pandas as pd

from src.ingestion.download import BOUNDS

WGS84 = "EPSG:4326"
METRIC_CRS = "EPSG:25833"
LIGHT_BUFFER_M = 20.0
RAW = Path("data/raw")
OUT = Path("data/processed")


def checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _valid_geometries(frame: gpd.GeoDataFrame, label: str) -> gpd.GeoDataFrame:
    frame = frame[frame.geometry.notna() & ~frame.geometry.is_empty].copy()
    if frame.empty:
        raise ValueError(f"No valid {label} geometries")
    frame["geometry"] = frame.geometry.make_valid()
    if not frame.geometry.is_valid.all():
        raise ValueError(f"Invalid {label} geometries remain after repair")
    return frame


def load_lights(path: Path) -> gpd.GeoDataFrame:
    lights = gpd.read_file(path)
    if lights.crs is None:
        raise ValueError("Lighting source has no CRS")
    lights = _valid_geometries(lights, "lighting")
    lights = lights.explode(index_parts=False).reset_index(drop=True)
    lights = lights[lights.geometry.geom_type == "Point"].copy()
    if lights.empty:
        raise ValueError("Lighting source contains no point geometries")
    return lights.to_crs(METRIC_CRS)


def load_stops(path: Path) -> gpd.GeoDataFrame:
    stops = pd.read_csv(path, dtype={"stop_id": "string", "stop_name": "string"})
    required = {"stop_id", "stop_name", "stop_lat", "stop_lon"}
    if not required.issubset(stops.columns):
        raise ValueError("Transit stops source is missing required fields")
    stops["stop_lat"] = pd.to_numeric(stops["stop_lat"], errors="coerce")
    stops["stop_lon"] = pd.to_numeric(stops["stop_lon"], errors="coerce")
    stops = stops.dropna(subset=["stop_id", "stop_lat", "stop_lon"]).copy()
    if stops.empty:
        raise ValueError("Transit stops source contains no valid coordinates")
    stops = gpd.GeoDataFrame(
        stops[["stop_id", "stop_name"]],
        geometry=gpd.points_from_xy(stops["stop_lon"], stops["stop_lat"]),
        crs=WGS84,
    )
    return stops.to_crs(METRIC_CRS)


def _osm_way_id(value) -> str:
    if isinstance(value, (list, tuple, set)):
        return ";".join(map(str, value))
    return "" if pd.isna(value) else str(value)


def graph_frames(graph) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame, dict]:
    nodes, edges = ox.graph_to_gdfs(graph, nodes=True, edges=True, fill_edge_geometry=True)
    if nodes.crs is None or edges.crs is None:
        raise ValueError("Walking graph lacks a CRS")
    edges = _valid_geometries(edges.reset_index(), "walking-edge")
    edges["segment_id"] = edges.apply(lambda row: f"{row['u']}:{row['v']}:{row['key']}", axis=1)
    if edges["segment_id"].duplicated().any():
        raise ValueError("Walking graph contains duplicate edge identities")
    edges["osm_way_id"] = edges.get("osmid", pd.Series(index=edges.index, dtype=object)).map(_osm_way_id)

    components = sorted(nx.weakly_connected_components(graph), key=len, reverse=True)
    if not components:
        raise ValueError("Walking graph has no connected components")
    component_id = {str(node): number for number, component in enumerate(components) for node in component}
    component_size = {number: len(component) for number, component in enumerate(components)}
    edges["weak_component_id"] = edges["u"].map(lambda node: component_id[str(node)])
    edges["weak_component_size"] = edges["weak_component_id"].map(component_size)
    edges["is_largest_weak_component"] = edges["weak_component_id"].eq(0)

    nodes = _valid_geometries(nodes.reset_index().rename(columns={"osmid": "node_id"}), "walking-node")
    nodes["node_id"] = nodes["node_id"].astype(str)
    nodes["weak_component_id"] = nodes["node_id"].map(component_id)
    nodes["weak_component_size"] = nodes["weak_component_id"].map(component_size)
    nodes["is_largest_weak_component"] = nodes["weak_component_id"].eq(0)
    summary = {
        "weak_component_count": len(components),
        "largest_weak_component_nodes": len(components[0]),
    }
    return nodes.to_crs(METRIC_CRS), edges.to_crs(METRIC_CRS), summary


def calculate_features(
    edges: gpd.GeoDataFrame,
    lights: gpd.GeoDataFrame | None,
    stops: gpd.GeoDataFrame | None,
    light_buffer_m: float = LIGHT_BUFFER_M,
) -> gpd.GeoDataFrame:
    """Return metrics on metric-CRS edges; null is reserved for unavailable input."""
    if edges.crs is None or str(edges.crs).upper() != METRIC_CRS:
        raise ValueError(f"Edges must use {METRIC_CRS}")
    if "segment_id" not in edges or edges["segment_id"].duplicated().any():
        raise ValueError("Edges require unique segment_id values")
    if light_buffer_m <= 0:
        raise ValueError("Light buffer must be positive")

    result = edges.copy()
    result["length_m"] = result.geometry.length
    if (result["length_m"] <= 0).any():
        raise ValueError("Walking edges must have positive length")

    if lights is None or lights.empty:
        result["nearby_light_count"] = pd.NA
        result["mapped_light_covered_length_m"] = np.nan
        result["mapped_light_coverage_pct"] = np.nan
        result["lighting_data_status"] = "source_missing"
    else:
        if str(lights.crs).upper() != METRIC_CRS:
            raise ValueError(f"Lights must use {METRIC_CRS}")
        matches = lights.sindex.query(result.geometry, predicate="dwithin", distance=light_buffer_m)
        counts = np.bincount(matches[0], minlength=len(result)) if matches.size else np.zeros(len(result), dtype=int)
        covered_lengths = np.zeros(len(result), dtype=float)
        # Buffer only lights that can touch each edge. This produces the same union-of-
        # buffers measure as a city-wide union, without repeatedly intersecting every edge
        # with one very large geometry.
        for edge_position in np.unique(matches[0]) if matches.size else []:
            nearby_positions = matches[1, matches[0] == edge_position]
            nearby_buffers = lights.geometry.iloc[nearby_positions].buffer(light_buffer_m).union_all()
            covered_lengths[edge_position] = result.geometry.iloc[edge_position].intersection(nearby_buffers).length
        result["mapped_light_covered_length_m"] = np.minimum(covered_lengths, result["length_m"])
        result["mapped_light_coverage_pct"] = 100 * result["mapped_light_covered_length_m"] / result["length_m"]
        result["mapped_light_coverage_pct"] = result["mapped_light_coverage_pct"].clip(lower=0, upper=100)
        result["nearby_light_count"] = counts
        result["lighting_data_status"] = "source_snapshot_available"

    if stops is None or stops.empty:
        result["nearest_transit_stop_m"] = np.nan
        result["transit_data_status"] = "source_missing"
    else:
        if str(stops.crs).upper() != METRIC_CRS:
            raise ValueError(f"Stops must use {METRIC_CRS}")
        nearest = gpd.sjoin_nearest(
            result[["segment_id", "geometry"]],
            stops[["geometry"]],
            how="left",
            distance_col="nearest_transit_stop_m",
        )
        distance = nearest.groupby("segment_id")["nearest_transit_stop_m"].min()
        result["nearest_transit_stop_m"] = result["segment_id"].map(distance)
        result["transit_data_status"] = "source_snapshot_available"

    source_available = result["lighting_data_status"].eq("source_snapshot_available") & result["transit_data_status"].eq("source_snapshot_available")
    result["data_quality_status"] = np.where(source_available, "source_snapshot_available_inventory_completeness_unknown", "source_missing")
    validate_features(result)
    return result


def validate_features(features: gpd.GeoDataFrame) -> None:
    if features.empty or features["segment_id"].duplicated().any():
        raise ValueError("Segment features must be non-empty with unique identities")
    if not features.geometry.is_valid.all() or (features["length_m"] <= 0).any():
        raise ValueError("Segment features contain invalid geometry or length")
    coverage = features["mapped_light_coverage_pct"].dropna()
    if not coverage.between(0, 100).all():
        raise ValueError("Mapped-light coverage is outside 0–100 percent")
    distances = features["nearest_transit_stop_m"].dropna()
    if (distances < 0).any():
        raise ValueError("Transit-stop distance cannot be negative")


def write_outputs(nodes: gpd.GeoDataFrame, features: gpd.GeoDataFrame, report: dict, directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    manifest = directory / "manifest.json"
    manifest.unlink(missing_ok=True)
    node_output = nodes[["node_id", "weak_component_id", "weak_component_size", "is_largest_weak_component", "geometry"]].to_crs(WGS84)
    edge_output = features[[
        "segment_id", "u", "v", "key", "osm_way_id", "length_m", "nearby_light_count",
        "mapped_light_covered_length_m", "mapped_light_coverage_pct", "nearest_transit_stop_m",
        "lighting_data_status", "transit_data_status", "data_quality_status", "weak_component_id",
        "weak_component_size", "is_largest_weak_component", "geometry",
    ]].to_crs(WGS84)
    node_path = directory / "walk_nodes.parquet"
    edge_path = directory / "segment_features.parquet"
    node_output.to_parquet(node_path, index=False)
    edge_output.to_parquet(edge_path, index=False)
    report["outputs"] = {
        "walk_nodes": {"file": node_path.name, "sha256": checksum(node_path)},
        "segment_features": {"file": edge_path.name, "sha256": checksum(edge_path)},
    }
    manifest.write_text(json.dumps(report, indent=2), encoding="utf-8")


def main(light_buffer_m: float = LIGHT_BUFFER_M, output: Path = OUT) -> None:
    raw_manifest = RAW / "manifest.json"
    required = [RAW / "lights.geojson", RAW / "stops.csv", RAW / "walk.graphml", raw_manifest]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("Raw snapshot is incomplete: " + ", ".join(missing))
    source_manifest = json.loads(raw_manifest.read_text(encoding="utf-8"))
    lights = load_lights(RAW / "lights.geojson")
    stops = load_stops(RAW / "stops.csv")
    graph = ox.load_graphml(RAW / "walk.graphml")
    nodes, edges, connectivity = graph_frames(graph)
    features = calculate_features(edges, lights, stops, light_buffer_m=light_buffer_m)
    report = {
        "source_manifest_sha256": checksum(raw_manifest),
        "source_retrieved_utc": source_manifest.get("retrieved_utc"),
        "input_bounds_wgs84": BOUNDS,
        "metric_crs": METRIC_CRS,
        "mapped_light_buffer_m": light_buffer_m,
        "lights_used": len(lights),
        "stops_used": len(stops),
        "nodes_exported": len(nodes),
        "segments_exported": len(features),
        **connectivity,
        "method_notes": [
            "Coverage is the length of each segment inside the union of 20 m buffers around mapped-light points.",
            "Mapped-light coverage is an infrastructure proxy, not a measure of illumination, lamp functionality or safety.",
            "Nearest transit-stop distance is Euclidean distance from an edge geometry to a mapped stop point; it is not a walking-access or service-availability measure.",
        ],
    }
    write_outputs(nodes, features, report, output)
    print(f"Validated processed snapshot: {output / 'manifest.json'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--light-buffer-m", type=float, default=LIGHT_BUFFER_M)
    parser.add_argument("--output", type=Path, default=OUT)
    arguments = parser.parse_args()
    main(arguments.light_buffer_m, arguments.output)
