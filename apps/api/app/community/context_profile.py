"""Context-Aware Usage Profile & Ephemeral Context Envelope (E14c / D19 / D19b / Rule 8 & 9).

Hard privacy & safety guarantees:
- Rule 8: Zero GPS persistence, zero background geofencing. Raw lat/lng are
  immediately snapped server-side to a coarse Dubai district (`area_coarse`)
  and dropped before storage or logging.
- Rule 9: `user_state` is strictly ephemeral session context (Redis / in-process
  TTL cache with 600s TTL) and is NEVER written to `temporal_memory` or
  health/fitness storage. Sensitive topics are blocked via `pre_write`.
- D19: Never delete normal history. Explicit Lower sets `lowered_at` -> weight
  0.01 (`< 0.10` surface threshold). Unrefreshed entries decay after 30 days
  down to `0.05`.
- D19b: Lowered/aged entries remain 100% explicitly callable via recall, which
  clears `lowered_at`, refreshes `last_seen_at`, and boosts weight to >= 0.35.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from functools import lru_cache
import json
import math
import os
import re
from threading import RLock
import time
from typing import Any, Mapping
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from . import store as cm
from .routes import scope

router = APIRouter(tags=["community-context"])

# ---------------------------------------------------------------- constants
WEIGHT_MIN: float = 0.01
AGE_DECAY_FLOOR: float = 0.05
SURFACE_THRESHOLD: float = 0.10
RECALL_BOOST_DELTA: float = 0.25
RECALL_MIN_WEIGHT: float = 0.35
CONTEXT_TTL_SECONDS: int = 600

DUBAI_TZ = timezone(timedelta(hours=4))

DUBAI_AREAS: dict[str, tuple[float, float]] = {
    "Dubai Marina": (25.0805, 55.1403),
    "JLT": (25.0721, 55.1463),
    "DIFC": (25.2120, 55.2806),
    "Downtown Dubai": (25.1972, 55.2744),
    "Business Bay": (25.1851, 55.2665),
    "Jumeirah": (25.2084, 55.2470),
    "Al Quoz": (25.1372, 55.2289),
    "Deira": (25.2713, 55.3175),
    "Bur Dubai": (25.2528, 55.2974),
    "Palm Jumeirah": (25.1124, 55.1390),
    "Internet City": (25.0956, 55.1561),
}

_AREA_ALIASES: dict[str, str] = {
    "dubai marina": "Dubai Marina",
    "marina": "Dubai Marina",
    "jlt": "JLT",
    "jumeirah lakes towers": "JLT",
    "difc": "DIFC",
    "downtown": "Downtown Dubai",
    "downtown dubai": "Downtown Dubai",
    "business bay": "Business Bay",
    "jumeirah": "Jumeirah",
    "al quoz": "Al Quoz",
    "alquoz": "Al Quoz",
    "deira": "Deira",
    "bur dubai": "Bur Dubai",
    "palm jumeirah": "Palm Jumeirah",
    "palm": "Palm Jumeirah",
    "internet city": "Internet City",
    "dubai internet city": "Internet City",
    "dic": "Internet City",
}

USER_STATES: tuple[str, ...] = (
    "stationary",
    "sitting",
    "standing",
    "walking",
    "running",
    "driving",
    "unknown",
)
_USER_STATE_SET = frozenset(USER_STATES)

DEVICE_CLASSES: tuple[str, ...] = (
    "mobile_ios",
    "mobile_android",
    "mobile_web",
    "desktop",
    "web",
    "unknown",
)
_DEVICE_CLASS_SET = frozenset(DEVICE_CLASSES)

EVENT_TYPES: tuple[str, ...] = (
    "upvote",
    "downvote",
    "reply",
    "bookmark",
    "repost",
    "dwell",
    "hide",
    "lower",
)
_POSITIVE_EVENT_WEIGHTS: dict[str, float] = {
    "upvote": 1.0,
    "bookmark": 1.5,
    "reply": 1.3,
    "repost": 1.2,
    "dwell": 0.6,
}
_NEGATIVE_EVENT_WEIGHTS: dict[str, float] = {
    "downvote": 0.8,
    "hide": 1.2,
}

# Calibration constant for invertible bounded log score -> [0, 1] weight.
_SCORE_LOG_DENOM = math.log1p(6.0)

# ---------------------------------------------------------------- DDL
DDL = (
    """CREATE TABLE IF NOT EXISTS cm_interaction_events (
        id TEXT PRIMARY KEY,
        owner TEXT NOT NULL,
        post_id TEXT NOT NULL DEFAULT '',
        topic_key TEXT NOT NULL DEFAULT '',
        event_type TEXT NOT NULL,
        value REAL NOT NULL DEFAULT 1.0,
        area_coarse TEXT NOT NULL DEFAULT 'unknown',
        device_class TEXT NOT NULL DEFAULT 'unknown',
        time_bucket TEXT NOT NULL DEFAULT 'workday',
        user_state TEXT NOT NULL DEFAULT 'unknown',
        session_id TEXT NOT NULL DEFAULT '',
        dedupe_key TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL
    )""",
    "CREATE UNIQUE INDEX IF NOT EXISTS cm_interaction_events_dedupe ON cm_interaction_events(owner, dedupe_key) WHERE dedupe_key <> ''",
    "CREATE INDEX IF NOT EXISTS cm_interaction_events_owner_time ON cm_interaction_events(owner, created_at)",
    """CREATE TABLE IF NOT EXISTS cm_usage_profile (
        owner TEXT NOT NULL,
        topic_key TEXT NOT NULL,
        time_bucket TEXT NOT NULL,
        area_coarse TEXT NOT NULL,
        format_bucket TEXT NOT NULL,
        positive_score REAL NOT NULL DEFAULT 0.0,
        negative_score REAL NOT NULL DEFAULT 0.0,
        evidence_count INTEGER NOT NULL DEFAULT 0,
        distinct_sessions INTEGER NOT NULL DEFAULT 0,
        first_seen_at TEXT NOT NULL,
        last_seen_at TEXT NOT NULL,
        lowered_at TEXT,
        suppressed INTEGER NOT NULL DEFAULT 0,
        updated_at TEXT NOT NULL,
        PRIMARY KEY (owner, topic_key, time_bucket, area_coarse, format_bucket)
    )""",
    """CREATE TABLE IF NOT EXISTS cm_usage_settings (
        owner TEXT PRIMARY KEY,
        context_aware_enabled INTEGER NOT NULL DEFAULT 0,
        updated_at TEXT NOT NULL
    )""",
)


def setup_context_profile(store) -> None:
    if getattr(store, "_context_profile_ready", False):
        return
    cm.setup(store)
    for stmt in DDL:
        store.db.execute(stmt)
    if getattr(store.db, "dialect", "sqlite") == "postgres":
        for tbl in ("cm_interaction_events", "cm_usage_profile", "cm_usage_settings"):
            try:
                store.db.execute(f"ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY")
            except Exception:
                pass
    store.db.commit()
    store._context_profile_ready = True


# ---------------------------------------------------------------- geo / time / safety helpers
def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2.0) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2.0) ** 2
    return 2.0 * r * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))


def snap_coordinates_to_area(lat: float, lng: float) -> str:
    """Snap raw coordinates immediately to the nearest coarse Dubai district.

    Raw lat/lng are never persisted, logged, or returned.
    """
    lat_f = float(lat)
    lng_f = float(lng)
    best_area = "Downtown Dubai"
    best_dist = float("inf")
    for name, (c_lat, c_lng) in DUBAI_AREAS.items():
        d = _haversine_km(lat_f, lng_f, c_lat, c_lng)
        if d < best_dist:
            best_dist = d
            best_area = name
    return best_area


def normalize_area_coarse(area: str | None) -> str:
    raw = (area or "").strip()
    if not raw:
        return "unknown"
    low = raw.lower()
    if low in _AREA_ALIASES:
        return _AREA_ALIASES[low]
    for canonical in DUBAI_AREAS:
        if canonical.lower() == low:
            return canonical
    return raw[:60]


def compute_time_bucket(dt_utc: datetime | None = None) -> tuple[str, bool]:
    """Return `(time_bucket, is_weekend)` in Asia/Dubai (UTC+4). Weekend is Sat/Sun."""
    if dt_utc is None:
        now_dt = datetime.now(timezone.utc)
    elif dt_utc.tzinfo is None:
        now_dt = dt_utc.replace(tzinfo=timezone.utc)
    else:
        now_dt = dt_utc
    dubai_dt = now_dt.astimezone(DUBAI_TZ)
    hour = dubai_dt.hour
    is_weekend = dubai_dt.weekday() in (5, 6)
    if 5 <= hour < 8:
        bucket = "early_morning"
    elif 8 <= hour < 10:
        bucket = "commute_am"
    elif 10 <= hour < 12:
        bucket = "workday"
    elif 12 <= hour < 14:
        bucket = "lunch"
    elif 14 <= hour < 17:
        bucket = "workday"
    elif 17 <= hour < 20:
        bucket = "commute_pm"
    elif 20 <= hour < 23:
        bucket = "evening"
    else:
        bucket = "late_night"
    return bucket, is_weekend


@lru_cache(maxsize=8192)
def _is_sensitive_topic_cached(clean: str) -> bool:
    """Rule-9 deterministic sensitivity check using memory_bridge/lab sensitive + E10 vocab."""
    checked = False
    try:
        from app.memory_bridge.sensitive import pre_write

        checked = True
        if pre_write(clean) is not None:
            return True
    except Exception:
        pass
    try:
        from app.lab import sensitive as lab_sensitive

        checked = True
        fn = getattr(lab_sensitive, "pre_write", None) or getattr(lab_sensitive, "filter_statement", None)
        if fn is not None and fn(clean) is not None:
            return True
    except Exception:
        pass
    try:
        from temporal_memory.vocab import get_vocab

        vocab = get_vocab()
        low = clean.lower().strip("# ")
        node = vocab.by_path.get(low)
        if node is not None and node.sensitive:
            return True
        for path in vocab.curated_token_to_paths.get(low, ()):
            vnode = vocab.by_path.get(path)
            if vnode is not None and vnode.sensitive:
                return True
        checked = True
    except Exception:
        pass
    # Fail closed only when no checker could run.
    return not checked


def is_sensitive_topic(text: str) -> bool:
    clean = (text or "").strip()
    if not clean:
        return False
    return _is_sensitive_topic_cached(clean.lower())


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _now_dt() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now_dt().isoformat(timespec="seconds")


# ---------------------------------------------------------------- ephemeral context store (Redis + TTL fallback)
_TTL_LOCK = RLock()
_EPHEMERAL_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}


def _redis_url_configured() -> str | None:
    for key in ("REDIS_URL", "TM_REDIS_URL"):
        val = (os.environ.get(key) or "").strip()
        if val:
            return val
    return None


def _get_redis_client():
    url = _redis_url_configured()
    if not url:
        return None
    try:
        import redis

        client = redis.Redis.from_url(
            url,
            decode_responses=True,
            socket_connect_timeout=0.25,
            socket_timeout=0.25,
        )
        client.ping()
        return client
    except Exception:
        return None


def _ctx_key(owner: str) -> str:
    return f"cm:ctx:{owner}"


def _sanitize_context_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Build sanitized ephemeral context envelope (never retains lat/lng)."""
    area_coarse = normalize_area_coarse(str(payload.get("area_coarse") or "unknown"))
    user_state = str(payload.get("user_state") or "unknown").strip().lower()
    if user_state not in _USER_STATE_SET:
        user_state = "unknown"
    device_class = str(payload.get("device_class") or "unknown").strip().lower()
    if device_class not in _DEVICE_CLASS_SET:
        device_class = "unknown"
    time_bucket = str(payload.get("time_bucket") or "").strip()
    is_weekend = payload.get("is_weekend")
    if not time_bucket or is_weekend is None:
        tb, wk = compute_time_bucket()
        time_bucket = time_bucket or tb
        if is_weekend is None:
            is_weekend = wk
    confidence = float(payload.get("confidence") or 0.0)
    confidence = max(0.0, min(1.0, confidence))
    source = str(payload.get("source") or "unavailable").strip()[:40]
    return {
        "area_coarse": area_coarse,
        "device_class": device_class,
        "time_bucket": time_bucket,
        "is_weekend": bool(is_weekend),
        "user_state": user_state,
        "confidence": round(confidence, 4),
        "source": source,
        "ttl_seconds": CONTEXT_TTL_SECONDS,
        "updated_at": str(payload.get("updated_at") or _now_iso()),
    }


