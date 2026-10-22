"""Owner-bound discovery over a fresh provider batch, with no listing persistence.

The client supplies intent/constraints, never candidate attributes. Topics used
for scoring provider types are transient; feedback still records the app-owned
category the user actually selected, not a copy of Google's listing attributes.
This endpoint discovers places. It cannot verify stock, dates or execute orders.
"""
from math import asin, cos, isfinite, radians, sin, sqrt
from typing import Literal

import httpx
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import Field, model_validator

from . import google_maps
from .config import settings
from .recommendations import Candidate, DAY, Rank, Strict, clock, owned

router = APIRouter(tags=["discovery"])
QUERIES = {
    "all": {None: "popular places"},
    "food": {None: "restaurants", "Restaurants": "restaurants", "Seafood": "seafood restaurants", "Delivery": "food delivery restaurants"},
    "coffee": {None: "coffee shops"}, "barber": {None: "barbers"},
    "pets": {None: "pet services", "Vet": "veterinary clinic", "24h": "24-hour veterinary clinic", "Pet shop": "pet shop",
             "Boarding": "pet boarding", "Grooming": "pet grooming", "Photo": "pet photography"},
    "home-help": {None: "home help services", "Maid": "maid services", "Cleaning": "home cleaning services", "Visa services": "visa typing services"},
    "laundry": {None: "laundry"}, "clothing": {None: "clothing stores"},
    "fix-it": {None: "home repair services", "AC": "air conditioning repair", "Plumbing": "plumber", "Electrical": "electrician"},
}
BASE_TOPICS = {"food":"food.restaurants", "coffee":"food.cafes", "pets":"pets.care", "home-help":"services.cleaning",
               "laundry":"services.laundry", "clothing":"shopping.clothing", "fix-it":"services.repairs"}
TYPE_TOPICS = {"seafood_restaurant":"food.seafood", "restaurant":"food.restaurants", "cafe":"food.cafes", "coffee_shop":"food.cafes",
               "laundry":"services.laundry", "clothing_store":"shopping.clothing", "pet_store":"pets.care",
               "veterinary_care":"pets.care", "plumber":"services.repairs", "electrician":"services.repairs"}


class PlaceDiscovery(Strict):
    session_id: str = Field(min_length=8, max_length=64)
    category: str = "all"
    subcategory: str | None = None
    lat: float = Field(default=25.0805, ge=-90, le=90, allow_inf_nan=False)
    lng: float = Field(default=55.1403, ge=-180, le=180, allow_inf_nan=False)
    radius_km: float = Field(default=10, ge=.5, le=25, allow_inf_nan=False)
    open_now: bool = False
    sort: Literal["recommended", "closest"] = "recommended"
    query: str | None = Field(default=None, max_length=60, pattern=r"^[\w '&-]+$")  # e.g. a dish: "lasagna"

    @model_validator(mode="after")
    def reviewed_context(self):
        if self.category not in QUERIES or self.subcategory not in QUERIES[self.category]:
            raise ValueError("Choose a reviewed category and subcategory")
        return self


def distance_km(lat, lng, p):
    try:
        plat, plng = float(p["lat"]), float(p["lng"])
    except (KeyError, TypeError, ValueError):
        return None
    if not isfinite(plat) or not isfinite(plng) or not (-90 <= plat <= 90 and -180 <= plng <= 180):
        return None
    a = sin(radians(plat-lat)/2)**2 + cos(radians(lat))*cos(radians(plat))*sin(radians(plng-lng)/2)**2
    return 6371 * 2 * asin(sqrt(min(1,max(0,a))))


def place_topics(place, body):
    types = set(place.get("types") or []) | {place.get("type")}
    topics = {TYPE_TOPICS[t] for t in types if t in TYPE_TOPICS}
    if any(t and t.endswith("_restaurant") for t in types):
        topics.add("food.restaurants")
    # The context is an app-selected topic, not a retained provider attribute.
    base = BASE_TOPICS.get(body.category)
    if base:
        topics.add(base)
    if body.category == "pets":
        topics.add({"Grooming":"pets.grooming", "Boarding":"pets.boarding"}.get(body.subcategory,"pets.care"))
    return sorted(topics)


