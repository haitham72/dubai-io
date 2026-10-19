"""Server-side Google Maps Platform calls. The key never leaves the server.
Places results are returned uncached, with the attribution the terms require,
and the live UI must show them on a Google map (Places policy)."""
from datetime import datetime, timezone

import httpx

from .config import settings

HOME = {"latitude": 25.0805, "longitude": 55.1403}  # Dubai Marina, the area the user told us
PLACE_FIELDS = ",".join(f"places.{f}" for f in ("id", "displayName", "rating", "userRatingCount", "location", "formattedAddress", "primaryType", "googleMapsUri"))


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
