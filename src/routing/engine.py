"""Compute shortest and mapped-lighting-aware walking route comparisons."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Hashable

import networkx as nx
import pandas as pd


WALKING_SPEED_M_PER_MINUTE = 75.0
DEFAULT_LIGHTING_PENALTY = 2.0
DEFAULT_UNKNOWN_COVERAGE_PENALTY = 1.0
DEFAULT_MAX_DETOUR_RATIO = 0.20
DEFAULT_TRANSIT_PROXIMITY_PENALTY = 0.0
TRANSIT_PROXIMITY_SCALE_M = 200.0


@dataclass(frozen=True)
class RouteMetrics:
    """Transparent summary of a route's length and infrastructure proxies."""

    distance_m: float
    estimated_minutes: float
    mapped_light_coverage_pct: float | None
    mapped_light_known_length_m: float
    mapped_light_unknown_length_m: float
    mean_nearest_transit_stop_m: float | None


@dataclass(frozen=True)
class Route:
    """Ordered directed edges and metrics for one route."""

    nodes: tuple[Hashable, ...]
    edges: tuple[tuple[Hashable, Hashable, Hashable], ...]
    metrics: RouteMetrics


@dataclass(frozen=True)
class RouteComparison:
    """Baseline route and an optional feasible lighting-aware alternative."""

    shortest: Route
    lighting_aware: Route | None
    alternative_unavailable_reason: str | None


def _segment_id(u: Hashable, v: Hashable, key: Hashable) -> str:
    return f"{u}:{v}:{key}"


def _as_number(value, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} must be numeric") from error
    if number < 0:
        raise ValueError(f"{name} cannot be negative")
    return number


def build_route_graph(
    graph: nx.MultiDiGraph,
    features: pd.DataFrame,
    lighting_penalty: float = DEFAULT_LIGHTING_PENALTY,
    unknown_coverage_penalty: float = DEFAULT_UNKNOWN_COVERAGE_PENALTY,
    transit_proximity_penalty: float = DEFAULT_TRANSIT_PROXIMITY_PENALTY,
) -> nx.MultiDiGraph:
    """Join validated segment features to routing edges and assign route costs.

    The lighting-aware cost is distance multiplied by a penalty for lower known
    mapped-light coverage. Null coverage remains explicit and receives a fixed
    uncertainty penalty; it is never treated as zero coverage.
    """
    if lighting_penalty < 0 or unknown_coverage_penalty < 0 or transit_proximity_penalty < 0:
        raise ValueError("Routing penalties cannot be negative")
    required = {"segment_id", "length_m", "mapped_light_coverage_pct", "nearest_transit_stop_m"}
    missing = required.difference(features.columns)
    if missing:
        raise ValueError("Features are missing required columns: " + ", ".join(sorted(missing)))
    if features["segment_id"].isna().any() or features["segment_id"].duplicated().any():
        raise ValueError("Features require unique, non-null segment_id values")

    by_segment = features.set_index("segment_id", drop=False)
    routed = nx.MultiDiGraph()
    routed.graph.update(graph.graph)
    routed.add_nodes_from(graph.nodes(data=True))

    for u, v, key, edge_data in graph.edges(keys=True, data=True):
        segment_id = _segment_id(u, v, key)
        if segment_id not in by_segment.index:
            continue
        feature = by_segment.loc[segment_id]
        length_m = _as_number(feature["length_m"], "length_m")
        if length_m == 0:
            continue
        coverage_value = feature["mapped_light_coverage_pct"]
        coverage_known = pd.notna(coverage_value)
        if coverage_known:
            coverage_pct = _as_number(coverage_value, "mapped_light_coverage_pct")
            if coverage_pct > 100:
                raise ValueError("mapped_light_coverage_pct cannot exceed 100")
            lighting_cost = length_m * (1 + lighting_penalty * (1 - coverage_pct / 100))
        else:
            coverage_pct = None
            lighting_cost = length_m * (1 + unknown_coverage_penalty)
        transit_value = feature["nearest_transit_stop_m"]
        transit_distance = _as_number(transit_value, "nearest_transit_stop_m") if pd.notna(transit_value) else TRANSIT_PROXIMITY_SCALE_M
        transit_cost = lighting_cost * (1 + transit_proximity_penalty * min(transit_distance / TRANSIT_PROXIMITY_SCALE_M, 1))

        routed.add_edge(
            u,
            v,
            key=key,
            **edge_data,
            segment_id=segment_id,
            length_m=length_m,
            mapped_light_coverage_pct=coverage_pct,
            nearest_transit_stop_m=transit_value,
            baseline_cost=length_m,
            lighting_cost=lighting_cost,
            preference_cost=transit_cost,
        )
    if routed.number_of_edges() == 0:
        raise ValueError("No graph edges matched validated segment features")
    return routed


