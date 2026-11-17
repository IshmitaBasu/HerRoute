"""Local HTTP interface for HerRoute's interactive browser experience."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.geocoding.aws_places import autocomplete_addresses, resolve_address
from src.routing.run import compare_points, load_routing_snapshot, route_coordinates


STATIC_DIR = Path(__file__).parent / "static"
app = FastAPI(title="HerRoute", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class RouteRequest(BaseModel):
    origin_place_id: str = Field(min_length=1, max_length=500)
    destination_place_id: str = Field(min_length=1, max_length=500)
    lighting_penalty: float = Field(default=2.0, ge=0, le=3)
    transit_proximity_penalty: float = Field(default=0.0, ge=0, le=3)
    max_detour_pct: int = Field(default=20, ge=0, le=30)


def comparison_payload(graph, comparison) -> dict:
    """Convert routing objects into browser-safe route and metric data."""
    def payload(route):
        if route is None:
            return None
        return {"coordinates": route_coordinates(graph, route), "metrics": asdict(route.metrics)}

    return {
        "shortest": payload(comparison.shortest),
        "lighting_aware": payload(comparison.lighting_aware),
        "alternative_unavailable_reason": comparison.alternative_unavailable_reason,
    }


@app.get("/")
def index():
    """Serve the local single-page interface."""
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health():
    """Provide a credential-free liveness check for container hosts."""
    return {"status": "ok", "routing_snapshot_available": Path("data/raw/walk.graphml").exists() and Path("data/processed/segment_features.parquet").exists()}


@app.get("/api/suggest")
def suggest(q: str = Query(min_length=0, max_length=200)):
    """Return live, pilot-filtered address choices after three characters."""
    try:
        suggestions = autocomplete_addresses(q)
    except ValueError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return [{"place_id": item.place_id, "label": item.label} for item in suggestions]


@app.post("/api/routes")
def routes(request: RouteRequest):
    """Resolve selected addresses and calculate both walking routes."""
    try:
        origin = resolve_address(request.origin_place_id)
        destination = resolve_address(request.destination_place_id)
        graph, features = load_routing_snapshot()
        comparison = compare_points(
            graph,
            features,
            origin.lon,
            origin.lat,
            destination.lon,
            destination.lat,
            lighting_penalty=request.lighting_penalty,
            transit_proximity_penalty=request.transit_proximity_penalty,
            max_detour_ratio=request.max_detour_pct / 100,
        )
    except (FileNotFoundError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {
        "origin": asdict(origin),
        "destination": asdict(destination),
        "comparison": comparison_payload(graph, comparison),
    }
