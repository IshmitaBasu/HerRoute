import networkx as nx
import pandas as pd
import pytest

from src.routing.engine import compare_routes
from src.routing.run import comparison_summary, nearest_graph_node, route_coordinates, validate_pilot_point


def graph_with_two_routes(alternative_length=110.0):
    graph = nx.MultiDiGraph()
    graph.add_edge("a", "b", key=0)
    graph.add_edge("b", "d", key=0)
    graph.add_edge("a", "c", key=0)
    graph.add_edge("c", "d", key=0)
    rows = []
    for u, v, length, coverage in [
        ("a", "b", 100.0, 0.0),
        ("b", "d", 100.0, 0.0),
        ("a", "c", alternative_length, 100.0),
        ("c", "d", alternative_length, 100.0),
    ]:
        rows.append(
            {
                "segment_id": f"{u}:{v}:0",
                "length_m": length,
                "mapped_light_coverage_pct": coverage,
                "nearest_transit_stop_m": 20.0,
            }
        )
    return graph, pd.DataFrame(rows)


def test_returns_feasible_distinct_lighting_aware_route():
    graph, features = graph_with_two_routes()

    result = compare_routes(graph, features, "a", "d")

    assert result.shortest.metrics.distance_m == 200
    assert result.shortest.metrics.mapped_light_coverage_pct == 0
    assert result.lighting_aware is not None
    assert result.lighting_aware.metrics.distance_m == 220
    assert result.lighting_aware.metrics.mapped_light_coverage_pct == 100
    assert result.alternative_unavailable_reason is None


def test_rejects_candidate_over_detour_limit():
    graph, features = graph_with_two_routes(alternative_length=130)

    result = compare_routes(graph, features, "a", "d")

    assert result.lighting_aware is None
    assert result.alternative_unavailable_reason == "The lighting-aware candidate exceeds the configured detour limit."


def test_reports_when_shortest_route_is_already_lighting_aware():
    graph = nx.MultiDiGraph()
    graph.add_edge("a", "b", key=0)
    graph.add_edge("b", "d", key=0)
    features = pd.DataFrame(
        [
            {"segment_id": "a:b:0", "length_m": 100, "mapped_light_coverage_pct": 100, "nearest_transit_stop_m": 10},
            {"segment_id": "b:d:0", "length_m": 100, "mapped_light_coverage_pct": 100, "nearest_transit_stop_m": 10},
        ]
    )

    result = compare_routes(graph, features, "a", "d")

    assert result.lighting_aware is None
    assert result.alternative_unavailable_reason == "No distinct lighting-aware alternative was found."


def test_transit_preference_can_choose_a_closer_mapped_stop_route():
    graph = nx.MultiDiGraph()
    for u, v in [("a", "b"), ("b", "d"), ("a", "c"), ("c", "d")]:
        graph.add_edge(u, v, key=0)
    features = pd.DataFrame(
        [
            {"segment_id": "a:b:0", "length_m": 100, "mapped_light_coverage_pct": 0, "nearest_transit_stop_m": 200},
            {"segment_id": "b:d:0", "length_m": 100, "mapped_light_coverage_pct": 0, "nearest_transit_stop_m": 200},
            {"segment_id": "a:c:0", "length_m": 110, "mapped_light_coverage_pct": 100, "nearest_transit_stop_m": 10},
            {"segment_id": "c:d:0", "length_m": 110, "mapped_light_coverage_pct": 100, "nearest_transit_stop_m": 10},
        ]
    )

    result = compare_routes(graph, features, "a", "d", lighting_penalty=0, transit_proximity_penalty=2)

    assert result.lighting_aware is not None
    assert result.lighting_aware.nodes == ("a", "c", "d")


def test_rejects_identical_endpoints_and_unknown_nodes():
    graph, features = graph_with_two_routes()
    with pytest.raises(ValueError, match="different"):
        compare_routes(graph, features, "a", "a")
    with pytest.raises(ValueError, match="not present"):
        compare_routes(graph, features, "missing", "d")


def test_rejects_coordinates_outside_pilot_area():
    with pytest.raises(ValueError, match="pilot area"):
        validate_pilot_point(13.5, 52.6)


def test_snaps_to_nearest_graph_node_without_optional_dependencies():
    graph = nx.MultiDiGraph()
    graph.add_node("near", x=13.405, y=52.518)
    graph.add_node("far", x=13.420, y=52.530)

    assert nearest_graph_node(graph, 13.4051, 52.5181) == "near"


def test_summary_hides_network_identifiers():
    graph, features = graph_with_two_routes()
    summary = comparison_summary(compare_routes(graph, features, "a", "d"))

    assert summary["shortest"]["edge_count"] == 2
    assert "nodes" not in summary["shortest"]
    assert summary["lighting_aware"]["metrics"]["mapped_light_coverage_pct"] == 100


def test_route_coordinates_are_wgs84_pairs():
    graph, features = graph_with_two_routes()
    for index, node in enumerate(graph.nodes):
        graph.nodes[node]["x"] = 13.4 + index / 1000
        graph.nodes[node]["y"] = 52.5 + index / 1000
    route = compare_routes(graph, features, "a", "d").shortest

    coordinates = route_coordinates(graph, route)

    assert coordinates[0] == [13.4, 52.5]
    assert len(coordinates) == len(route.nodes)
