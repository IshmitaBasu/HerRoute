"""AWS Location Places V2 support for interactive address selection."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import boto3
import requests
from botocore.exceptions import BotoCoreError, ClientError

from src.geocoding.nominatim import PlaceMatch
from src.ingestion.download import PILOT, within


DEFAULT_REGION = "eu-central-1"
MAX_SUGGESTIONS = 5


@dataclass(frozen=True)
class AddressSuggestion:
    """One address offered by AWS Location autocomplete."""

    place_id: str
    label: str


def _client():
    """Use the user's existing AWS CLI login in the Frankfurt region by default."""
    return boto3.client("geo-places", region_name=os.getenv("AWS_REGION", DEFAULT_REGION))


def _api_key() -> str | None:
    """Return a scoped Amazon Location API key when a hosted service provides one."""
    value = os.getenv("HERROUTE_LOCATION_API_KEY", "").strip()
    return value or None


def _places_url(path: str) -> str:
    region = os.getenv("AWS_REGION", DEFAULT_REGION)
    return f"https://places.geo.{region}.amazonaws.com{path}"


def _api_key_autocomplete(query: str, key: str) -> dict[str, Any]:
    """Call Places V2 without exposing a hosted service's API key to browsers."""
    response = requests.post(
        _places_url("/v2/autocomplete"),
        params={"key": key},
        json={
            "QueryText": query,
            "MaxResults": MAX_SUGGESTIONS,
            "Language": "de",
            "IntendedUse": "SingleUse",
            "Filter": {"BoundingBox": list(PILOT), "IncludeCountries": ["DE"]},
        },
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


def _api_key_get_place(place_id: str, key: str) -> dict[str, Any]:
    response = requests.get(
        _places_url(f"/v2/place/{quote(place_id, safe='')}"),
        params={"key": key, "language": "de", "intended-use": "SingleUse"},
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


def autocomplete_addresses(query: str, client: Any | None = None) -> list[AddressSuggestion]:
    """Return address suggestions after at least three typed characters.

    Results are restricted to the existing Berlin pilot boundary and are used
    only for the live selection interaction (AWS ``SingleUse`` terms).
    """
    cleaned_query = query.strip()
    if len(cleaned_query) < 3:
        return []
    try:
        if client is not None:
            response = client.autocomplete(
                QueryText=cleaned_query,
                MaxResults=MAX_SUGGESTIONS,
                Language="de",
                IntendedUse="SingleUse",
                Filter={"BoundingBox": list(PILOT), "IncludeCountries": ["DE"]},
            )
        elif key := _api_key():
            response = _api_key_autocomplete(cleaned_query, key)
        else:
            response = _client().autocomplete(
                QueryText=cleaned_query,
                MaxResults=MAX_SUGGESTIONS,
                Language="de",
                IntendedUse="SingleUse",
                Filter={"BoundingBox": list(PILOT), "IncludeCountries": ["DE"]},
            )
    except requests.RequestException as error:
        raise ValueError("Address suggestions are unavailable; check the hosted Location API key.") from error
    except (BotoCoreError, ClientError) as error:
        raise ValueError(f"Address suggestions are unavailable: {error}") from error

    suggestions: list[AddressSuggestion] = []
    for item in response.get("ResultItems", []):
        place_id = item.get("PlaceId")
        label = item.get("Address", {}).get("Label") or item.get("Title")
        if isinstance(place_id, str) and isinstance(label, str):
            suggestions.append(AddressSuggestion(place_id=place_id, label=label))
    return suggestions


def resolve_address(place_id: str, client: Any | None = None) -> PlaceMatch:
    """Resolve a selected suggestion to coordinates for the route engine."""
    try:
        if client is not None:
            response = client.get_place(
                PlaceId=place_id,
                Language="de",
                IntendedUse="SingleUse",
            )
        elif key := _api_key():
            response = _api_key_get_place(place_id, key)
        else:
            response = _client().get_place(
                PlaceId=place_id,
                Language="de",
                IntendedUse="SingleUse",
            )
    except requests.RequestException as error:
        raise ValueError("Selected address is unavailable; check the hosted Location API key.") from error
    except (BotoCoreError, ClientError) as error:
        raise ValueError(f"Selected address is unavailable: {error}") from error

    position = response.get("Position")
    label = response.get("Address", {}).get("Label")
    if not isinstance(position, list) or len(position) != 2 or not isinstance(label, str):
        raise ValueError("Selected address did not include a valid map position")
    try:
        lon, lat = float(position[0]), float(position[1])
    except (TypeError, ValueError) as error:
        raise ValueError("Selected address did not include numeric map coordinates") from error
    if not within(lon, lat, PILOT):
        raise ValueError("Selected address is outside the Alexanderplatz pilot area")
    return PlaceMatch(label=label, lon=lon, lat=lat)
