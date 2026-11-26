"""Live Today feed endpoint (GET /api/today) with Rule 9 gating, two-tower scoring, and per-owner TTL cache."""
from __future__ import annotations

import asyncio
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import os
import re
from threading import RLock
import time
from typing import Any, Awaitable, Callable
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Request
import httpx

from app import google_maps
from app.chat_memory import HELD_BACK_ROOTS, get_bridge_client, is_sensitive_memory_item, require_verified_owner
from app.config import settings
from app.identity.models import VerifiedPrincipal
from app.luna import research as luna_research
from app.memory_bridge.models import ConsentDeniedError, MemoryBridgeError, MemoryBridgeUnavailable
from app.memory_bridge.sensitive import filter_statement, pre_write

router = APIRouter(tags=["today-feed"])

DEFAULT_CACHE_TTL_S = 900
DEFAULT_PROVIDER_TIMEOUT_S = 8.0
MAX_CONFIRMED_QUERIES = 4
MAX_CARDS = 12

_STOPWORDS: frozenset[str] = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "have",
    "in", "is", "it", "my", "noticed", "of", "on", "or", "pattern", "recurring",
    "that", "the", "to", "with", "you", "your", "i", "interest", "interests",
})

_PLACE_HINTS: frozenset[str] = frozenset({
    "cafe", "cafes", "coffee", "restaurant", "restaurants", "dining", "food", "brunch",
    "seafood", "bakery", "park", "parks", "gym", "padel", "tennis", "beach", "museum",
    "gallery", "barber", "salon", "spa", "vet", "mall", "hotel", "cinema", "lounge",
    "roastery", "bistro", "club", "studio", "running", "trail", "cycling",
})

_SHOPPING_HINTS: frozenset[str] = frozenset({
    "shopping", "gear", "hardware", "monitor", "monitors", "oled", "laptop", "phone",
    "keyboard", "mouse", "camera", "lens", "headphones", "earbuds", "shoes", "sneakers",
    "running", "clothing", "apparel", "watch", "book", "books", "espresso", "grinder",
    "machine", "desk", "chair", "console", "controller", "speaker", "gift", "gifts",
    "equipment", "accessories", "bag", "backpack",
})

_YOUTUBE_HINTS: frozenset[str] = frozenset({
    "ai", "ml", "llm", "python", "coding", "programming", "software", "design", "ui",
    "ux", "video", "photography", "music", "podcast", "gaming", "game", "games",
    "tutorial", "course", "learning", "research", "fitness", "workout", "cooking",
    "coffee", "espresso", "tech", "review", "reviews", "architecture", "robotics",
})

