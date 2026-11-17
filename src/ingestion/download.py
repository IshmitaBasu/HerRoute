"""Download a bounded, validated candidate snapshot. Run with python -m src.ingestion.download."""

import csv
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile

import networkx as nx
import osmnx as ox
import requests
from osmnx._errors import ResponseStatusCodeError

BOUNDS = (13.390, 52.512, 13.435, 52.533)  # buffered candidate: west, south, east, north
PILOT = (13.395, 52.515, 13.430, 52.530)
OUT = Path("data/raw")
WFS = "https://gdi.berlin.de/services/wfs/beleuchtung"
GTFS = "https://unternehmen.vbb.de/gtfs"
HEADERS = {"User-Agent": "HerRoute research prototype (public data ingestion)"}
NETWORK_MAX_ATTEMPTS = 4
NETWORK_RETRY_DELAY_SECONDS = 15


def within(lon, lat, bounds=BOUNDS):
    w, s, e, n = bounds
    return w <= lon <= e and s <= lat <= n


def checksum(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_lights(directory):
    params = {"service": "WFS", "version": "1.0.0", "request": "GetFeature",
              "typeName": "beleuchtung:beleuchtung", "outputFormat": "application/json",
              "srsName": "EPSG:4326", "bbox": ",".join(map(str, BOUNDS)) + ",EPSG:4326"}
    response = requests.get(WFS, params=params, headers=HEADERS, timeout=120)
    response.raise_for_status()
    data = response.json()
    features = data.get("features", [])
    if data.get("type") != "FeatureCollection" or not features:
        raise ValueError("Lighting response is empty or not a feature collection")
    matched = data.get("numberMatched", data.get("totalFeatures"))
    if isinstance(matched, int) and matched != len(features):
        raise ValueError("Lighting response is truncated; paging is required")
    service_timestamp = data.get("timeStamp")
    selected = []
    for feature in features:
        geometry = feature.get("geometry") or {}
        coordinates = geometry.get("coordinates", [])
        points = [coordinates] if geometry.get("type") == "Point" else coordinates if geometry.get("type") == "MultiPoint" else []
        if not points or any(len(point) < 2 or not within(*point[:2], bounds=(13.0, 52.3, 13.8, 52.7)) for point in points):
            raise ValueError("Unexpected lighting geometry or coordinates outside Berlin")
        if all(within(*point[:2]) for point in points):
            selected.append(feature)
    if not selected:
        raise ValueError("No lights inside requested bounds")
    data["features"] = selected
    data.pop("bbox", None)
    for key in ("totalFeatures", "numberMatched", "numberReturned"):
        data.pop(key, None)
    path = directory / "lights.geojson"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return {"count": len(selected), "returned_count": len(features), "service_response_timestamp": service_timestamp,
            "url": response.url, "etag": response.headers.get("ETag"),
            "last_modified": response.headers.get("Last-Modified"), "file": path.name, "sha256": checksum(path)}


def download_stops(directory):
    response = requests.get(GTFS, headers=HEADERS, timeout=(30, 180), stream=True)
    response.raise_for_status()
    zip_path = directory / "vbb_gtfs.zip"
    with zip_path.open("wb") as target:
        for chunk in response.iter_content(1024 * 1024):
            target.write(chunk)
    with ZipFile(zip_path) as archive:
        with archive.open("stops.txt") as source:
            import io
            reader = csv.DictReader(io.TextIOWrapper(source, encoding="utf-8-sig", newline=""))
            if not {"stop_id", "stop_name", "stop_lat", "stop_lon"}.issubset(reader.fieldnames or []):
                raise ValueError("GTFS missing required stop fields")
            fields = reader.fieldnames
            selected = []
            for row in reader:
                try:
                    lon, lat = float(row["stop_lon"]), float(row["stop_lat"])
                except (ValueError, TypeError):
                    continue
                if within(lon, lat):
                    selected.append(row)
    if not selected:
        raise ValueError("No GTFS stops in buffered pilot")
    path = directory / "stops.csv"
    with path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=fields)
        writer.writeheader()
        writer.writerows(selected)
    return {"count": len(selected), "url": response.url, "last_modified": response.headers.get("Last-Modified"),
            "etag": response.headers.get("ETag"), "file": path.name, "sha256": checksum(path),
            "archive_sha256": checksum(zip_path)}


def download_network(
    directory: Path,
    max_attempts: int = NETWORK_MAX_ATTEMPTS,
    sleep=time.sleep,
):
    """Download the network with bounded retries for public Overpass capacity errors."""
    if max_attempts < 1:
        raise ValueError("Network download requires at least one attempt")
    ox.settings.requests_timeout = 180
    ox.settings.http_user_agent = HEADERS["User-Agent"]
    for attempt in range(1, max_attempts + 1):
        try:
            graph = ox.graph_from_bbox(BOUNDS, network_type="walk", retain_all=True)
            break
        except (ResponseStatusCodeError, requests.RequestException) as error:
            if attempt == max_attempts:
                raise RuntimeError(
                    f"Walking-network download failed after {max_attempts} attempts; "
                    "the public Overpass service may be at capacity."
                ) from error
            delay_seconds = NETWORK_RETRY_DELAY_SECONDS * 2 ** (attempt - 1)
            print(
                f"Walking-network download attempt {attempt}/{max_attempts} failed: {error}. "
                f"Retrying in {delay_seconds} seconds...",
                flush=True,
            )
            sleep(delay_seconds)
    if not graph.number_of_nodes() or not graph.number_of_edges():
        raise ValueError("Empty walking network")
    for _, attrs in graph.nodes(data=True):
        if not within(attrs["x"], attrs["y"]):
            raise ValueError("Network node outside requested bounds")
    components = sorted((len(c) for c in nx.weakly_connected_components(graph)), reverse=True)
    path = directory / "walk.graphml"
    ox.save_graphml(graph, path)
    return {"nodes": graph.number_of_nodes(), "edges": graph.number_of_edges(),
            "weak_components": len(components), "largest_component_nodes": components[0],
            "url": ox.settings.overpass_url, "file": path.name, "sha256": checksum(path)}


def main(output: Path | None = None):
    # A manifest is written only after every source has succeeded. A failed run must not
    # leave a manifest that could be mistaken for a validated snapshot.
    directory = output or OUT
    directory.mkdir(parents=True, exist_ok=True)
    manifest_path = directory / "manifest.json"
    manifest_path.unlink(missing_ok=True)
    result = {"retrieved_utc": datetime.now(timezone.utc).isoformat(), "pilot_bounds_wgs84": PILOT,
              "download_bounds_wgs84": BOUNDS, "source_data_dates": "unknown unless provided by source"}
    for key, function in (("lights", download_lights), ("stops", download_stops), ("network", download_network)):
        print(f"Downloading {key}...", flush=True)
        result[key] = function(directory)
        print(json.dumps(result[key]), flush=True)
    manifest_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Validated source manifest: {manifest_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUT, help="Directory for this candidate raw snapshot")
    arguments = parser.parse_args()
    main(arguments.output)