def _shortest_edge_path(
    graph: nx.MultiDiGraph, origin: Hashable, destination: Hashable, weight: str
) -> tuple[tuple[Hashable, ...], tuple[tuple[Hashable, Hashable, Hashable], ...]]:
    try:
        nodes = tuple(nx.shortest_path(graph, origin, destination, weight=weight, method="dijkstra"))
    except nx.NodeNotFound as error:
        raise ValueError("Origin or destination is not present in the routing graph") from error
    except nx.NetworkXNoPath as error:
        raise ValueError("No directed walking path connects the selected endpoints") from error

    edges: list[tuple[Hashable, Hashable, Hashable]] = []
    for u, v in zip(nodes, nodes[1:]):
        choices = graph.get_edge_data(u, v)
        if not choices:
            raise RuntimeError("Path contained an edge that could not be recovered")
        key = min(choices, key=lambda candidate_key: choices[candidate_key][weight])
        edges.append((u, v, key))
    return nodes, tuple(edges)


def _metrics(graph: nx.MultiDiGraph, edges: tuple[tuple[Hashable, Hashable, Hashable], ...]) -> RouteMetrics:
    if not edges:
        raise ValueError("A route must contain at least one edge")
    distance_m = 0.0
    known_length_m = 0.0
    covered_length_m = 0.0
    unknown_length_m = 0.0
    transit_distance_weighted_sum = 0.0
    transit_length_m = 0.0
    for u, v, key in edges:
        edge = graph[u][v][key]
        length_m = edge["length_m"]
        distance_m += length_m
        coverage_pct = edge["mapped_light_coverage_pct"]
        if coverage_pct is None:
            unknown_length_m += length_m
        else:
            known_length_m += length_m
            covered_length_m += length_m * coverage_pct / 100
        transit_distance = edge["nearest_transit_stop_m"]
        if pd.notna(transit_distance):
            transit_distance_weighted_sum += length_m * _as_number(transit_distance, "nearest_transit_stop_m")
            transit_length_m += length_m

    coverage_pct = 100 * covered_length_m / known_length_m if known_length_m else None
    mean_transit_m = transit_distance_weighted_sum / transit_length_m if transit_length_m else None
    return RouteMetrics(
        distance_m=distance_m,
        estimated_minutes=distance_m / WALKING_SPEED_M_PER_MINUTE,
        mapped_light_coverage_pct=coverage_pct,
        mapped_light_known_length_m=known_length_m,
        mapped_light_unknown_length_m=unknown_length_m,
        mean_nearest_transit_stop_m=mean_transit_m,
    )


def compare_routes(
    graph: nx.MultiDiGraph,
    features: pd.DataFrame,
    origin: Hashable,
    destination: Hashable,
    max_detour_ratio: float = DEFAULT_MAX_DETOUR_RATIO,
    lighting_penalty: float = DEFAULT_LIGHTING_PENALTY,
    transit_proximity_penalty: float = DEFAULT_TRANSIT_PROXIMITY_PENALTY,
) -> RouteComparison:
    """Return a shortest route and a distinct lighting-aware route when feasible."""
    if not 0 <= max_detour_ratio:
        raise ValueError("max_detour_ratio cannot be negative")
    if origin == destination:
        raise ValueError("Origin and destination must be different")

    routed = build_route_graph(
        graph,
        features,
        lighting_penalty=lighting_penalty,
        transit_proximity_penalty=transit_proximity_penalty,
    )
    shortest_nodes, shortest_edges = _shortest_edge_path(routed, origin, destination, "baseline_cost")
    shortest = Route(shortest_nodes, shortest_edges, _metrics(routed, shortest_edges))
    candidate_nodes, candidate_edges = _shortest_edge_path(routed, origin, destination, "preference_cost")
    candidate = Route(candidate_nodes, candidate_edges, _metrics(routed, candidate_edges))

    if candidate.edges == shortest.edges:
        return RouteComparison(shortest, None, "No distinct lighting-aware alternative was found.")
    if candidate.metrics.distance_m > shortest.metrics.distance_m * (1 + max_detour_ratio):
        return RouteComparison(shortest, None, "The lighting-aware candidate exceeds the configured detour limit.")
    if candidate.metrics.mapped_light_coverage_pct is None:
        return RouteComparison(shortest, None, "The candidate has no known mapped-light coverage.")
    baseline_coverage = shortest.metrics.mapped_light_coverage_pct
    if baseline_coverage is not None and candidate.metrics.mapped_light_coverage_pct <= baseline_coverage:
        return RouteComparison(shortest, None, "The candidate does not improve mapped-light coverage.")
    return RouteComparison(shortest, candidate, None)
