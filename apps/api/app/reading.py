"""Pull-only headline discovery. No article bodies, model or scheduler. Thumbnails
are the publisher's own link-preview image, proxied and never stored past the cache.

Only public topic labels go to the existing search provider. Publisher metadata
has a short shared cache; owner preferences are resolved afresh on every read.
"""
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from hashlib import sha256
import html
import ipaddress
import socket
from concurrent.futures import ThreadPoolExecutor
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
        if len([part for part in url.path.split("/") if part]) < 2:
            continue  # a front or section page, not an article
        title = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]*>", "", str(item.get("title") or "")))).strip()
        title = re.sub(r"\s*[|\-–]\s*" + re.escape(sources[host]) + r"\s*$", "", title, flags=re.I)[:200]  # drop " | Publisher"
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


OG_TAG = re.compile(r"<meta\b[^>]*(?:property|name)\s*=\s*[\"'](?:og:image(?::secure_url)?|twitter:image)[\"'][^>]*>", re.I)
OG_CONTENT = re.compile(r"content\s*=\s*[\"']([^\"']+)[\"']", re.I)
IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/avif"}
_thumbs = {}  # article id -> publisher preview URL; bounded, process-local like the headline cache
UA = "DubaiIO-LinkPreview/1.0 (+headline thumbnails)"


def public_https(url):
    """Only https on port 443 to a host that resolves to public addresses (no SSRF to internal hosts)."""
    try:
        parts = urlsplit(url)
        if parts.scheme != "https" or not parts.hostname or parts.username or parts.password or parts.port not in {None, 443}:
            return False
        return all(ipaddress.ip_address(info[4][0]).is_global for info in socket.getaddrinfo(parts.hostname, 443))
    except (ValueError, OSError):
        return False


def preview_image(url):
    """The publisher's declared link-preview image, read from the page head only."""
    site = (urlsplit(url).hostname or "").removeprefix("www.")
    head = b""
    try:
        for _ in range(3):  # at most two redirects, each staying on the same publisher
            host = urlsplit(url).hostname or ""
            if not public_https(url) or not (host == site or host.endswith("." + site)):
                return None
            with httpx.stream("GET", url, timeout=4, follow_redirects=False, headers={"User-Agent": UA}) as page:
                if page.status_code in (301, 302, 303, 307, 308) and page.headers.get("location"):
                    url = str(httpx.URL(url).join(page.headers["location"]))
                    continue
                if page.status_code != 200 or "html" not in page.headers.get("content-type", ""):
                    return None
                for chunk in page.iter_bytes():
                    head += chunk
                    if len(head) > 300_000 or b"</head>" in head.lower():
                        break
                break
        else:
            return None
    except httpx.HTTPError:
        return None
    for tag in OG_TAG.findall(head.decode("utf-8", "ignore")):
        found = OG_CONTENT.search(tag)
        image = html.unescape(found.group(1)).strip() if found else ""
        if image.startswith("https://") and len(image) < 2000:
            return image
    return None


def add_thumbnails(articles):
    with ThreadPoolExecutor(6) as pool:
        images = list(pool.map(lambda a: preview_image(a["url"]), articles))
    with _lock:
        if len(_thumbs) > 400:
            _thumbs.clear()
        for article, image in zip(articles, images):
            if image:
                _thumbs[article["id"]] = image
            article["thumbnail"] = {"url": f"/api/reading/thumbnails/{article['id']}", "credit": article["source"]} if image else None
    return articles


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
            _thumbs.update(cached[3])  # the image map may have been trimmed; cached headlines keep theirs
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
            articles, checked_at = add_thumbnails(fetch_headlines(topics, sources)), utcnow().isoformat()
            with _lock:
                _cache[cache_key] = (now, articles, checked_at, {a["id"]: _thumbs[a["id"]] for a in articles if a["id"] in _thumbs})
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


@router.get("/api/reading/thumbnails/{article_id}")
def thumbnail(article_id: str, request: Request):
    """Serves only images for headlines this server admitted; the browser never contacts publishers."""
    recommendations.owned(request)
    with _lock:
        image = _thumbs.get(article_id)
    if not image or not public_https(image):
        raise HTTPException(404, "No thumbnail")
    try:
        with httpx.stream("GET", image, timeout=5, follow_redirects=False, headers={"User-Agent": UA}) as got:
            kind = got.headers.get("content-type", "").split(";")[0].strip().lower()
            if got.status_code != 200 or kind not in IMAGE_TYPES:
                raise HTTPException(404, "No thumbnail")
            body = b""
            for chunk in got.iter_bytes():
                body += chunk
                if len(body) > 2_000_000:
                    raise HTTPException(404, "No thumbnail")
    except httpx.HTTPError:
        raise HTTPException(404, "No thumbnail")
    return Response(body, media_type=kind, headers={"Cache-Control": "private, max-age=900", "X-Content-Type-Options": "nosniff"})
