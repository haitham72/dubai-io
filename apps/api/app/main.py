"""Dubai-io API (Phase 1 slice): Luna on LangGraph, stated-fact memory, and
server-side Google Places / Routes. It also serves the lab at /lab, so a phone
on the same Wi-Fi uses one origin and the keys stay on this machine.

Run: cd apps/api && .venv/Scripts/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
Then open http://<pc-ip>:8000/lab/home-v2-cyan.html
"""
import uuid
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import catalog, google_maps
from .auth import router as auth_router
from .actions import COOKIE, engine, router as action_router
from .config import settings
from .merchant import merchant_pin, router as merchant_router
from .proactive import router as proactive_router
from .profile import router as profile_router
from .recommendations import router as recommendations_router
from .discovery import router as discovery_router
from .tasks import router as tasks_router
from .reading import router as reading_router
from .projects import router as projects_router
from .projects import resolve_context as resolve_project_context
from .tasks import resolve_context as resolve_task_context
from .luna import graph as luna
from .luna.schema import FactKey, FocusContext, TaskFocusContext, ProjectFocusContext

@asynccontextmanager
async def lifespan(_app):
    merchant_pin()  # sandbox merchant PIN: MERCHANT_PIN, or generated into data/merchant.pin
    if settings.widget_port:  # mini-apps on their own origin (rule 10)
        from .widgets import serve_in_background
        serve_in_background("0.0.0.0", settings.widget_port)
    yield


app = FastAPI(title="Dubai-io API", version="0.1.0", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(action_router)
app.include_router(merchant_router)
app.include_router(proactive_router)
app.include_router(profile_router)
app.include_router(recommendations_router)
app.include_router(discovery_router)
app.include_router(tasks_router)
app.include_router(reading_router)
app.include_router(projects_router)


@app.middleware("http")
async def revalidate_app_files(request: Request, call_next):
    """Phones and rehearsal browsers must pick up edited modules: revalidate HTML/JS/CSS (ETag keeps it cheap)."""
    response = await call_next(request)
    if request.url.path.endswith((".html", ".js", ".css", "/")):
        response.headers["Cache-Control"] = "no-cache"
    return response


class TurnIn(BaseModel):
    text: str = Field(min_length=1, max_length=600)
    thread_id: str = Field(default_factory=lambda: uuid.uuid4().hex, max_length=64)
    user_id: str = Field(default="demo-user", max_length=64)
    focus: FocusContext | None = None
    task_focus: TaskFocusContext | None = None
    project_focus: ProjectFocusContext | None = None


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


@app.get("/api/catalog")
def published_catalog():
    """Both clients read the same published fixture catalog; prices stay host-owned."""
    return {"provenance": catalog.PROVENANCE, "as_of": catalog.AS_OF, "providers": [
        {"id": key, "name": name, "service": service,
         "items": [{"id": item, "name": label, "price_aed": price} for item, (label, price) in items.items()],
         "slots": slots}
        for key, (name, service, items, slots) in catalog.PROVIDERS.items()]}


@app.post("/api/luna/turn")
def luna_turn(body: TurnIn, request: Request):
    if not settings.openai_api_key:
        raise HTTPException(503, "OPENAI_API_KEY is not set")
    try:
        owner = engine().store.owner(request.cookies.get(COOKIE))
        context = {"focus": body.focus} if body.focus else {}
        if body.task_focus:
            context["task_context"] = resolve_task_context(engine().store, owner, body.task_focus)
        if body.project_focus:
            context["project_context"] = resolve_project_context(engine().store, owner, body.thread_id, body.project_focus)
        return luna.turn(body.thread_id, owner, body.text, **context)
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
    return {"forgotten": luna.forget_fact(owner, key)}


@app.get("/api/memory/{user_id}", deprecated=True)
def memory(user_id: str, request: Request):
    owner = engine().store.owner(request.cookies.get(COOKIE))
    if user_id != owner:
        raise HTTPException(404, "Memory not found")
    return {"told": luna.facts.current(owner)}


@app.delete("/api/memory/{user_id}/{key}", deprecated=True)
def forget(user_id: str, key: FactKey, request: Request):
    owner = engine().store.owner(request.cookies.get(COOKIE))
    if user_id != owner:
        raise HTTPException(404, "Memory not found")
    return {"forgotten": luna.forget_fact(owner, key)}


@app.post("/api/places/search")
async def places(body: PlacesIn):
    if not settings.google_key:
        raise HTTPException(503, "GOOGLE_PLACES_KEY is not set")
    try:
        return await google_maps.search_places(body.query, body.lat, body.lng)
    except httpx.HTTPStatusError as err:
        raise HTTPException(502, f"Places error {err.response.status_code}") from err


@app.get("/api/places/photo")
async def places_photo(name: str = Query(max_length=1200), w: int = 480):
    try:
        data, kind = await google_maps.place_photo(name, w)
    except ValueError:
        raise HTTPException(400, "Bad photo reference")
    except httpx.HTTPError:
        raise HTTPException(502, "Photo unavailable")
    return Response(data, media_type=kind, headers={"Cache-Control": "private, max-age=3600"})


@app.get("/api/maps/config")
def maps_config(request: Request):
    """Browser key for the interactive in-app Google map. The server Places key is
    lent only to a local preview (localhost) so it never ships to real users."""
    if settings.google_maps_browser_key:
        return {"key": settings.google_maps_browser_key, "source": "browser_key"}
    if request.url.hostname in {"localhost", "127.0.0.1", "::1"} and settings.google_key:
        return {"key": settings.google_key, "source": "local_preview_fallback"}
    raise HTTPException(503, "Interactive map not configured")


@app.get("/api/staticmap")
async def staticmap(c: str = Query(pattern=r"^-?\d+(\.\d+)?,-?\d+(\.\d+)?$"), m: str = Query(default="", max_length=400), z: int | None = Query(default=None, ge=3, le=20), s: str = Query(default="wide", pattern="^(wide|tall)$")):
    """Google map image with up to 9 numbered pins: c=lat,lng · m=lat,lng|lat,lng · z=zoom."""
    try:
        pins = [tuple(float(v) for v in pair.split(",")) for pair in m.split("|") if pair][:9]
        if any(len(p) != 2 or not (-90 <= p[0] <= 90 and -180 <= p[1] <= 180) for p in pins):
            raise ValueError
        center = tuple(float(v) for v in c.split(","))
        data = await google_maps.static_map(center, pins, z, "460x640" if s == "tall" else "640x400")
    except ValueError:
        raise HTTPException(400, "Bad coordinates")
    except httpx.HTTPError:
        raise HTTPException(502, "Map unavailable")
    return Response(data, media_type="image/png", headers={"Cache-Control": "private, max-age=600"})


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