_NOTICED_PREFIX_RE = re.compile(
    r"^\s*i\s+noticed(?:\s+recurring\s+interest\s+in|\s+that|\s+a\s+pattern\s+in)?\s*",
    re.IGNORECASE,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _tokenize(text: str) -> set[str]:
    tokens = re.findall(r"[a-z0-9]{3,}", (text or "").lower())
    return {t for t in tokens if t not in _STOPWORDS}


def _clean_noticed_label(text: str) -> str:
    cleaned = _NOTICED_PREFIX_RE.sub("", (text or "").strip()).strip(" .:-")
    return cleaned or (text or "").strip()


def _is_https_url(url: Any) -> bool:
    return isinstance(url, str) and url.strip().startswith("https://")


def _valid_image_url(url: Any) -> str | None:
    if isinstance(url, str):
        val = url.strip()
        if val.startswith("https://") or val.startswith("/api/places/photo?"):
            return val
    return None


@dataclass(frozen=True)
class InterestItem:
    id: str
    label: str
    clean_label: str
    path: str
    kind: str  # "subject" | "topic"
    confirmed: bool
    salience: float
    tokens: frozenset[str] = field(default_factory=frozenset)


@dataclass
class _CacheEntry:
    created_mono: float
    payload: dict[str, Any]


_CACHE_LOCK = RLock()
_OWNER_CACHE: dict[str, _CacheEntry] = {}


def clear_today_cache(owner_id: str | None = None) -> None:
    """Clear per-owner Today cache (or all entries when owner_id is None)."""
    with _CACHE_LOCK:
        if owner_id is None:
            _OWNER_CACHE.clear()
        else:
            _OWNER_CACHE.pop(owner_id, None)


def _cache_ttl_seconds() -> float:
    raw = (os.environ.get("TODAY_CACHE_TTL_S") or str(DEFAULT_CACHE_TTL_S)).strip()
    try:
        return max(1.0, float(raw))
    except ValueError:
        return float(DEFAULT_CACHE_TTL_S)


# ------------------------------------------------------------------ providers
ProviderFn = Callable[[str], list[dict[str, Any]] | Awaitable[list[dict[str, Any]]]]


@dataclass
class ProviderRegistry:
    shopping: ProviderFn
    place: ProviderFn
    web: ProviderFn
    youtube: ProviderFn


def _default_shopping_provider(query: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    try:
        items = luna_research.shopping_search(query, stores=3)
    except httpx.HTTPError:
        items = []
    if not items:
        try:
            items = luna_research.amazon_search(query, limit=3)
        except httpx.HTTPError:
            items = []
    out: list[dict[str, Any]] = []
    for p in items:
        url = p.get("link") or p.get("url")
        if not _is_https_url(url) or not p.get("title"):
            continue
        subtitle_parts = [str(x) for x in (p.get("price"), f"{p['rating']}★" if p.get("rating") else None) if x]
        out.append({
            "title": str(p["title"])[:140],
            "subtitle": " · ".join(subtitle_parts) or str(p.get("source") or "Live listing"),
            "image_url": _valid_image_url(p.get("thumbnail") or p.get("image_url")),
            "source": str(p.get("source") or "Google Shopping"),
            "url": str(url),
            "provenance": "provider_confirmed",
        })
    return out


async def _default_place_provider(query: str) -> list[dict[str, Any]]:
    if not settings.google_key:
        return []
    res = await google_maps.search_places(query, limit=3)
    out: list[dict[str, Any]] = []
    for p in res.get("places") or []:
        url = p.get("maps_url") or p.get("website") or p.get("url")
        if not _is_https_url(url) or not p.get("name"):
            continue
        subtitle_parts = [
            str(x)
            for x in (
                p.get("short_address") or p.get("address"),
                f"{p['rating']}★" if p.get("rating") else None,
            )
            if x
        ]
        photo_ref = p.get("photo")
        img = _valid_image_url(p.get("image_url"))
        if img is None and isinstance(photo_ref, str) and photo_ref:
            img = f"/api/places/photo?name={quote(photo_ref, safe='')}"
        out.append({
            "title": str(p["name"])[:140],
            "subtitle": " · ".join(subtitle_parts) or "Dubai",
            "image_url": img,
            "source": "Google Places",
            "url": str(url),
            "provenance": "provider_confirmed",
        })
    return out


def _default_web_provider(query: str) -> list[dict[str, Any]]:
    hits = luna_research.web_search(query)
    out: list[dict[str, Any]] = []
    for h in hits[:3]:
        url = h.get("url")
        if not _is_https_url(url) or not h.get("title"):
            continue
        out.append({
            "title": str(h["title"])[:140],
            "subtitle": str(h.get("snippet") or "")[:160],
            "image_url": _valid_image_url(h.get("image_url")),
            "source": str(h.get("via") or "Web"),
            "url": str(url),
            "provenance": "provider_confirmed",
        })
    return out


def _default_youtube_provider(query: str) -> list[dict[str, Any]]:
    serp_key = os.getenv("SERPAPI_KEY", "").strip()
    if serp_key:
        r = httpx.get(
            "https://serpapi.com/search.json",
            timeout=8,
            params={"engine": "youtube", "search_query": query[:120], "api_key": serp_key},
        )
        r.raise_for_status()
        out: list[dict[str, Any]] = []
        for v in (r.json().get("video_results") or [])[:3]:
            link = v.get("link") or ""
            title = v.get("title") or ""
            if not _is_https_url(link) or not title:
                continue
            thumb = v.get("thumbnail")
            if isinstance(thumb, dict):
                thumb = thumb.get("static") or thumb.get("rich")
            chan = (v.get("channel") or {}).get("name") if isinstance(v.get("channel"), dict) else None
            out.append({
                "title": str(title)[:140],
                "subtitle": str(chan or v.get("published_date") or "YouTube"),
                "image_url": _valid_image_url(thumb),
                "source": "YouTube",
                "url": str(link),
                "provenance": "provider_confirmed",
            })
        return out

    tvly_key = os.getenv("TVLY_API_KEY", "").strip()
    if tvly_key:
        hits = luna_research.tavily(f"site:youtube.com {query}")
        out = []
        for h in hits[:3]:
            url = h.get("url") or ""
            if not _is_https_url(url) or "youtube.com" not in url or not h.get("title"):
                continue
            out.append({
                "title": str(h["title"])[:140],
                "subtitle": str(h.get("snippet") or "YouTube")[:140],
                "image_url": _valid_image_url(h.get("image_url")),
                "source": "YouTube",
                "url": str(url),
                "provenance": "provider_confirmed",
            })
        return out
    return []


def default_provider_registry() -> ProviderRegistry:
    return ProviderRegistry(
        shopping=_default_shopping_provider,
        place=_default_place_provider,
        web=_default_web_provider,
        youtube=_default_youtube_provider,
    )


_provider_registry_override: ProviderRegistry | None = None


def set_provider_registry(registry: ProviderRegistry | None) -> None:
    """Test hook to override live provider adapters globally."""
    global _provider_registry_override
    _provider_registry_override = registry


def get_provider_registry(request: Request) -> ProviderRegistry:
    """Resolve ProviderRegistry from app.state, override hook, or default live providers."""
    app_reg = getattr(request.app.state, "today_providers", None)
    if isinstance(app_reg, ProviderRegistry):
        return app_reg
    if _provider_registry_override is not None:
        return _provider_registry_override
    return default_provider_registry()


# ------------------------------------------------------------ bridge readers
def _flatten_themes(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flat: list[dict[str, Any]] = []
    for node in items:
        if not isinstance(node, dict):
            continue
        flat.append(node)
        children = node.get("children")
        if isinstance(children, list) and children:
            flat.extend(_flatten_themes(children))
    return flat


def _fetch_owner_subjects(client: Any, owner: str) -> list[dict[str, Any]]:
    list_fn = getattr(client, "list_subjects", None)
    if callable(list_fn):
        raw = list_fn(owner)
        if isinstance(raw, dict):
            return _flatten_themes(list(raw.get("themes") or raw.get("subjects") or []))
        return [dict(x) if isinstance(x, dict) else {"id": x.id, "path": x.path, "label": x.label, "kind": getattr(x, "kind", "topic"), "status": getattr(x, "status", "active"), "salience": getattr(x, "salience", 0.5), "sensitive_cat": getattr(x, "sensitive_cat", None), "provenance": getattr(x, "provenance", "user_supplied")} for x in (raw or [])]
    vault_fn = getattr(client, "get_vault_subjects", None)
    if callable(vault_fn):
        res = vault_fn(owner) or {}
        return _flatten_themes(list(res.get("themes") or []))
    return []


def _fetch_owner_hypotheses(client: Any, owner: str) -> list[dict[str, Any]]:
    list_fn = getattr(client, "list_hypotheses", None)
    if callable(list_fn):
        raw = list_fn(owner)
        if isinstance(raw, dict):
            return list(raw.get("hypotheses") or [])
        return [dict(x) if isinstance(x, dict) else {"id": x.id, "text": x.text, "subject_id": getattr(x, "subject_id", ""), "subject_path": getattr(x, "subject_path", ""), "provenance": getattr(x, "provenance", "inferred")} for x in (raw or [])]
    hyp_fn = getattr(client, "get_hypotheses", None)
    if callable(hyp_fn):
        res = hyp_fn(owner) or {}
        return list(res.get("hypotheses") or [])
    return []


def _fetch_owner_facts(client: Any, owner: str) -> list[dict[str, Any]]:
    search_fn = getattr(client, "search_facts", None)
    if callable(search_fn):
        return list(search_fn(owner, "", limit=100) or [])
    alt_fn = getattr(client, "search", None)
    if callable(alt_fn):
        res = alt_fn(owner, "", limit=100)
        if isinstance(res, dict):
            return list(res.get("facts") or [])
        return list(res or [])
    return []


def _is_sensitive_interest_dict(item: dict[str, Any]) -> bool:
    if is_sensitive_memory_item(item):
        return True
    path = str(item.get("path") or item.get("subject_path") or "").strip("/")
    if path:
        for seg in path.split("/"):
            if seg.strip().lower() in HELD_BACK_ROOTS:
                return True
    for key in ("label", "path", "subject_path", "text"):
        val = item.get(key)
        if isinstance(val, str) and val.strip():
            if filter_statement(val) is not None or pre_write(val) is not None:
                return True
    return False


# ----------------------------------------------------------- interest extraction
def extract_owner_interests(
    client: Any,
    owner: str,
) -> tuple[list[InterestItem], list[InterestItem], str | None]:
    """Read owner memory and return (confirmed_interests, unconfirmed_interests, area_hint)."""
    subjects = [item for item in _fetch_owner_subjects(client, owner) if item.get("weight", 1.0) >= 0.10]
    hypotheses = [item for item in _fetch_owner_hypotheses(client, owner) if item.get("weight", 1.0) >= 0.10]
    facts = _fetch_owner_facts(client, owner)

    confirmed_facts_by_subj: dict[str, list[dict[str, Any]]] = {}
    hypothesis_subj_ids: set[str] = set()
    area_hint: str | None = None

    for f in facts:
        if not isinstance(f, dict) or _is_sensitive_interest_dict(f):
            continue
        sid = str(f.get("subject_id") or "")
        status = str(f.get("status") or "active")
        prov = str(f.get("provenance") or "user_supplied")
        text = str(f.get("text") or "")
        if status == "hypothesis" or prov == "inferred" or text.lower().startswith("i noticed"):
            if sid:
                hypothesis_subj_ids.add(sid)
        elif status == "active":
            if sid:
                confirmed_facts_by_subj.setdefault(sid, []).append(f)
            spath = str(f.get("subject_path") or "").lower()
            if area_hint is None and (spath.endswith("area") or spath.endswith("location")):
                cleaned_area = text.strip()
                if cleaned_area and len(cleaned_area) <= 48:
                    area_hint = cleaned_area

    for h in hypotheses:
        if isinstance(h, dict) and not _is_sensitive_interest_dict(h):
            sid = str(h.get("subject_id") or "")
            if sid:
                hypothesis_subj_ids.add(sid)

    confirmed: list[InterestItem] = []
    unconfirmed: list[InterestItem] = []
    seen_confirmed_labels: set[str] = set()
    seen_unconfirmed_labels: set[str] = set()

    for s in subjects:
        if not isinstance(s, dict) or _is_sensitive_interest_dict(s):
            continue
        sid = str(s.get("id") or s.get("subject_id") or "")
        path = str(s.get("path") or s.get("subject_path") or "general").strip("/")
        raw_label = str(s.get("label") or path.split("/")[-1].replace("-", " ").title()).strip()
        if not raw_label:
            continue
        clean_lbl = _clean_noticed_label(raw_label)
        salience = float(s.get("salience") if s.get("salience") is not None else 0.7)
        salience = max(0.05, min(1.0, salience))
        status = str(s.get("status") or "active").lower()
        prov = str(s.get("provenance") or "user_supplied").lower()
        review_state = str(s.get("review_state") or "").lower()

        if isinstance(s.get("confirmed"), bool):
            is_confirmed = bool(s["confirmed"])
        elif status == "candidate" or review_state == "pending_review" or prov == "inferred":
            is_confirmed = bool(sid and confirmed_facts_by_subj.get(sid))
        elif sid and sid in hypothesis_subj_ids and not confirmed_facts_by_subj.get(sid):
            is_confirmed = False
        else:
            is_confirmed = status == "active"

        fact_texts = " ".join(str(f.get("text") or "") for f in confirmed_facts_by_subj.get(sid, []))
        tokens = frozenset(_tokenize(f"{clean_lbl} {path.replace('/', ' ')} {fact_texts}"))
        if is_confirmed:
            key = clean_lbl.lower()
            if key in seen_confirmed_labels:
                continue
            seen_confirmed_labels.add(key)
            confirmed.append(
                InterestItem(
                    id=sid or f"subj_{len(confirmed) + 1}",
                    label=raw_label,
                    clean_label=clean_lbl,
                    path=path,
                    kind="subject" if s.get("kind") != "topic" else "topic",
                    confirmed=True,
                    salience=salience,
                    tokens=tokens,
                )
            )
        else:
            key = clean_lbl.lower()
            if key in seen_unconfirmed_labels:
                continue
            seen_unconfirmed_labels.add(key)
            unconfirmed.append(
                InterestItem(
                    id=sid or f"hyp_subj_{len(unconfirmed) + 1}",
                    label=raw_label,
                    clean_label=clean_lbl,
                    path=path,
                    kind="topic",
                    confirmed=False,
                    salience=min(salience, 0.75),
                    tokens=tokens,
                )
            )

    # Fallback: confirmed active facts whose subject was not returned by vault/subjects.
    covered_sids = {i.id for i in confirmed}
    for sid, flist in confirmed_facts_by_subj.items():
        if sid in covered_sids:
            continue
        f0 = flist[0]
        spath = str(f0.get("subject_path") or "general").strip("/")
        lbl = spath.split("/")[-1].replace("-", " ").replace("_", " ").strip().title()
        if not lbl or lbl.lower() in seen_confirmed_labels:
            continue
        seen_confirmed_labels.add(lbl.lower())
        confirmed.append(
            InterestItem(
                id=sid or f"topic_{len(confirmed) + 1}",
                label=lbl,
                clean_label=lbl,
                path=spath,
                kind="topic",
                confirmed=True,
                salience=0.8,
                tokens=frozenset(_tokenize(f"{lbl} {spath.replace('/', ' ')}")),
            )
        )

    for h in hypotheses:
        if not isinstance(h, dict) or _is_sensitive_interest_dict(h):
            continue
        hid = str(h.get("id") or "")
        raw_text = str(h.get("text") or h.get("label") or "").strip()
        if not raw_text:
            continue
        clean_lbl = _clean_noticed_label(raw_text)
        key = clean_lbl.lower()
        if key in seen_unconfirmed_labels:
            continue
        seen_unconfirmed_labels.add(key)
        spath = str(h.get("subject_path") or "").strip("/")
        salience = float(h.get("salience") if h.get("salience") is not None else 0.55)
        unconfirmed.append(
            InterestItem(
                id=hid or f"hyp_{len(unconfirmed) + 1}",
                label=raw_text,
                clean_label=clean_lbl,
                path=spath,
                kind="topic",
                confirmed=False,
                salience=max(0.05, min(0.85, salience)),
                tokens=frozenset(_tokenize(f"{clean_lbl} {spath.replace('/', ' ')}")),
            )
        )

    confirmed.sort(key=lambda item: (-item.salience, item.clean_label.lower()))
    unconfirmed.sort(key=lambda item: (-item.salience, item.clean_label.lower()))
    return confirmed, unconfirmed, area_hint


# ----------------------------------------------------------- two-tower engine
def _select_categories(interest: InterestItem) -> list[str]:
    tokens = set(interest.tokens) | _tokenize(interest.path.replace("/", " "))
    cats: list[str] = []
    if tokens & _SHOPPING_HINTS or "shopping" in interest.path.lower():
        cats.append("shopping")
    if tokens & _PLACE_HINTS or any(k in interest.path.lower() for k in ("food", "place", "dining", "outings")):
        cats.append("place")
    if tokens & _YOUTUBE_HINTS or any(k in interest.path.lower() for k in ("learn", "tech", "gaming", "media")):
        cats.append("youtube")
    if not cats:
        cats = ["web", "shopping"]
    elif "web" not in cats and len(cats) < 2:
        cats.append("web")
    return cats[:2]


def _build_provider_query(interest: InterestItem, category: str, area_hint: str | None) -> str:
    base = interest.clean_label.strip()
    if category == "place":
        loc = area_hint or ("Dubai" if "dubai" not in base.lower() else "")
        return f"{base} {loc}".strip()[:120]
    if category == "shopping" and "uae" not in base.lower() and "dubai" not in base.lower():
        return f"{base} UAE".strip()[:120]
    return base[:120]


async def _call_provider(fn: ProviderFn, query: str, timeout_s: float) -> tuple[list[dict[str, Any]], bool]:
    async def _invoke() -> list[dict[str, Any]]:
        if asyncio.iscoroutinefunction(fn):
            return list(await fn(query) or [])
        res = await asyncio.to_thread(fn, query)
        if asyncio.iscoroutine(res):
            return list(await res or [])
        return list(res or [])

    try:
        items = await asyncio.wait_for(_invoke(), timeout=timeout_s)
        return items, False
    except Exception:
        return [], True


def _token_overlap_score(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    exact = len(a & b)
    if exact > 0:
        return float(exact)
    # Stem prefix match (>= 5 chars) for morphological variants (e.g. espresso/espressos, gamer/gaming).
    stem_hits = 0
    for ta in a:
        if len(ta) < 5:
            continue
        for tb in b:
            if len(tb) >= 5 and (ta.startswith(tb[:5]) or tb.startswith(ta[:5])):
                stem_hits += 1
                break
    return 0.7 * stem_hits


def _score_and_rerank(
    candidates: list[dict[str, Any]],
    unconfirmed: list[InterestItem],
) -> list[dict[str, Any]]:
    scored: list[tuple[float, float, dict[str, Any]]] = []
    for cand in candidates:
        interest: InterestItem = cand["_interest"]
        card_tokens = _tokenize(f"{cand['title']} {cand['subtitle']} {interest.clean_label} {cand['category']}")
        base_score = (
            interest.salience
            + 0.15 * _token_overlap_score(card_tokens, set(interest.tokens))
            + (0.05 if cand.get("image_url") else 0.0)
        )

        best_hyp: InterestItem | None = None
        best_overlap = 0.0
        for hyp in unconfirmed:
            ov = _token_overlap_score(card_tokens, set(hyp.tokens))
            if ov > best_overlap:
                best_overlap = ov
                best_hyp = hyp

        boost = 0.0
        if best_hyp is not None and best_overlap >= 0.7:
            boost = 0.25 * max(0.1, best_hyp.salience) * min(2.0, best_overlap)
            because = f"Because: Confirmed interest {interest.clean_label} · Boosted by unconfirmed pattern {best_hyp.clean_label}"
        else:
            because = f"Because: Confirmed interest {interest.clean_label}"

        item = {k: v for k, v in cand.items() if not k.startswith("_")}
        item["because"] = because
        scored.append((base_score + boost, base_score, item))

    scored.sort(key=lambda row: (-row[0], -row[1], row[2]["title"].lower()))

    deduped: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    for _, _, item in scored:
        dedupe_key = str(item.get("url") or f"{item['title'].lower()}|{item['source'].lower()}")
        if dedupe_key in seen_keys:
            continue
        seen_keys.add(dedupe_key)
        deduped.append(item)
        if len(deduped) >= MAX_CARDS:
            break
    return deduped


@router.get("/api/today")
async def get_today_feed(
    refresh: int = Query(default=0, ge=0, le=1),
    principal: VerifiedPrincipal = Depends(require_verified_owner),
    client: Any = Depends(get_bridge_client),
    providers: ProviderRegistry = Depends(get_provider_registry),
) -> dict[str, Any]:
    """Return personalized live Today cards strictly scoped to the verified owner."""
    owner = principal.user_id
    ttl = _cache_ttl_seconds()
    now_mono = time.monotonic()

    # The remote owner version changes on Lower, Restore and account deletion, including
    # changes made outside this API process. Never return an unvalidated remote cache entry.
    local_cache = not callable(getattr(client, "memory_version", None))
    if refresh == 0 and local_cache:
        with _CACHE_LOCK:
            entry = _OWNER_CACHE.get(owner)
            if entry is not None and (now_mono - entry.created_mono) < ttl:
                cached_payload = deepcopy(entry.payload)
                cached_payload["cached"] = True
                return cached_payload

    try:
        confirmed, unconfirmed, area_hint = extract_owner_interests(client, owner)
    except MemoryBridgeUnavailable as exc:
        raise HTTPException(status_code=503, detail={"code": exc.code, "message": str(exc)}) from exc
    except ConsentDeniedError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": str(exc)}) from exc
    except MemoryBridgeError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": str(exc)}) from exc

    as_of = _now_iso()
    interests_dto = [
        {
            "id": item.id,
            "label": item.clean_label if item.confirmed else item.label,
            "kind": item.kind,
            "confirmed": item.confirmed,
            "salience": round(item.salience, 4),
        }
        for item in (*confirmed, *unconfirmed)
    ]

    if not confirmed:
        payload = {
            "owner_id": owner,
            "as_of": as_of,
            "cached": False,
            "interests": interests_dto,
            "cards": [],
            "empty_reason": "no_confirmed_interests",
            "provenance": "provider_confirmed",
            "demo": False,
        }
        if local_cache:
            with _CACHE_LOCK:
                _OWNER_CACHE[owner] = _CacheEntry(created_mono=now_mono, payload=deepcopy(payload))
        return payload

    # Rule 9: Only confirmed interests ever trigger external provider searches.
    timeout_s = float(os.environ.get("TODAY_PROVIDER_TIMEOUT_S", str(DEFAULT_PROVIDER_TIMEOUT_S)))
    jobs: list[tuple[InterestItem, str, str, ProviderFn]] = []
    provider_map: dict[str, ProviderFn] = {
        "shopping": providers.shopping,
        "place": providers.place,
        "web": providers.web,
        "youtube": providers.youtube,
    }
    for interest in confirmed[:MAX_CONFIRMED_QUERIES]:
        for category in _select_categories(interest):
            fn = provider_map[category]
            query = _build_provider_query(interest, category, area_hint)
            jobs.append((interest, category, query, fn))

    results = await asyncio.gather(*(_call_provider(fn, query, timeout_s) for _, _, query, fn in jobs))

    raw_candidates: list[dict[str, Any]] = []
    error_count = 0
    for (interest, category, _, _), (items, failed) in zip(jobs, results):
        if failed:
            error_count += 1
            continue
        for raw in items:
            if not isinstance(raw, dict):
                continue
            title = str(raw.get("title") or "").strip()
            url = raw.get("url") or raw.get("link")
            if not title or not _is_https_url(url):
                continue
            card_id = str(
                raw.get("id")
                or hashlib.sha256(f"{category}|{url}|{title}".encode("utf-8")).hexdigest()[:16]
            )
            raw_candidates.append({
                "id": card_id,
                "interest": interest.clean_label,
                "category": category,
                "title": title[:140],
                "subtitle": str(raw.get("subtitle") or "")[:200],
                "image_url": _valid_image_url(raw.get("image_url") or raw.get("thumbnail")),
                "source": str(raw.get("source") or category),
                "url": str(url),
                "provenance": "provider_confirmed",
                "as_of": str(raw.get("as_of") or as_of),
                "_interest": interest,
            })

    cards = _score_and_rerank(raw_candidates, unconfirmed)
    empty_reason: str | None = None
    if not cards:
        empty_reason = "providers_unavailable" if error_count == len(jobs) else "no_live_results"

    payload = {
        "owner_id": owner,
        "as_of": as_of,
        "cached": False,
        "interests": interests_dto,
        "cards": cards,
        "empty_reason": empty_reason,
        "provenance": "provider_confirmed",
        "demo": False,
    }
    if local_cache:
        with _CACHE_LOCK:
            _OWNER_CACHE[owner] = _CacheEntry(created_mono=now_mono, payload=deepcopy(payload))
    return payload
