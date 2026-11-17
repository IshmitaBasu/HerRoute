"""Low-volume, user-triggered place search through a configurable geocoder."""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass

import requests

from src.ingestion.download import PILOT, within


DEFAULT_GEOCODER_URL = "https://nominatim.openstreetmap.org/search"
MIN_REQUEST_INTERVAL_SECONDS = 1.0
_request_lock = threading.Lock()
_last_request_monotonic = 0.0


@dataclass(frozen=True)
class PlaceMatch:
    """A geocoded place that has passed the HerRoute pilot-area check."""

    label: str
    lon: float
    lat: float


def _wait_for_request_slot() -> None:
    global _last_request_monotonic
    with _request_lock:
        remaining = MIN_REQUEST_INTERVAL_SECONDS - (time.monotonic() - _last_request_monotonic)
        if remaining > 0:
            time.sleep(remaining)
        _last_request_monotonic = time.monotonic()


def search_locations(query: str, timeout_seconds: float = 15.0) -> tuple[PlaceMatch, ...]:
    """Find user-requested Berlin locations within the pilot area.

    This function is deliberately for an explicit search submission only. It
    must not be called for autocomplete, bulk geocoding, or background refreshes.
    """
    cleaned_query = query.strip()
    if len(cleaned_query) < 3:
        raise ValueError("Enter at least three characters for each location")
    west, south, east, north = PILOT
    _wait_for_request_slot()
    response = requests.get(
        os.getenv("HERROUTE_GEOCODER_URL", DEFAULT_GEOCODER_URL),
        params={
            "q": f"{cleaned_query}, Berlin, Germany",
            "format": "jsonv2",
            "limit": 5,
            "bounded": 1,
            "viewbox": f"{west},{north},{east},{south}",
        },
        headers={
            "User-Agent": os.getenv("HERROUTE_GEOCODER_USER_AGENT", "HerRoute/0.1 local research prototype"),
            "Accept-Language": "en",
        },
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    matches = response.json()
    if not isinstance(matches, list):
        raise ValueError("Location search returned an unexpected response")
    pilot_matches: list[PlaceMatch] = []
    seen: set[tuple[str, float, float]] = set()
    for match in matches:
        try:
            lon = float(match["lon"])
            lat = float(match["lat"])
            label = str(match["display_name"])
        except (KeyError, TypeError, ValueError):
            continue
        if within(lon, lat, PILOT):
            identifier = (label, lon, lat)
            if identifier not in seen:
                seen.add(identifier)
                pilot_matches.append(PlaceMatch(label=label, lon=lon, lat=lat))
    if pilot_matches:
        return tuple(pilot_matches)
    raise ValueError("No matching location was found inside the Alexanderplatz pilot area")


def resolve_location(query: str, timeout_seconds: float = 15.0) -> PlaceMatch:
    """Resolve the best match for command-line callers.

    The interface uses :func:`search_locations` so people can choose an exact
    address from its candidates instead of silently accepting the first result.
    """
    return search_locations(query, timeout_seconds=timeout_seconds)[0]
