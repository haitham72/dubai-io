"""Prayer times via Aladhan (no key): cached, honest unavailable state."""
import httpx
from datetime import date

from fastapi import APIRouter, Query

from .ml_rag import cache_get, cache_set

router = APIRouter(tags=["prayer"])
METHOD = 16  # Dubai, UAE
PRAYERS = ("Fajr", "Sunrise", "Dhuhr", "Asr", "Maghrib", "Isha")


@router.get("/api/prayer-times")
def prayer_times(city: str = Query(default="Dubai", max_length=60),
                 country: str = Query(default="UAE", max_length=60)):
    today = date.today().strftime("%d-%m-%Y")
    key = f"prayer:{city}|{country}|{today}"
    cached = cache_get(key)
    if cached is not None:
        return cached
    try:
        response = httpx.get("https://api.aladhan.com/v1/timingsByCity/" + today,
                             params={"city": city, "country": country, "method": METHOD}, timeout=10)
        response.raise_for_status()
        data = response.json()["data"]
        payload = {"status": "ok", "city": city, "country": country, "date": data["date"]["readable"],
                   "timings": {name: data["timings"][name] for name in PRAYERS},
                   "source": "Aladhan", "method": METHOD, "provenance": "provider_confirmed"}
        cache_set(key, payload, ttl=12 * 3600)
    except Exception:
        payload = {"status": "unavailable", "city": city, "country": country,
                   "reason": "Prayer times could not load right now."}
        cache_set(key, payload, ttl=60)
    return payload
