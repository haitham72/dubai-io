"""Dubai-io API (Phase 1 slice): Luna on LangGraph, stated-fact memory, and
server-side Google Places / Routes. It also serves the lab at /lab, so a phone
on the same Wi-Fi uses one origin and the keys stay on this machine.

Run: cd apps/api && .venv/Scripts/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
Then open http://<pc-ip>:8000/lab/home-v2-cyan.html
"""
import uuid

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import google_maps
from .config import settings
from .luna import graph as luna

app = FastAPI(title="Dubai-io API", version="0.1.0")


class TurnIn(BaseModel):
    text: str = Field(min_length=1, max_length=600)
    thread_id: str = Field(default_factory=lambda: uuid.uuid4().hex, max_length=64)
    user_id: str = Field(default="demo-user", max_length=64)


class PlacesIn(BaseModel):
    query: str = Field(min_length=2, max_length=120)
    lat: float | None = None
    lng: float | None = None


class LatLng(BaseModel):
    latitude: float
    longitude: float


class RouteIn(BaseModel):
    origin: LatLng
    destination: LatLng


@app.get("/api/health")
def health():
    return {"ok": True, "luna": settings.luna_model, "effort": settings.luna_effort,
            "openai_key": bool(settings.openai_api_key), "google_key": bool(settings.google_key)}


@app.post("/api/luna/turn")
def luna_turn(body: TurnIn):
    if not settings.openai_api_key:
        raise HTTPException(503, "OPENAI_API_KEY is not set")
    try:
        return luna.turn(body.thread_id, body.user_id, body.text)
    except Exception as err:  # the web falls back to its lab router
        raise HTTPException(502, f"Luna failed: {type(err).__name__}") from err


@app.get("/api/memory/{user_id}")
def memory(user_id: str):
    return {"told": luna.facts.current(user_id)}


@app.delete("/api/memory/{user_id}/{key}")
def forget(user_id: str, key: str):
    return {"forgotten": luna.facts.forget(user_id, key)}


@app.post("/api/places/search")
async def places(body: PlacesIn):
    if not settings.google_key:
        raise HTTPException(503, "GOOGLE_PLACES_KEY is not set")
    try:
        return await google_maps.search_places(body.query, body.lat, body.lng)
    except httpx.HTTPStatusError as err:
        raise HTTPException(502, f"Places error {err.response.status_code}") from err


@app.post("/api/route")
async def route(body: RouteIn):
    if not settings.google_key:
        raise HTTPException(503, "GOOGLE_PLACES_KEY is not set")
    try:
        return await google_maps.route(body.origin.model_dump(), body.destination.model_dump())
    except httpx.HTTPStatusError as err:
        raise HTTPException(502, f"Routes error {err.response.status_code}") from err


@app.get("/")
def root():
    return RedirectResponse("/lab/home-v2-cyan.html")


app.mount("/lab", StaticFiles(directory=settings.lab_dir, html=True), name="lab")