def matches_type(place, body):
    """Known type constraints fail closed; a text-search hit is not type proof."""
    types = set(place.get("types") or []) | {place.get("type")}
    if body.category == "coffee":
        return bool(types & {"cafe","coffee_shop"})
    if body.category == "food":
        return "seafood_restaurant" in types if body.subcategory == "Seafood" else any(t == "restaurant" or t and t.endswith("_restaurant") for t in types)
    if body.category == "pets" and body.subcategory in {"Vet","24h"}:
        return "veterinary_care" in types
    return True


def search_text(body):
    """The reviewed category query, narrowed by a specific dish/item when one was asked for."""
    query = (body.query or "").strip()
    if not query:
        return QUERIES[body.category][body.subcategory]
    return f"{query} restaurant" if body.category == "food" else f"{query} {QUERIES[body.category][body.subcategory]}"


@router.post("/api/discovery/places")
async def discover_places(body: PlaceDiscovery, request: Request, response: Response):
    rec, owner = owned(request)  # Establish ownership before a paid provider call.
    if not settings.google_key:
        raise HTTPException(503,"Live places are not configured")
    try:
        batch = await google_maps.search_places(search_text(body),body.lat,body.lng,
                                               radius_m=int(body.radius_km*1000),limit=20)
    except httpx.HTTPError as err:
        raise HTTPException(502,"Live places are unavailable. Try again.") from err
    # Reload dismissals and interests after the network wait: a correction during
    # provider retrieval must take effect before scoring this request.
    with rec.store.lock:
        hidden = {row[0] for row in rec.store.db.execute("""SELECT entity_id FROM recommendation_events
            WHERE owner=? AND kind='dismiss' AND received_at>? AND expires_at>?""", (owner,clock()-7*DAY,clock())).fetchall()}
        rec.store.db.commit()
    eligible, excluded, seen = [], {"distance_unknown":0,"outside_radius":0,"not_open":0,"type_unverified":0,"dismissed":0}, set()
    for place in batch["places"]:
        pid = place.get("id")
        if not pid or pid in seen:
            continue
        seen.add(pid)
        km = distance_km(body.lat,body.lng,place)
        why = "dismissed" if "g:"+pid in hidden else "distance_unknown" if km is None else "outside_radius" if km > body.radius_km else (
              "not_open" if body.open_now and place.get("open_now") is not True else "type_unverified" if not matches_type(place,body) else None)
        if why:
            excluded[why] += 1
            continue
        eligible.append({**place,"distance_km":round(km,2),"_distance":km,"_topics":place_topics(place,body)})
    eligible.sort(key=lambda p:p["_distance"])
    candidates = [Candidate(id="g:"+p["id"],topics=p["_topics"]) for p in eligible]
    intent = "food.seafood" if body.category == "food" and body.subcategory == "Seafood" else BASE_TOPICS.get(body.category)
    ranked = rec.rank(owner,Rank(session_id=body.session_id,surface="maps",intent=intent,sort=body.sort,candidates=candidates),
                      practical={"g:"+p["id"]:1-p["_distance"]/body.radius_km for p in eligible},variety=True)
    by_id = {"g:"+p["id"]:p for p in eligible}
    result = []
    for row in ranked["results"]:
        place = by_id[row["id"]]
        result.append({k:v for k,v in place.items() if not k.startswith("_")} | {"recommendation":row})
    response.headers["Cache-Control"] = "private, no-store"
    return {"places":result,"as_of":batch["as_of"],"attribution":"Google","cache":"none",
            "run_id":ranked["run_id"],"ranker_version":ranked["ranker_version"],"sort":body.sort,
            "constraints":{"radius_km":body.radius_km,"open_now":body.open_now},"excluded":excluded,
            "notice":"Search matches do not verify 24-hour coverage." if body.subcategory == "24h" else None}
