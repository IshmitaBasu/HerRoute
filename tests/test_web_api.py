import networkx as nx
import pandas as pd
import httpx
import pytest

from src.geocoding.aws_places import AddressSuggestion
from src.geocoding.nominatim import PlaceMatch
from src.web import app as web


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_suggest_returns_browser_safe_address_choices(monkeypatch):
    monkeypatch.setattr(
        web,
        "autocomplete_addresses",
        lambda query: [AddressSuggestion(place_id="rosa", label="Rosa-Luxemburg-Straße 1, Berlin")],
    )
    transport = httpx.ASGITransport(app=web.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/suggest", params={"q": "rosa"})

    assert response.status_code == 200
    assert response.json() == [{"place_id": "rosa", "label": "Rosa-Luxemburg-Straße 1, Berlin"}]


@pytest.mark.anyio
async def test_routes_resolves_selected_places_and_returns_map_geometry(monkeypatch):
    graph = nx.MultiDiGraph()
    graph.add_node("origin", x=13.405, y=52.518)
    graph.add_node("destination", x=13.423, y=52.526)
    graph.add_edge("origin", "destination", key=0)
    features = pd.DataFrame(
        [
            {
                "segment_id": "origin:destination:0",
                "length_m": 200.0,
                "mapped_light_coverage_pct": 80.0,
                "nearest_transit_stop_m": 25.0,
            }
        ]
    )
    places = {
        "from": PlaceMatch("From address", 13.405, 52.518),
        "to": PlaceMatch("To address", 13.423, 52.526),
    }
    monkeypatch.setattr(web, "resolve_address", lambda place_id: places[place_id])
    monkeypatch.setattr(web, "load_routing_snapshot", lambda: (graph, features))
    transport = httpx.ASGITransport(app=web.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/routes",
            json={"origin_place_id": "from", "destination_place_id": "to", "lighting_penalty": 2, "max_detour_pct": 20},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["origin"]["label"] == "From address"
    assert payload["comparison"]["shortest"]["coordinates"] == [[13.405, 52.518], [13.423, 52.526]]
    assert payload["comparison"]["lighting_aware"] is None
