"""Dubai-io API (Phase 1 slice): Luna on LangGraph, stated-fact memory, and
server-side Google Places / Routes. It also serves the lab at /lab, so a phone
on the same Wi-Fi uses one origin and the keys stay on this machine.

Run: cd apps/api && .venv/Scripts/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
Then open http://<pc-ip>:8000/lab/home-v2-cyan.html
"""
import uuid

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import google_maps
from .auth import router as auth_router
from .actions import COOKIE, engine, router as action_router
from .config import settings
from .merchant import merchant_pin, router as merchant_router
from .luna import graph as luna
from .luna.schema import FactKey

app = FastAPI(title="Dubai-io API", version="0.1.0")
app.include_router(auth_router)
app.include_router(action_router)
app.include_router(merchant_router)


@app.middleware("http")
async def revalidate_app_files(request: Request, call_next):
    """Phones and rehearsal browsers must pick up edited modules: revalidate HTML/JS/CSS (ETag keeps it cheap)."""
    response = await call_next(request)
    if request.url.path.endswith((".html", ".js", ".css", "/")):
        response.headers["Cache-Control"] = "no-cache"
    return response


@app.on_event("startup")
def _startup():
    merchant_pin()  # sandbox merchant PIN: MERCHANT_PIN, or generated into data/merchant.pin
    if settings.widget_port:  # mini-apps on their own origin (rule 10)
        from .widgets import serve_in_background
        serve_in_background("0.0.0.0", settings.widget_port)


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
            "openai_key": bool(settings.openai_api_key), "google_key": bool(settings.google_key), "widget_port": settings.widget_port}


@app.post("/api/luna/turn")
def luna_turn(body: TurnIn, request: Request):
    if not settings.openai_api_key:
        raise HTTPException(503, "OPENAI_API_KEY is not set")
    try:
        owner = engine().store.owner(request.cookies.get(COOKIE)) if request.cookies.get(COOKIE) else body.user_id
        return luna.turn(body.thread_id, owner, body.text)
    except HTTPException:
        raise
    except Exception as err:  # the web falls back to its lab router
        raise HTTPException(502, f"Luna failed: {type(err).__name__}") from err


class FactEdit(BaseModel):
    value: str = Field(min_length=1, max_length=80)


@app.get("/api/session/memory")
def session_memory(request: Request):
    owner = engine().store.owner(request.cookies.get(COOKIE))
    return {"told": luna.facts.current(owner)}


@app.put("/api/session/memory/{key}")
def edit_session_fact(key: FactKey, body: FactEdit, request: Request):
    owner = engine().store.owner(request.cookies.get(COOKIE))
    value = body.value.strip()
    if not value:
        raise HTTPException(422, "Enter a value")
    return {"fact": luna.facts.add(owner, key, value, f"User edited saved detail: {key}={value}")}


@app.delete("/api/session/memory/{key}")
def forget_session_fact(key: FactKey, request: Request):
    owner = engine().store.owner(request.cookies.get(COOKIE))
    return {"forgotten": luna.facts.forget(owner, key)}


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
    return RedirectResponse("/index.html")


app.mount("/lab", StaticFiles(directory=settings.web_dir, html=True), name="lab")
app.mount("/", StaticFiles(directory=settings.web_dir, html=True), name="web")