def set_ephemeral_context(owner: str, payload: Mapping[str, Any], *, ttl_seconds: int = CONTEXT_TTL_SECONDS) -> tuple[dict[str, Any], str]:
    """Store ephemeral context in Redis when reachable, else in-process TTL cache."""
    clean = _sanitize_context_payload(payload)
    key = _ctx_key(owner)
    client = _get_redis_client()
    if client is not None:
        try:
            client.setex(key, int(ttl_seconds), json.dumps(clean))
            return clean, "redis"
        except Exception:
            pass
    expires_at = time.monotonic() + float(ttl_seconds)
    with _TTL_LOCK:
        _EPHEMERAL_CACHE[key] = (expires_at, clean)
    return clean, "memory_ttl"


def get_ephemeral_context(owner: str) -> dict[str, Any] | None:
    """Retrieve active ephemeral context (respecting TTL), or None."""
    key = _ctx_key(owner)
    client = _get_redis_client()
    if client is not None:
        try:
            raw = client.get(key)
            if raw:
                return _sanitize_context_payload(json.loads(raw))
        except Exception:
            pass
    with _TTL_LOCK:
        entry = _EPHEMERAL_CACHE.get(key)
        if not entry:
            return None
        expires_at, data = entry
        if time.monotonic() >= expires_at:
            _EPHEMERAL_CACHE.pop(key, None)
            return None
        return dict(data)


