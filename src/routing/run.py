"""Run a local HerRoute comparison for two WGS84 coordinates."""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict
from pathlib import Path

import osmnx as ox
import pandas as pd

from src.ingestion.download import PILOT, within
from src.routing.engine import RouteComparison, compare_routes


def validate_pilot_point(lon: float, lat: float) -> None:
    """Reject endpoints outside the deliberately limited pilot area."""
    if not within(lon, lat, PILOT):
        west, south, east, north = PILOT
        raise ValueError(
            "Endpoint must be within the Alexanderplatz pilot area "
            f"({west}, {south}) to ({east}, {north})"
        )


def nearest_graph_node(graph, lon: float, lat: float):
    """Return the closest graph node using a local geographic approximation.

    The pilot area is small enough that scaling longitude by the cosine of the
    query latitude gives a stable nearest-node choice without OSMnx's optional
    scikit-learn dependency.
    """
    longitude_scale = math.cos(math.radians(lat))
    nearest_node = None
    nearest_distance_sq = math.inf
    for node, attributes in graph.nodes(data=True):
        try:
            node_lon = float(attributes["x"])
            node_lat = float(attributes["y"])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("Walking graph nodes require numeric WGS84 x and y coordinates") from error
        distance_sq = ((node_lon - lon) * longitude_scale) ** 2 + (node_lat - lat) ** 2
        if distance_sq < nearest_distance_sq:
            nearest_node = node
            nearest_distance_sq = distance_sq
    if nearest_node is None:
        raise ValueError("Walking graph contains no nodes")
    return nearest_node


def compare_coordinates(
    origin_lon: float,
    origin_lat: float,
    destination_lon: float,
    destination_lat: float,
    graph_path: Path = Path("data/raw/walk.graphml"),
    features_path: Path = Path("data/processed/segment_features.parquet"),
    max_detour_ratio: float = 0.20,
    lighting_penalty: float = 2.0,
) -> RouteComparison:
    """Validate, snap two coordinates to the graph, and compare their routes."""
    validate_pilot_point(origin_lon, origin_lat)
    validate_pilot_point(destination_lon, destination_lat)
    if not graph_path.exists() or not features_path.exists():
        raise FileNotFoundError("Run ingestion and geospatial processing before routing")
    graph = ox.load_graphml(graph_path)
    features = pd.read_parquet(features_path)
    origin = nearest_graph_node(graph, origin_lon, origin_lat)
    destination = nearest_graph_node(graph, destination_lon, destination_lat)
    return compare_routes(
        graph,
        features,
        origin,
        destination,
        max_detour_ratio=max_detour_ratio,
        lighting_penalty=lighting_penalty,
    )


def comparison_summary(comparison: RouteComparison) -> dict:
    """Return presentation-ready route metrics without exposing graph internals."""
    def route_summary(route):
        if route is None:
            return None
        return {
            "node_count": len(route.nodes),
            "edge_count": len(route.edges),
            "metrics": asdict(route.metrics),
        }

    return {
        "shortest": route_summary(comparison.shortest),
        "lighting_aware": route_summary(comparison.lighting_aware),
        "alternative_unavailable_reason": comparison.alternative_unavailable_reason,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin-lon", type=float, required=True)
    parser.add_argument("--origin-lat", type=float, required=True)
    parser.add_argument("--destination-lon", type=float, required=True)
    parser.add_argument("--destination-lat", type=float, required=True)
    parser.add_argument("--max-detour-ratio", type=float, default=0.20)
    parser.add_argument("--lighting-penalty", type=float, default=2.0)
    parser.add_argument("--summary", action="store_true", help="Print metrics without node and edge identifiers")
    arguments = parser.parse_args()
    result = compare_coordinates(
        arguments.origin_lon,
        arguments.origin_lat,
        arguments.destination_lon,
        arguments.destination_lat,
        max_detour_ratio=arguments.max_detour_ratio,
        lighting_penalty=arguments.lighting_penalty,
    )
    output = comparison_summary(result) if arguments.summary else asdict(result)
    print(json.dumps(output, indent=2, default=str))


if __name__ == "__main__":
    main()
