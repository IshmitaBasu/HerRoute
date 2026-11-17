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