def clear_ephemeral_context(owner: str) -> None:
    key = _ctx_key(owner)
    client = _get_redis_client()
    if client is not None:
        try:
            client.delete(key)
        except Exception:
            pass
    with _TTL_LOCK:
        _EPHEMERAL_CACHE.pop(key, None)


def purge_owner_community_data(owner_id: str, store=None) -> dict[str, Any]:
    """Account-level Delete my data (D19): clear Community SQL + Redis/TTL context.

    Deletes `cm_interaction_events`, `cm_usage_profile`, `cm_usage_settings`, the
    Redis key `cm:ctx:{owner}`, and the in-process TTL fallback cache.
    """
    if store is None:
        from app.actions import engine

        store = engine().store
    clear_ephemeral_context(owner_id)
    setup_context_profile(store)
    store.db.execute("DELETE FROM cm_usage_profile WHERE owner=?", (owner_id,))
    store.db.execute("DELETE FROM cm_interaction_events WHERE owner=?", (owner_id,))
    store.db.execute("DELETE FROM cm_usage_settings WHERE owner=?", (owner_id,))
    store.db.commit()
    return {"purged": True, "owner": owner_id}


def purge_owner_context(store, owner: str) -> None:
    """Backward-compatible alias for `purge_owner_community_data`."""
    purge_owner_community_data(owner, store=store)


# ---------------------------------------------------------------- settings & qualification
def is_context_aware_enabled(store, owner: str) -> bool:
    """D22: context-aware usage is strictly opt-in (default off when unset)."""
    setup_context_profile(store)
    row = store.db.execute(
        "SELECT context_aware_enabled FROM cm_usage_settings WHERE owner=?",
        (owner,),
    ).fetchone()
    if row is None:
        return False
    return bool(row[0])


def set_context_aware_enabled(store, owner: str, enabled: bool) -> dict[str, Any]:
    setup_context_profile(store)
    stamp = _now_iso()
    val = 1 if enabled else 0
    existing = store.db.execute("SELECT owner FROM cm_usage_settings WHERE owner=?", (owner,)).fetchone()
    if existing:
        store.db.execute(
            "UPDATE cm_usage_settings SET context_aware_enabled=?, updated_at=? WHERE owner=?",
            (val, stamp, owner),
        )
    else:
        store.db.execute(
            "INSERT INTO cm_usage_settings (owner, context_aware_enabled, updated_at) VALUES (?,?,?)",
            (owner, val, stamp),
        )
    store.db.commit()
    if not enabled:
        clear_ephemeral_context(owner)
    return {"context_aware_enabled": bool(enabled), "updated_at": stamp}


