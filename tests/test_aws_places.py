from src.geocoding.aws_places import autocomplete_addresses, resolve_address


class PlacesClient:
    def autocomplete(self, **kwargs):
        self.autocomplete_kwargs = kwargs
        return {
            "ResultItems": [
                {"PlaceId": "first", "Address": {"Label": "Rosa-Luxemburg-Straße 1, Berlin"}},
                {"PlaceId": "second", "Title": "Rosa-Luxemburg-Straße, Berlin"},
            ]
        }

    def get_place(self, **kwargs):
        self.get_place_kwargs = kwargs
        return {"Position": [13.41, 52.525], "Address": {"Label": "Rosa-Luxemburg-Straße 1, Berlin"}}


class HttpResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def test_autocomplete_waits_for_three_characters_and_limits_the_pilot_area():
    client = PlacesClient()

    assert autocomplete_addresses("ro", client=client) == []
    suggestions = autocomplete_addresses("rosa", client=client)

    assert [suggestion.place_id for suggestion in suggestions] == ["first", "second"]
    assert client.autocomplete_kwargs["Filter"]["BoundingBox"] == [13.395, 52.515, 13.43, 52.53]
    assert client.autocomplete_kwargs["IntendedUse"] == "SingleUse"


def test_selected_address_returns_a_routeable_pilot_coordinate():
    client = PlacesClient()

    match = resolve_address("first", client=client)

    assert match.label == "Rosa-Luxemburg-Straße 1, Berlin"
    assert (match.lon, match.lat) == (13.41, 52.525)
    assert client.get_place_kwargs["PlaceId"] == "first"


def test_hosted_api_key_is_sent_server_side_for_places_calls(monkeypatch):
    captured = {}

    def fake_post(url, **kwargs):
        captured["post_url"] = url
        captured["post"] = kwargs
        return HttpResponse({"ResultItems": [{"PlaceId": "chosen", "Title": "Alexanderplatz"}]})

    def fake_get(url, **kwargs):
        captured["get_url"] = url
        captured["get"] = kwargs
        return HttpResponse(
            {"Position": [13.405, 52.518], "Address": {"Label": "Alexanderplatz, Berlin"}}
        )

    monkeypatch.setenv("HERROUTE_LOCATION_API_KEY", "scoped-key")
    monkeypatch.setattr("src.geocoding.aws_places.requests.post", fake_post)
    monkeypatch.setattr("src.geocoding.aws_places.requests.get", fake_get)

    suggestions = autocomplete_addresses("alex")
    place = resolve_address("chosen")

    assert suggestions[0].place_id == "chosen"
    assert place.label == "Alexanderplatz, Berlin"
    assert captured["post_url"].endswith("/v2/autocomplete")
    assert captured["post"]["params"] == {"key": "scoped-key"}
    assert captured["post"]["json"]["IntendedUse"] == "SingleUse"
    assert captured["get_url"].endswith("/v2/place/chosen")
    assert captured["get"]["params"]["key"] == "scoped-key"
