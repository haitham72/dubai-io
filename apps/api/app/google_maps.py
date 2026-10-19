"""Server-side Google Maps Platform calls. The key never leaves the server.
Places results are returned uncached, with the attribution the terms require,
and the live UI must show them on a Google map (Places policy)."""
from datetime import datetime, timezone

import re

import httpx

from .config import settings

HOME = {"latitude": 25.0805, "longitude": 55.1403}  # Dubai Marina, the area the user told us
PLACE_FIELDS = ",".join(f"places.{f}" for f in ("id", "displayName", "rating", "userRatingCount", "location", "formattedAddress", "shortFormattedAddress", "primaryType", "googleMapsUri", "photos", "currentOpeningHours.openNow", "nationalPhoneNumber", "websiteUri"))
PHOTO_NAME = re.compile(r"^places/[A-Za-z0-9_-]{1,300}/photos/[A-Za-z0-9_-]{1,900}$")


async def search_places(query: str, lat: float | None = None, lng: float | None = None, radius_m: int = 6000, limit: int = 8) -> dict:
    center = {"latitude": lat, "longitude": lng} if lat is not None and lng is not None else HOME
    body = {"textQuery": query, "maxResultCount": limit, "locationBias": {"circle": {"center": center, "radius": float(radius_m)}}}
    async with httpx.AsyncClient(timeout=10) as http:
        r = await http.post("https://places.googleapis.com/v1/places:searchText", json=body,
                            headers={"X-Goog-Api-Key": settings.google_key, "X-Goog-FieldMask": PLACE_FIELDS})
    r.raise_for_status()
    places = [{
        "id": p.get("id"),
        "name": (p.get("displayName") or {}).get("text"),
        "rating": p.get("rating"),
        "ratings": p.get("userRatingCount"),
        "lat": (p.get("location") or {}).get("latitude"),
        "lng": (p.get("location") or {}).get("longitude"),
        "address": p.get("formattedAddress"),
        "type": p.get("primaryType"),
        "maps_url": p.get("googleMapsUri"),
        "short_address": p.get("shortFormattedAddress"),
        "open_now": (p.get("currentOpeningHours") or {}).get("openNow"),
        "phone": p.get("nationalPhoneNumber"),
        "website": p.get("websiteUri"),
        # Photos are served through /api/places/photo (key stays server-side); the author credit must be shown.
        "photo": ((p.get("photos") or [{}])[0]).get("name"),
        "photo_by": [a.get("displayName") for a in ((p.get("photos") or [{}])[0]).get("authorAttributions", []) if a.get("displayName")][:1],
        "provenance": "provider_confirmed",
    } for p in r.json().get("places", [])]
    return {"places": places, "attribution": "Google", "cache": "none", "as_of": datetime.now(timezone.utc).isoformat(timespec="seconds")}


async def route(origin: dict, dest: dict, mode: str = "DRIVE") -> dict:
    body = {"origin": {"location": {"latLng": origin}}, "destination": {"location": {"latLng": dest}}, "travelMode": mode}
    async with httpx.AsyncClient(timeout=10) as http:
        r = await http.post("https://routes.googleapis.com/directions/v2:computeRoutes", json=body,
                            headers={"X-Goog-Api-Key": settings.google_key, "X-Goog-FieldMask": "routes.duration,routes.distanceMeters"})
    r.raise_for_status()
    rt = (r.json().get("routes") or [{}])[0]
    secs = int(str(rt.get("duration", "0s")).rstrip("s") or 0)
    return {"minutes": round(secs / 60), "km": round(rt.get("distanceMeters", 0) / 1000, 1), "provenance": "estimate", "attribution": "Google", "as_of": datetime.now(timezone.utc).isoformat(timespec="seconds")}


async def place_photo(name: str, width: int = 480) -> tuple[bytes, str]:
    """Stream a Places photo through the server so the key never reaches the browser."""
    if not PHOTO_NAME.match(name):
        raise ValueError("bad photo name")
    async with httpx.AsyncClient(timeout=10, follow_redirects=True) as http:
        r = await http.get(f"https://places.googleapis.com/v1/{name}/media", params={"maxWidthPx": max(64, min(width, 1200)), "key": settings.google_key})
    r.raise_for_status()
    return r.content, r.headers.get("content-type", "image/jpeg")


async def static_map(center: tuple[float, float], markers: list[tuple[float, float]], zoom: int | None = None, size: str = "640x400") -> bytes:
    """A Google map image (Places results must sit on a Google map) with numbered pins."""
    params = [("size", size if size in ("640x400", "460x640") else "640x400"), ("scale", "2"), ("maptype", "roadmap"), ("key", settings.google_key),
              ("style", "feature:poi|visibility:simplified"), ("style", "feature:poi.business|visibility:off")]
    if zoom:
        params += [("center", f"{center[0]:.6f},{center[1]:.6f}"), ("zoom", str(zoom))]
    for i, (lat, lng) in enumerate(markers[:9], 1):
        params.append(("markers", f"color:0x0A9CC2|label:{i}|{lat:.6f},{lng:.6f}"))
    if not markers:
        params += [("center", f"{center[0]:.6f},{center[1]:.6f}"), ("zoom", str(zoom or 14))]
    async with httpx.AsyncClient(timeout=10) as http:
        r = await http.get("https://maps.googleapis.com/maps/api/staticmap", params=params)
    r.raise_for_status()
    return r.content
