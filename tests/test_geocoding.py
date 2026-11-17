import pytest

from src.geocoding.nominatim import resolve_location, search_locations


class Response:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def test_returns_all_valid_locations_inside_pilot(monkeypatch):
    captured = {}

    def fake_get(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return Response(
            [
                {"display_name": "Outside", "lon": "13.5", "lat": "52.6"},
                {"display_name": "Alexanderplatz station", "lon": "13.405", "lat": "52.518"},
                {"display_name": "Alexanderplatz address", "lon": "13.406", "lat": "52.519"},
            ]
        )

    monkeypatch.setattr("src.geocoding.nominatim.requests.get", fake_get)
    monkeypatch.setattr("src.geocoding.nominatim._last_request_monotonic", 0.0)

    results = search_locations("Alexanderplatz")

    assert [result.label for result in results] == ["Alexanderplatz station", "Alexanderplatz address"]
    assert results[0].lon == 13.405
    assert captured["params"]["bounded"] == 1
    assert captured["params"]["limit"] == 5


def test_rejects_short_or_out_of_pilot_search(monkeypatch):
    with pytest.raises(ValueError, match="three characters"):
        resolve_location("ab")

    monkeypatch.setattr("src.geocoding.nominatim.requests.get", lambda *args, **kwargs: Response([]))
    monkeypatch.setattr("src.geocoding.nominatim._last_request_monotonic", 0.0)
    with pytest.raises(ValueError, match="pilot area"):
        resolve_location("No match")


def test_resolve_location_keeps_first_result_for_command_line_callers(monkeypatch):
    monkeypatch.setattr(
        "src.geocoding.nominatim.search_locations",
        lambda query, timeout_seconds: (
            type("Match", (), {"label": "First", "lon": 13.405, "lat": 52.518})(),
        ),
    )

    result = resolve_location("Alexanderplatz")

    assert result.label == "First"