_USAGE_COLS = (
    "owner",
    "topic_key",
    "time_bucket",
    "area_coarse",
    "format_bucket",
    "positive_score",
    "negative_score",
    "evidence_count",
    "distinct_sessions",
    "first_seen_at",
    "last_seen_at",
    "lowered_at",
    "suppressed",
    "updated_at",
)


def _row_to_dict(row: Mapping[str, Any] | tuple[Any, ...]) -> dict[str, Any]:
    if isinstance(row, Mapping):
        return dict(row)
    return dict(zip(_USAGE_COLS, row))


def is_usage_qualified(row: Mapping[str, Any] | tuple[Any, ...]) -> bool:
    """Two-visit qualification: distinct_sessions >= 2 OR >= 6h separation across >= 2 events."""
    d = _row_to_dict(row)
    sessions = int(d.get("distinct_sessions") or 0)
    evidence = int(d.get("evidence_count") or 0)
    if sessions >= 2 and evidence >= 2:
        return True
    if evidence >= 2:
        first_dt = _parse_iso(d.get("first_seen_at"))
        last_dt = _parse_iso(d.get("last_seen_at"))
        if first_dt and last_dt and (last_dt - first_dt) >= timedelta(hours=6):
            return True
    return False


def _score_to_base_weight(net_score: float) -> float:
    if net_score <= 0.0:
        return 0.0
    return min(1.0, math.log1p(net_score) / _SCORE_LOG_DENOM)


def _weight_to_net_score(weight: float) -> float:
    w = max(0.0, min(1.0, float(weight)))
    return math.expm1(w * _SCORE_LOG_DENOM)


def compute_usage_weight(row: Mapping[str, Any] | tuple[Any, ...], now: datetime | None = None) -> float:
    """Compute D19 + D19b effective weight for a `cm_usage_profile` row.

    - Explicit Lower (`lowered_at` set or `suppressed`) -> `WEIGHT_MIN` (`0.01`).
    - Positive affinity decays after 30 days with 30-day half-life down to `AGE_DECAY_FLOOR` (`0.05`).
    - Entries `< SURFACE_THRESHOLD` (`0.10`) are excluded from passive recommendations.
    """
    d = _row_to_dict(row)
    if d.get("lowered_at") or int(d.get("suppressed") or 0):
        return WEIGHT_MIN
    pos = float(d.get("positive_score") or 0.0)
    neg = float(d.get("negative_score") or 0.0)
    net = max(0.0, pos - neg)
    if net <= 0.0:
        return WEIGHT_MIN if neg > 0.0 else 0.0
    base = _score_to_base_weight(net)
    now_dt = now or _now_dt()
    if now_dt.tzinfo is None:
        now_dt = now_dt.replace(tzinfo=timezone.utc)
    last_dt = _parse_iso(d.get("last_seen_at")) or now_dt
    age_days = max(0.0, (now_dt - last_dt).total_seconds() / 86400.0)
    if age_days > 30.0:
        decay = 0.5 ** ((age_days - 30.0) / 30.0)
        eff = max(AGE_DECAY_FLOOR, base * decay)
    else:
        eff = max(AGE_DECAY_FLOOR, base)
    return round(min(1.0, eff), 6)


def _present_usage_entry(row: Mapping[str, Any] | tuple[Any, ...], *, context_enabled: bool = True, now: datetime | None = None) -> dict[str, Any]:
    d = _row_to_dict(row)
    weight = compute_usage_weight(d, now=now)
    qualified = is_usage_qualified(d)
    lowered = bool(d.get("lowered_at")) or bool(int(d.get("suppressed") or 0))
    # Topic affinity can personalise the feed without sensor opt-in.
    # D22 context_enabled gates ephemeral area/user_state only (see heartbeat/ranker).
    _ = context_enabled
    active_in_feed = bool(not lowered and qualified and weight >= SURFACE_THRESHOLD)
    return {
        "owner": d["owner"],
        "topic_key": d["topic_key"],
        "time_bucket": d["time_bucket"],
        "area_coarse": d["area_coarse"],
        "format_bucket": d["format_bucket"],
        "positive_score": round(float(d["positive_score"]), 4),
        "negative_score": round(float(d["negative_score"]), 4),
        "evidence_count": int(d["evidence_count"]),
        "distinct_sessions": int(d["distinct_sessions"]),
        "first_seen_at": d["first_seen_at"],
        "last_seen_at": d["last_seen_at"],
        "lowered_at": d.get("lowered_at"),
        "lowered": lowered,
        "suppressed": bool(int(d.get("suppressed") or 0)),
        "updated_at": d["updated_at"],
        "weight": weight,
        "qualified": qualified,
        "active_in_feed": active_in_feed,
    }


# ---------------------------------------------------------------- event logging & usage projection
def _normalize_topic_key(topic_key: str) -> str:
    return re.sub(r"\s+", " ", (topic_key or "").strip().lower().lstrip("#"))[:120]


def _infer_format_bucket(store, post_id: str, explicit: str | None) -> str:
    if explicit and explicit.strip().lower() in ("short", "medium", "long"):
        return explicit.strip().lower()
    if post_id:
        row = store.db.execute("SELECT text FROM cm_posts WHERE id=?", (post_id,)).fetchone()
        if row and row[0]:
            n = len(row[0])
            if n <= 120:
                return "short"
            if n <= 280:
                return "medium"
            return "long"
    return "short"


