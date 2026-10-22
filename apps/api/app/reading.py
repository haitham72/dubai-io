"""Pull-only headline discovery. No article bodies, images, model or scheduler.

Only public topic labels go to the existing search provider. Publisher metadata
has a short shared cache; owner preferences are resolved afresh on every read.
"""
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from hashlib import sha256
import html
import json
import os
import re
from threading import Lock
import time
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

from fastapi import APIRouter, HTTPException, Query, Request, Response
import httpx

from . import recommendations

router = APIRouter(tags=["reading"])
TOPICS = {"for_you": "For you", "dubai": "Dubai", "arts": "Arts & culture", "food": "Food",
          "events": "Events", "technology": "Technology", "official": "Official updates"}
QUERIES = {"dubai": "Dubai UAE local news", "arts": "Dubai UAE arts culture exhibitions news",
           "food": "Dubai restaurants food news", "events": "Dubai festivals concerts events news",
           "technology": "Dubai UAE technology news", "official": "Dubai UAE official announcements"}
PUBLISHERS = {"thenationalnews.com": "The National", "gulfnews.com": "Gulf News",
              "khaleejtimes.com": "Khaleej Times", "wam.ae": "Emirates News Agency",
              "mediaoffice.ae": "Dubai Media Office", "dubaiculture.gov.ae": "Dubai Culture"}
OFFICIAL = {k: v for k, v in PUBLISHERS.items() if k in {"wam.ae", "mediaoffice.ae", "dubaiculture.gov.ae"}}
MAPPING = {"food.restaurants": "food", "food.seafood": "food", "food.cafes": "food",
           "events.festivals": "events", "events.live_music": "events", "events.exhibitions": "arts",
           "outings.attractions": "events", "shopping.books": "arts"}
TTL = 900
_cache, _recent = {}, {}
_lock = Lock()


def utcnow():
    return datetime.now(timezone.utc)


def selection(rec, owner, session_id, topic):
    if topic != "for_you":
        return [topic], "Because you selected " + TOPICS[topic], "user_supplied"
    interests = rec.interests(owner, session_id)
    eligible = sorted((i for i in interests if i["topic"] in MAPPING and (
        i["status"] == "confirmed" or i["learning_state"] == "ready" and i["signal"] > 0)),
        key=lambda i: (i["status"] == "confirmed", i["signal"]), reverse=True)
    topics = list(dict.fromkeys(MAPPING[i["topic"]] for i in eligible))[:2]
    if not topics:
        return ["dubai"], "A general Dubai news selection. Choose a topic to change it.", "estimate"
    chosen = [i for i in eligible if MAPPING[i["topic"]] in topics]
    confirmed = all(i["status"] == "confirmed" for i in chosen)
    return topics, ("Because of your confirmed interests" if confirmed else "Because of topics you explored"), "user_supplied" if confirmed else "inferred"


def published(value, at):
    if not isinstance(value, str) or not value:
        return None
    try:
        date = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            date = parsedate_to_datetime(value)
        except (ValueError, TypeError):
            return None
    if date.tzinfo is None or date > at + timedelta(hours=1) or date < at - timedelta(days=8):
        return None
    return date.astimezone(timezone.utc).isoformat()


def headlines(results, sources, at):
    out, seen = [], set()
    for item in results[:20]:
        if not isinstance(item, dict):
            continue
        try:
            url = urlsplit(item.get("url", ""))
            domain = (url.hostname or "").lower()
            host = next((h for h in sources if domain == h or domain.endswith("." + h)), None)
            if url.scheme != "https" or not host or url.username or url.password or url.port not in {None, 443}:
                continue
        except (ValueError, TypeError):
            continue
        title = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]*>", "", str(item.get("title") or "")))).strip()[:200]
        date = published(item.get("published_date"), at)
        if not title or not date:
            continue  # A recency filter is not a publication timestamp.
        params = [(k, v) for k, v in parse_qsl(url.query) if not k.lower().startswith("utm_") and k.lower() not in {"fbclid", "gclid"}]
        link = urlunsplit(("https", domain, url.path or "/", urlencode(params), ""))
        title_key = re.sub(r"\W+", "", title.casefold())
        if link in seen or title_key in seen:
            continue
        seen.update((link, title_key))
        out.append({"id": sha256(link.encode()).hexdigest()[:24], "title": title, "url": link,
                    "source": sources[host], "published_at": date, "date_basis": "search_provider_reported",
                    "checked_at": at.isoformat(), "provenance": "provider_confirmed"})
    return out[:8]


def fetch_headlines(topics, sources):
    key = os.getenv("TVLY_API_KEY", "")
    if not key:
        raise RuntimeError("unconfigured")
    # No names, chat text, task details, location coordinates or owner IDs.
    query = " OR ".join(QUERIES[t] for t in topics)
    result = httpx.post("https://api.tavily.com/search", timeout=8,
        headers={"Authorization": "Bearer " + key}, json={"query": query, "topic": "news",
            "time_range": "week", "search_depth": "basic", "max_results": 12,
            "include_answer": False, "include_raw_content": False, "include_images": False,
            "include_published_date": True, "include_domains": list(sources), "auto_parameters": False})
    result.raise_for_status()
    return headlines(result.json().get("results", []), sources, utcnow())


@router.get("/api/reading")
def reading(request: Request, response: Response, topic: str = "for_you",
            session_id: str | None = Query(default=None, max_length=64)):
    response.headers["Cache-Control"] = "private, no-store"
    if topic not in TOPICS:
        raise HTTPException(422, "Choose an available news topic")
    rec, owner = recommendations.owned(request)
    selected = selection(rec, owner, session_id, topic)
    topics, reason, provenance = selected
    sources = OFFICIAL if topic == "official" else PUBLISHERS
    cache_key = tuple(topics)
    now = time.monotonic()
    with _lock:
        cached = _cache.get(cache_key)
        if cached and now - cached[0] < TTL:
            articles, checked_at = cached[1], cached[2]
        else:
            # Bound accidental repeated scrolling/reloads without background polling.
            _recent[owner] = [at for at in _recent.get(owner, []) if now - at < 60]
            if len(_recent[owner]) >= 4:
                raise HTTPException(429, "News was just refreshed. Try again in a minute.")
            _recent[owner].append(now)
            articles, checked_at = None, None
            for key in [k for k, v in _cache.items() if now - v[0] >= TTL]:
                _cache.pop(key, None)
            if len(_recent) > 500:
                for key in [k for k, times in _recent.items() if not times or now - times[-1] > 60]:
                    _recent.pop(key, None)
    state = "ready"
    if articles is None:
        try:
            articles, checked_at = fetch_headlines(topics, sources), utcnow().isoformat()
            with _lock:
                _cache[cache_key] = (now, articles, checked_at)
        except (httpx.HTTPError, RuntimeError, ValueError, TypeError):
            articles, checked_at, state = [], utcnow().isoformat(), "unavailable"
    # A mid-request Forget/edit must not return a stale personalized feed.
    if selection(rec, owner, session_id, topic) != selected:
        articles, state = [], "preferences_changed"
    return {"articles": articles, "status": state, "topic": topic, "topics": TOPICS,
            "reason": reason if state != "preferences_changed" else "Your preferences changed. Refresh for a new selection.",
            "provenance": provenance, "checked_at": checked_at, "polling": False,
            "attribution": "Headlines via Tavily. Read the full story at its publisher.",
            "date_basis": "Dates reported by the search provider; check the publisher for updates."}
