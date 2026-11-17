"""AWS Location Places V2 support for interactive address selection."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import boto3
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


def autocomplete_addresses(query: str, client: Any | None = None) -> list[AddressSuggestion]:
    """Return address suggestions after at least three typed characters.

    Results are restricted to the existing Berlin pilot boundary and are used
    only for the live selection interaction (AWS ``SingleUse`` terms).
    """
    cleaned_query = query.strip()
    if len(cleaned_query) < 3:
        return []
    try:
        response = (client or _client()).autocomplete(
            QueryText=cleaned_query,
            MaxResults=MAX_SUGGESTIONS,
            Language="de",
            IntendedUse="SingleUse",
            Filter={"BoundingBox": list(PILOT), "IncludeCountries": ["DE"]},
        )
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
        response = (client or _client()).get_place(
            PlaceId=place_id,
            Language="de",
            IntendedUse="SingleUse",
        )
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