def record_interaction_event(
    store,
    owner: str,
    *,
    post_id: str = "",
    topic_key: str = "",
    event_type: str,
    value: float = 1.0,
    area_coarse: str | None = None,
    device_class: str = "unknown",
    time_bucket: str | None = None,
    user_state: str = "unknown",
    format_bucket: str | None = None,
    session_id: str = "",
    dedupe_key: str = "",
    created_at: str | None = None,
) -> dict[str, Any]:
    """Persist one deduped interaction event and project it into `cm_usage_profile`."""
    setup_context_profile(store)
    etype = (event_type or "").strip().lower()
    if etype not in EVENT_TYPES:
        raise HTTPException(422, f"Unsupported event_type: {etype}")
    clean_state = (user_state or "unknown").strip().lower()
    if clean_state not in _USER_STATE_SET:
        clean_state = "unknown"
    clean_device = (device_class or "unknown").strip().lower()
    if clean_device not in _DEVICE_CLASS_SET:
        clean_device = "unknown"
    clean_topic = _normalize_topic_key(topic_key)
    ctx_now = get_ephemeral_context(owner) or {}
    # Ephemeral only (D22 / Rule 8+9): never permanently store area_coarse or user_state.
    clean_area = normalize_area_coarse(area_coarse or ctx_now.get("area_coarse") or "unknown")
    tb = (time_bucket or "").strip() or ctx_now.get("time_bucket") or compute_time_bucket()[0]
    fmt = _infer_format_bucket(store, post_id, format_bucket)
    stamp = created_at or _now_iso()
    dkey = (dedupe_key or "").strip()[:160]
    sess = (session_id or "").strip()[:120]
    persisted_area = "unknown"
    persisted_state = "unknown"

    if dkey:
        existing = store.db.execute(
            "SELECT id,owner,post_id,topic_key,event_type,value,area_coarse,device_class,time_bucket,user_state,session_id,dedupe_key,created_at FROM cm_interaction_events WHERE owner=? AND dedupe_key=?",
            (owner, dkey),
        ).fetchone()
        if existing:
            return {
                "deduped": True,
                "event": {
                    "id": existing[0], "owner": existing[1], "post_id": existing[2],
                    "topic_key": existing[3], "event_type": existing[4], "value": float(existing[5]),
                    # Echo request/ephemeral values; SQL columns stay unknown.
                    "area_coarse": clean_area, "device_class": existing[7], "time_bucket": existing[8],
                    "user_state": clean_state, "session_id": existing[10], "dedupe_key": existing[11],
                    "created_at": existing[12],
                },
                "profile_entry": None,
            }

    seen_session_before = False
    if sess and clean_topic:
        seen_session_before = bool(
            store.db.execute(
                "SELECT 1 FROM cm_interaction_events WHERE owner=? AND topic_key=? AND time_bucket=? AND session_id=? LIMIT 1",
                (owner, clean_topic, tb, sess),
            ).fetchone()
        )

    eid = uuid4().hex
    store.db.execute(
        """INSERT OR IGNORE INTO cm_interaction_events
           (id,owner,post_id,topic_key,event_type,value,area_coarse,device_class,time_bucket,user_state,session_id,dedupe_key,created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (eid, owner, post_id or "", clean_topic, etype, float(value), persisted_area, clean_device, tb, persisted_state, sess, dkey, stamp),
    )

    # Refresh ephemeral TTL envelope only (never SQL) when context-aware is opted in.
    if is_context_aware_enabled(store, owner) and (clean_area != "unknown" or clean_state != "unknown"):
        tb_now, is_wk = compute_time_bucket()
        set_ephemeral_context(
            owner,
            {
                "area_coarse": clean_area if clean_area != "unknown" else ctx_now.get("area_coarse", "unknown"),
                "device_class": clean_device,
                "time_bucket": tb or tb_now,
                "is_weekend": bool(ctx_now.get("is_weekend", is_wk)),
                "user_state": clean_state if clean_state != "unknown" else ctx_now.get("user_state", "unknown"),
                "confidence": float(ctx_now.get("confidence") or 0.0),
                "source": str(ctx_now.get("source") or "event"),
                "updated_at": stamp,
            },
            ttl_seconds=CONTEXT_TTL_SECONDS,
        )

    profile_entry = None
    # Rule 9: never persist sensitive topics into long-term usage profile.
    # D22: usage profile buckets never key on ephemeral area_coarse.
    if clean_topic and not is_sensitive_topic(clean_topic):
        profile_entry = _project_usage_event(
            store,
            owner=owner,
            topic_key=clean_topic,
            time_bucket=tb,
            area_coarse=persisted_area,
            format_bucket=fmt,
            event_type=etype,
            value=float(value),
            session_id=sess,
            seen_session_before=seen_session_before,
            stamp=stamp,
        )

    store.db.commit()
    return {
        "deduped": False,
        "event": {
            "id": eid, "owner": owner, "post_id": post_id or "",
            "topic_key": clean_topic, "event_type": etype, "value": float(value),
            "area_coarse": clean_area, "device_class": clean_device, "time_bucket": tb,
            "user_state": clean_state, "session_id": sess, "dedupe_key": dkey,
            "created_at": stamp,
        },
        "profile_entry": profile_entry,
    }


def _project_usage_event(
    store,
    *,
    owner: str,
    topic_key: str,
    time_bucket: str,
    area_coarse: str,
    format_bucket: str,
    event_type: str,
    value: float,
    session_id: str,
    seen_session_before: bool,
    stamp: str,
) -> dict[str, Any]:
    row = store.db.execute(
        f"SELECT {','.join(_USAGE_COLS)} FROM cm_usage_profile WHERE owner=? AND topic_key=? AND time_bucket=? AND area_coarse=? AND format_bucket=?",
        (owner, topic_key, time_bucket, area_coarse, format_bucket),
    ).fetchone()

    pos_delta = 0.0
    neg_delta = 0.0
    lowered_at = None
    if event_type in _POSITIVE_EVENT_WEIGHTS:
        if event_type == "dwell":
            # value may be seconds (e.g. 15s -> 0.6) or normalized [0,1].
            scaled = min(1.0, value / 15.0) if value > 1.0 else max(0.1, value)
            pos_delta = _POSITIVE_EVENT_WEIGHTS["dwell"] * scaled
        else:
            pos_delta = _POSITIVE_EVENT_WEIGHTS[event_type] * max(0.1, min(3.0, value))
    elif event_type in _NEGATIVE_EVENT_WEIGHTS:
        neg_delta = _NEGATIVE_EVENT_WEIGHTS[event_type] * max(0.1, min(3.0, value))
    elif event_type == "lower":
        lowered_at = stamp

    if row is None:
        first_seen = stamp
        last_seen = stamp
        pos_score = pos_delta
        neg_score = neg_delta
        evidence_count = 1
        distinct_sessions = 1
        suppressed = 0
        store.db.execute(
            """INSERT INTO cm_usage_profile
               (owner,topic_key,time_bucket,area_coarse,format_bucket,positive_score,negative_score,evidence_count,distinct_sessions,first_seen_at,last_seen_at,lowered_at,suppressed,updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (owner, topic_key, time_bucket, area_coarse, format_bucket,
             pos_score, neg_score, evidence_count, distinct_sessions,
             first_seen, last_seen, lowered_at, suppressed, stamp),
        )
    else:
        d = _row_to_dict(row)
        pos_score = float(d["positive_score"]) + pos_delta
        neg_score = float(d["negative_score"]) + neg_delta
        evidence_count = int(d["evidence_count"]) + 1
        distinct_sessions = int(d["distinct_sessions"])
        if session_id and not seen_session_before:
            distinct_sessions += 1
        elif distinct_sessions == 0:
            distinct_sessions = 1
        first_seen = min(d["first_seen_at"], stamp) if d["first_seen_at"] else stamp
        last_seen = max(d["last_seen_at"], stamp) if d["last_seen_at"] else stamp
        cur_lowered = stamp if event_type == "lower" else d.get("lowered_at")
        # Only explicit restore or explicit D19b recall clears lowered_at.
        store.db.execute(
            """UPDATE cm_usage_profile
               SET positive_score=?, negative_score=?, evidence_count=?, distinct_sessions=?,
                   first_seen_at=?, last_seen_at=?, lowered_at=?, updated_at=?
               WHERE owner=? AND topic_key=? AND time_bucket=? AND area_coarse=? AND format_bucket=?""",
            (pos_score, neg_score, evidence_count, distinct_sessions,
             first_seen, last_seen, cur_lowered, stamp,
             owner, topic_key, time_bucket, area_coarse, format_bucket),
        )

    updated = store.db.execute(
        f"SELECT {','.join(_USAGE_COLS)} FROM cm_usage_profile WHERE owner=? AND topic_key=? AND time_bucket=? AND area_coarse=? AND format_bucket=?",
        (owner, topic_key, time_bucket, area_coarse, format_bucket),
    ).fetchone()
    return _present_usage_entry(updated, context_enabled=is_context_aware_enabled(store, owner))


# ---------------------------------------------------------------- D19 Lower / Restore / D19b Recall
def list_usage_profile(
    store,
    owner: str,
    *,
    include_lowered: bool = True,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    setup_context_profile(store)
    ctx_enabled = is_context_aware_enabled(store, owner)
    rows = store.db.execute(
        f"SELECT {','.join(_USAGE_COLS)} FROM cm_usage_profile WHERE owner=? ORDER BY updated_at DESC, topic_key",
        (owner,),
    ).fetchall()
    out = []
    for r in rows:
        entry = _present_usage_entry(r, context_enabled=ctx_enabled, now=now)
        if not include_lowered and entry["lowered"]:
            continue
        out.append(entry)
    return out


def lower_usage_topic(
    store,
    owner: str,
    topic_key: str,
    *,
    time_bucket: str | None = None,
    area_coarse: str | None = None,
    format_bucket: str | None = None,
) -> dict[str, Any]:
    setup_context_profile(store)
    clean_topic = _normalize_topic_key(topic_key)
    if not clean_topic:
        raise HTTPException(422, "topic_key is required")
    stamp = _now_iso()
    clauses = ["owner=?", "topic_key=?"]
    params: list[Any] = [owner, clean_topic]
    if time_bucket:
        clauses.append("time_bucket=?")
        params.append(time_bucket)
    if area_coarse:
        clauses.append("area_coarse=?")
        params.append(normalize_area_coarse(area_coarse))
    if format_bucket:
        clauses.append("format_bucket=?")
        params.append(format_bucket)
    where = " AND ".join(clauses)
    rows = store.db.execute(
        f"SELECT {','.join(_USAGE_COLS)} FROM cm_usage_profile WHERE {where}",
        tuple(params),
    ).fetchall()
    store.db.execute(
        f"UPDATE cm_usage_profile SET lowered_at=?, updated_at=? WHERE {where}",
        (stamp, stamp, *params),
    )
    store.db.commit()
    ctx_enabled = is_context_aware_enabled(store, owner)
    updated_rows = store.db.execute(
        f"SELECT {','.join(_USAGE_COLS)} FROM cm_usage_profile WHERE {where}",
        tuple(params),
    ).fetchall()
    entries = [_present_usage_entry(r, context_enabled=ctx_enabled) for r in updated_rows]
    return {"topic_key": clean_topic, "lowered": True, "weight": WEIGHT_MIN, "updated": len(rows), "entries": entries}


def restore_usage_topic(
    store,
    owner: str,
    topic_key: str,
    *,
    time_bucket: str | None = None,
    area_coarse: str | None = None,
    format_bucket: str | None = None,
) -> dict[str, Any]:
    setup_context_profile(store)
    clean_topic = _normalize_topic_key(topic_key)
    if not clean_topic:
        raise HTTPException(422, "topic_key is required")
    stamp = _now_iso()
    clauses = ["owner=?", "topic_key=?"]
    params: list[Any] = [owner, clean_topic]
    if time_bucket:
        clauses.append("time_bucket=?")
        params.append(time_bucket)
    if area_coarse:
        clauses.append("area_coarse=?")
        params.append(normalize_area_coarse(area_coarse))
    if format_bucket:
        clauses.append("format_bucket=?")
        params.append(format_bucket)
    where = " AND ".join(clauses)
    store.db.execute(
        f"UPDATE cm_usage_profile SET lowered_at=NULL, suppressed=0, updated_at=? WHERE {where}",
        (stamp, *params),
    )
    store.db.commit()
    ctx_enabled = is_context_aware_enabled(store, owner)
    updated_rows = store.db.execute(
        f"SELECT {','.join(_USAGE_COLS)} FROM cm_usage_profile WHERE {where}",
        tuple(params),
    ).fetchall()
    entries = [_present_usage_entry(r, context_enabled=ctx_enabled) for r in updated_rows]
    return {"topic_key": clean_topic, "restored": True, "updated": len(entries), "entries": entries}


def recall_usage_topic(
    store,
    owner: str,
    topic_key: str,
    *,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    """D19b explicit recall: 100% callable even if lowered (0.01) or aged (0.05).

    Clears `lowered_at`, refreshes `last_seen_at`, and boosts effective weight to
    `min(1.0, max(0.35, w_eff + 0.25))`. Evidence counters stay untouched (Rule 9
    two-visit must not be fabricated). Matches the normalized topic key exactly.
    """
    setup_context_profile(store)
    clean_topic = _normalize_topic_key(topic_key)
    if not clean_topic:
        return []
    now_dt = now or _now_dt()
    if now_dt.tzinfo is None:
        now_dt = now_dt.replace(tzinfo=timezone.utc)
    stamp = now_dt.isoformat(timespec="seconds")

    rows = store.db.execute(
        f"SELECT {','.join(_USAGE_COLS)} FROM cm_usage_profile WHERE owner=? AND lower(topic_key)=?",
        (owner, clean_topic),
    ).fetchall()
    targets = [r for r in rows if _normalize_topic_key(r[1]) == clean_topic]

    ctx_enabled = is_context_aware_enabled(store, owner)
    recalled: list[dict[str, Any]] = []
    for r in targets:
        d = _row_to_dict(r)
        w_eff = compute_usage_weight(d, now=now_dt)
        w_new = min(1.0, max(RECALL_MIN_WEIGHT, w_eff + RECALL_BOOST_DELTA))
        net_needed = _weight_to_net_score(w_new)
        neg = float(d.get("negative_score") or 0.0)
        new_pos = max(float(d.get("positive_score") or 0.0), neg + net_needed)
        # Rule 9: never fabricate distinct_sessions / evidence_count.
        store.db.execute(
            """UPDATE cm_usage_profile
               SET positive_score=?, last_seen_at=?, lowered_at=NULL, suppressed=0, updated_at=?
               WHERE owner=? AND topic_key=? AND time_bucket=? AND area_coarse=? AND format_bucket=?""",
            (new_pos, stamp, stamp,
             owner, d["topic_key"], d["time_bucket"], d["area_coarse"], d["format_bucket"]),
        )
        updated = store.db.execute(
            f"SELECT {','.join(_USAGE_COLS)} FROM cm_usage_profile WHERE owner=? AND topic_key=? AND time_bucket=? AND area_coarse=? AND format_bucket=?",
            (owner, d["topic_key"], d["time_bucket"], d["area_coarse"], d["format_bucket"]),
        ).fetchone()
        recalled.append(_present_usage_entry(updated, context_enabled=ctx_enabled, now=now_dt))

    if targets:
        store.db.commit()
    return recalled


# ---------------------------------------------------------------- FastAPI models & routes
class HeartbeatIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # Coarse area only crosses the boundary (S3) — raw lat/lng stay on-device.
    area_coarse: str | None = Field(default=None, max_length=80)
    device_class: str = Field(default="unknown", max_length=40)
    user_state: str = Field(default="unknown", max_length=40)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    source: str = Field(default="unavailable", max_length=40)

    @field_validator("user_state")
    @classmethod
    def _validate_user_state(cls, v: str) -> str:
        low = (v or "unknown").strip().lower()
        if low not in _USER_STATE_SET:
            raise ValueError(f"user_state must be one of {USER_STATES}")
        return low

    @field_validator("device_class")
    @classmethod
    def _validate_device_class(cls, v: str) -> str:
        low = (v or "unknown").strip().lower()
        if low not in _DEVICE_CLASS_SET:
            raise ValueError(f"device_class must be one of {DEVICE_CLASSES}")
        return low


class InteractionEventIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    post_id: str = Field(default="", max_length=120)
    topic_key: str = Field(default="", max_length=120)
    event_type: str = Field(pattern="^(upvote|downvote|reply|bookmark|repost|dwell|hide|lower)$")
    value: float = Field(default=1.0, ge=0.0, le=1000.0)
    area_coarse: str | None = Field(default=None, max_length=80)
    device_class: str = Field(default="unknown", max_length=40)
    time_bucket: str | None = Field(default=None, max_length=40)
    user_state: str = Field(default="unknown", max_length=40)
    format_bucket: str | None = Field(default=None, max_length=20)
    session_id: str = Field(default="", max_length=120)
    dedupe_key: str = Field(default="", max_length=160)


class TopicActionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    topic_key: str = Field(min_length=1, max_length=120)
    time_bucket: str | None = Field(default=None, max_length=40)
    area_coarse: str | None = Field(default=None, max_length=80)
    format_bucket: str | None = Field(default=None, max_length=20)


class RecallIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    topic_key: str | None = Field(default=None, max_length=120)
    query: str | None = Field(default=None, max_length=200)


class UsageSettingsIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    context_aware_enabled: bool


@router.post("/api/community/context/heartbeat")
def context_heartbeat(body: HeartbeatIn, request: Request):
    store, owner = scope(request)
    with store.lock:
        enabled = is_context_aware_enabled(store, owner)
    area = normalize_area_coarse(body.area_coarse)
    time_bucket, is_weekend = compute_time_bucket()
    payload = {
        "area_coarse": area,
        "device_class": body.device_class,
        "time_bucket": time_bucket,
        "is_weekend": is_weekend,
        "user_state": body.user_state,
        "confidence": body.confidence,
        "source": body.source,
        "updated_at": _now_iso(),
    }
    if not enabled:
        clear_ephemeral_context(owner)
        return {
            "context": _sanitize_context_payload(payload),
            "stored": False,
            "context_aware_enabled": False,
            "ttl_seconds": CONTEXT_TTL_SECONDS,
            "backend": "disabled",
            "raw_coordinates_persisted": False,
        }
    stored_ctx, backend = set_ephemeral_context(owner, payload, ttl_seconds=CONTEXT_TTL_SECONDS)
    return {
        "context": stored_ctx,
        "stored": True,
        "context_aware_enabled": True,
        "ttl_seconds": CONTEXT_TTL_SECONDS,
        "backend": backend,
        "raw_coordinates_persisted": False,
    }


@router.get("/api/community/context/current")
def context_current(request: Request):
    store, owner = scope(request)
    with store.lock:
        enabled = is_context_aware_enabled(store, owner)
    ctx = get_ephemeral_context(owner) if enabled else None
    time_bucket, is_weekend = compute_time_bucket()
    return {
        "context": ctx,
        "active": ctx is not None,
        "time_bucket": time_bucket,
        "is_weekend": is_weekend,
        "ttl_seconds": CONTEXT_TTL_SECONDS,
        "context_aware_enabled": enabled,
    }


@router.post("/api/community/events")
def log_interaction_event(body: InteractionEventIn, request: Request):
    store, owner = scope(request)
    with store.lock:
        res = record_interaction_event(
            store,
            owner,
            post_id=body.post_id,
            topic_key=body.topic_key,
            event_type=body.event_type,
            value=body.value,
            area_coarse=body.area_coarse,
            device_class=body.device_class,
            time_bucket=body.time_bucket,
            user_state=body.user_state,
            format_bucket=body.format_bucket,
            session_id=body.session_id,
            dedupe_key=body.dedupe_key,
        )
    return res


@router.get("/api/community/profile/usage")
def get_usage_profile(request: Request, include_lowered: bool = Query(default=True)):
    store, owner = scope(request)
    with store.lock:
        entries = list_usage_profile(store, owner, include_lowered=include_lowered)
        enabled = is_context_aware_enabled(store, owner)
    return {
        "entries": entries,
        "usage": entries,
        "count": len(entries),
        "include_lowered": include_lowered,
        "context_aware_enabled": enabled,
    }


@router.post("/api/community/profile/usage/lower")
def lower_usage(body: TopicActionIn, request: Request):
    store, owner = scope(request)
    with store.lock:
        return lower_usage_topic(
            store,
            owner,
            body.topic_key,
            time_bucket=body.time_bucket,
            area_coarse=body.area_coarse,
            format_bucket=body.format_bucket,
        )


@router.post("/api/community/profile/usage/restore")
def restore_usage(body: TopicActionIn, request: Request):
    store, owner = scope(request)
    with store.lock:
        return restore_usage_topic(
            store,
            owner,
            body.topic_key,
            time_bucket=body.time_bucket,
            area_coarse=body.area_coarse,
            format_bucket=body.format_bucket,
        )


@router.post("/api/community/profile/usage/recall")
def recall_usage(body: RecallIn, request: Request):
    store, owner = scope(request)
    query_text = (body.query or body.topic_key or "").strip()
    if not query_text:
        raise HTTPException(422, "topic_key or query is required")
    from .recommender import recall_lowered_and_boost

    with store.lock:
        return recall_lowered_and_boost(store, owner, query_text)


@router.put("/api/community/profile/usage/settings")
def update_usage_settings(body: UsageSettingsIn, request: Request):
    store, owner = scope(request)
    with store.lock:
        return set_context_aware_enabled(store, owner, body.context_aware_enabled)
