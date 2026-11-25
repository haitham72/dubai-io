"""Real 4-Stage Two-Tower Community Recommender (E14b / D11 / D19 / D19b / Rule 9).

Stages:
1. Dual-tower candidate generation (`dim=128`) combining local `BAAI/bge-m3`
   when loaded (or deterministic hashed n-gram + E10 vocab warm-start) with
   optional trained weights from `cm_recommender_weights.json`, plus follow-graph
   recents and public cold-start trending posts. Uses `pgvector` when PG vector
   column is configured, else fast NumPy matrix multiply / pure-Python cosine.
2. Fail-closed Stage 2 hard policy & safety filters: private-group membership,
   blocks/mutes, soft-deleted, moderation `removed`, D11 `is_minor_protected`,
   Rule-9 `sensitive` topic suppression, and `user_state == 'driving'` safety mode.
3. Multi-task engagement scorer + `ContextFit` (`area_coarse`, `device_class`,
   `time_bucket`, `user_state`, active qualified `cm_usage_profile` >= 0.10).
4. Diversity re-ranking (max 2/author, max 3/group in top 20, 1-in-5 diversity
   slot) and strictly grounded deterministic `why_this` explanations.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re
from threading import RLock
from typing import Any, Mapping, Sequence
from uuid import uuid4
import zlib

try:
    import numpy as np
except Exception:  # pragma: no cover - numpy is available in venv
    np = None  # type: ignore[assignment]

from . import store as cm
from .context_profile import (
    DUBAI_AREAS,
    SURFACE_THRESHOLD,
    compute_time_bucket,
    compute_usage_weight,
    get_ephemeral_context,
    is_context_aware_enabled,
    is_sensitive_topic,
    is_usage_qualified,
    normalize_area_coarse,
    recall_usage_topic,
    setup_context_profile,
)
from .moderation import is_minor_age_band
from .routes import group_row, is_active_member, profile_by_owner

DIM = 128
_TOKEN_RE = re.compile(r"[#]?[a-z0-9_\u0621-\u064a]{2,}", re.I)
_HASHTAG_RE = re.compile(r"#([a-z0-9_]{2,40})", re.I)

DDL = (
    """CREATE TABLE IF NOT EXISTS cm_post_embeddings (
        post_id TEXT PRIMARY KEY,
        vec_json TEXT NOT NULL,
        topic_path TEXT NOT NULL DEFAULT '',
        area_coarse TEXT NOT NULL DEFAULT 'unknown',
        flair TEXT NOT NULL DEFAULT '',
        text_len INTEGER NOT NULL DEFAULT 0,
        updated_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS cm_recommendation_events (
        id TEXT PRIMARY KEY,
        owner TEXT NOT NULL,
        candidate_type TEXT,
        candidate_id TEXT,
        features TEXT NOT NULL DEFAULT '[]',
        why_this TEXT NOT NULL DEFAULT '',
        reason TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL
    )""",
)

DEFAULT_TASK_WEIGHTS: dict[str, float] = {
    "tower": 1.35,
    "upvote": 0.45,
    "reply": 0.40,
    "bookmark": 0.50,
    "repost": 0.35,
    "dwell": 0.25,
    "downvote": 0.55,
    "context_fit": 0.85,
}

# ---------------------------------------------------------------- caches (vocab, projection, weights, matrix)
_CACHE_LOCK = RLock()
_VOCAB_INDEX: dict[str, Any] | None = None
_BGE_PROJ: Any = None
_WEIGHTS_CACHE: dict[str, Any] | None = None
_WEIGHTS_MTIME: float | None = None
_WEIGHTS_PATH_LOADED: str | None = None
_MATRIX_CACHE: dict[int, tuple[int, str, list[str], Any, dict[str, dict[str, Any]]]] = {}


def setup_recommender(store) -> None:
    if getattr(store, "_recommender_ready", False):
        return
    cm.setup(store)
    setup_context_profile(store)
    for stmt in DDL:
        store.db.execute(stmt)
    if getattr(store.db, "dialect", "sqlite") == "postgres":
        try:
            store.db.execute(f"ALTER TABLE cm_post_embeddings ADD COLUMN IF NOT EXISTS vec vector({DIM})")
            store.db.execute(
                "CREATE INDEX IF NOT EXISTS cm_post_embeddings_hnsw ON cm_post_embeddings USING hnsw (vec vector_cosine_ops)"
            )
            store._pgvector_ready = True
        except Exception:
            store._pgvector_ready = False
    else:
        store._pgvector_ready = False
    store.db.commit()
    store._recommender_ready = True


def _weights_candidates() -> list[Path]:
    env_p = (os.environ.get("CM_RECOMMENDER_WEIGHTS") or "").strip()
    cands: list[Path] = []
    if env_p:
        cands.append(Path(env_p))
    root = Path(__file__).resolve().parents[4]
    cands.append(root / "apps" / "api" / "data" / "cm_recommender_weights.json")
    cands.append(Path(__file__).with_name("cm_recommender_weights.json"))
    return cands


def load_trained_weights(*, force: bool = False) -> dict[str, Any] | None:
    """Load optional trained two-tower weights (`cm_recommender_weights.json`)."""
    global _WEIGHTS_CACHE, _WEIGHTS_MTIME, _WEIGHTS_PATH_LOADED
    for path in _weights_candidates():
        if not path.is_file():
            continue
        try:
            mtime = path.stat().st_mtime
            with _CACHE_LOCK:
                if (
                    not force
                    and _WEIGHTS_CACHE is not None
                    and _WEIGHTS_PATH_LOADED == str(path)
                    and _WEIGHTS_MTIME == mtime
                ):
                    return _WEIGHTS_CACHE
                raw = json.loads(path.read_text(encoding="utf-8"))
                if np is not None:
                    if "W_item" in raw:
                        raw["_W_item_np"] = np.asarray(raw["W_item"], dtype=np.float32)
                    if "W_user" in raw:
                        raw["_W_user_np"] = np.asarray(raw["W_user"], dtype=np.float32)
                _WEIGHTS_CACHE = raw
                _WEIGHTS_MTIME = mtime
                _WEIGHTS_PATH_LOADED = str(path)
                return raw
        except Exception:
            continue
    return None


def _get_vocab_index() -> dict[str, Any]:
    global _VOCAB_INDEX
    if _VOCAB_INDEX is not None:
        return _VOCAB_INDEX
    with _CACHE_LOCK:
        if _VOCAB_INDEX is not None:
            return _VOCAB_INDEX
        token_to_topic: dict[str, tuple[str, str, bool]] = {}
        try:
            from temporal_memory.vocab import get_vocab

            vocab = get_vocab()
            for node in vocab.nodes:
                info = (node.path, node.cluster, bool(node.sensitive))
                for term in node.folded_terms:
                    token_to_topic.setdefault(term, info)
                    for part in term.split():
                        if len(part) >= 3:
                            token_to_topic.setdefault(part, info)
        except Exception:
            pass
        _VOCAB_INDEX = {"token_to_topic": token_to_topic}
        return _VOCAB_INDEX


def _get_bge_projection():
    global _BGE_PROJ
    if _BGE_PROJ is not None:
        return _BGE_PROJ
    if np is None:
        return None
    with _CACHE_LOCK:
        if _BGE_PROJ is None:
            rng = np.random.default_rng(20261125)
            mat = rng.normal(0.0, 1.0 / math.sqrt(DIM), size=(1024, DIM)).astype(np.float32)
            _BGE_PROJ = mat
        return _BGE_PROJ


# ---------------------------------------------------------------- math / vector utilities
def _l2_normalize_list(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vec))
    if norm <= 1e-12:
        return [0.0] * len(vec)
    inv = 1.0 / norm
    return [float(v * inv) for v in vec]


def _l2_normalize_np(arr):
    norm = float(np.linalg.norm(arr))
    if norm <= 1e-12:
        return np.zeros_like(arr, dtype=np.float32)
    return (arr / norm).astype(np.float32)


def _hash_feature(vec_arr, key: str, weight: float) -> None:
    h = zlib.crc32(key.encode("utf-8"))
    idx = h % DIM
    sign = 1.0 if ((h >> 8) & 1) == 0 else -1.0
    vec_arr[idx] += sign * weight
    idx2 = ((h >> 16) ^ (h * 2654435761)) % DIM
    sign2 = 1.0 if ((h >> 24) & 1) == 0 else -1.0
    vec_arr[idx2] += sign2 * (0.5 * weight)


def _detect_area_in_text(text: str) -> str:
    low = (text or "").lower()
    for name in DUBAI_AREAS:
        if name.lower() in low:
            return name
    if "marina" in low:
        return "Dubai Marina"
    if "downtown" in low:
        return "Downtown Dubai"
    return "unknown"


def _detect_topic_and_cluster(text: str, explicit_topic: str = "") -> tuple[str, str]:
    idx = _get_vocab_index()["token_to_topic"]
    if explicit_topic:
        low = explicit_topic.strip().lower().lstrip("#")
        hit = idx.get(low)
        if hit and not hit[2]:
            return hit[0], hit[1]
    tokens = _TOKEN_RE.findall((text or "").lower())
    for tok in tokens:
        clean = tok.lstrip("#")
        hit = idx.get(clean)
        if hit and not hit[2]:
            return hit[0], hit[1]
    return "", ""


def _length_bucket(text_len: int) -> str:
    if text_len <= 120:
        return "short"
    if text_len <= 280:
        return "medium"
    return "long"


def _apply_matrix(vec_list: list[float], weights_key: str) -> list[float]:
    weights = load_trained_weights()
    if not weights:
        return _l2_normalize_list(vec_list)
    if np is not None:
        w_np = weights.get(f"_{weights_key}_np")
        if w_np is not None and w_np.shape == (DIM, DIM):
            arr = np.asarray(vec_list, dtype=np.float32)
            proj = arr @ w_np
            return _l2_normalize_np(proj).tolist()
    mat = weights.get(weights_key)
    if isinstance(mat, list) and len(mat) == DIM:
        out = [sum(vec_list[i] * float(mat[i][j]) for i in range(DIM)) for j in range(DIM)]
        return _l2_normalize_list(out)
    return _l2_normalize_list(vec_list)


def _try_bge_m3_128(text: str, *, is_query: bool = False) -> list[float] | None:
    try:
        from temporal_memory.core import embed as tm_embed

        if not tm_embed.is_loaded():
            return None
        if is_query:
            raw = tm_embed.embed_query(text)
        else:
            raw = tm_embed.embed_passages([text])[0]
        if np is not None:
            proj = _get_bge_projection()
            arr = np.asarray(raw, dtype=np.float32)
            if proj is not None and arr.shape == (1024,):
                return _l2_normalize_np(arr @ proj).tolist()
        return _l2_normalize_list([float(x) for x in raw[:DIM]])
    except Exception:
        return None


# ---------------------------------------------------------------- Tower Encoders
def encode_text_topic_vector(
    text: str,
    *,
    topic_path: str = "",
    area_coarse: str = "unknown",
    flair: str = "",
    text_len: int | None = None,
    is_query: bool = False,
    apply_trained: bool = False,
) -> list[float]:
    """Deterministic 128-d semantic + E10 topic + metadata embedding."""
    if np is not None:
        vec = np.zeros(DIM, dtype=np.float32)
    else:
        vec = [0.0] * DIM  # type: ignore[assignment]

    clean_text = (text or "").strip()
    bge = _try_bge_m3_128(clean_text, is_query=is_query) if clean_text else None
    if bge is not None:
        if np is not None:
            vec += np.asarray(bge, dtype=np.float32) * 1.4
        else:
            for i in range(DIM):
                vec[i] += bge[i] * 1.4

    tokens = _TOKEN_RE.findall(clean_text.lower())
    vocab_idx = _get_vocab_index()["token_to_topic"]
    for i, tok in enumerate(tokens):
        clean_tok = tok.lstrip("#")
        if is_sensitive_topic(clean_tok):
            continue
        is_tag = tok.startswith("#")
        _hash_feature(vec, f"tok:{clean_tok}", 1.4 if is_tag else 1.0)
        if i + 1 < len(tokens):
            nxt = tokens[i + 1].lstrip("#")
            if not is_sensitive_topic(nxt):
                _hash_feature(vec, f"bi:{clean_tok}_{nxt}", 0.55)
        hit = vocab_idx.get(clean_tok)
        if hit and not hit[2]:
            _hash_feature(vec, f"topic:{hit[0]}", 1.1)
            _hash_feature(vec, f"cluster:{hit[1]}", 0.7)

    if topic_path and not is_sensitive_topic(topic_path):
        _hash_feature(vec, f"topic:{topic_path}", 1.2)
    norm_area = normalize_area_coarse(area_coarse)
    if norm_area != "unknown":
        _hash_feature(vec, f"area:{norm_area.lower()}", 0.9)
    if flair:
        _hash_feature(vec, f"flair:{flair.strip().lower()}", 0.6)
    if text_len is not None:
        _hash_feature(vec, f"fmt:{_length_bucket(int(text_len))}", 0.4)

    base = _l2_normalize_np(vec).tolist() if np is not None else _l2_normalize_list(list(vec))
    if apply_trained:
        return _apply_matrix(base, "W_item" if not is_query else "W_user")
    return base


def encode_item_vector(
    text: str,
    *,
    tags: Sequence[str] = (),
    group_name: str = "",
    area_coarse: str = "unknown",
    flair: str = "",
    topic_path: str = "",
) -> tuple[list[float], str, str]:
    """Encode a community post into `(vec_128, resolved_topic_path, resolved_area)`."""
    merged = " ".join(part for part in (text, " ".join(f"#{t.lstrip('#')}" for t in tags), group_name) if part)
    t_path, _cluster = _detect_topic_and_cluster(merged, explicit_topic=topic_path)
    area = normalize_area_coarse(area_coarse)
    if area == "unknown":
        area = _detect_area_in_text(merged)
    vec = encode_text_topic_vector(
        merged,
        topic_path=t_path,
        area_coarse=area,
        flair=flair,
        text_len=len(text or ""),
        is_query=False,
        apply_trained=True,
    )
    return vec, t_path, area


def encode_user_context_vector(
    store,
    owner: str,
    *,
    interests: Sequence[str] = (),
    profile_area: str = "unknown",
    bridge_features: Sequence[Any] = (),
    usage_entries: Sequence[Mapping[str, Any]] = (),
    recent_events: Sequence[Mapping[str, Any]] = (),
    context: Mapping[str, Any] | None = None,
    is_minor: bool = False,
    context_enabled: bool = True,
) -> list[float]:
    """Encode User + Context Tower (`128-d`). Returns zero vector if minor-protected or cold."""
    if is_minor:
        return [0.0] * DIM
    acc = np.zeros(DIM, dtype=np.float32) if np is not None else [0.0] * DIM

    def _add(v: Sequence[float], weight: float) -> None:
        if weight == 0.0:
            return
        if np is not None:
            nonlocal acc
            acc += np.asarray(v, dtype=np.float32) * float(weight)
        else:
            for i in range(DIM):
                acc[i] += float(v[i]) * float(weight)

    # 1. Consented long-term interests + bridge InterestFeatures.
    clean_interests = [str(i).strip() for i in interests if str(i).strip() and not is_sensitive_topic(str(i))]
    if clean_interests:
        _add(
            encode_text_topic_vector(
                " ".join(clean_interests),
                area_coarse=profile_area,
                is_query=True,
                apply_trained=False,
            ),
            1.0,
        )

    for feat in bridge_features:
        slug = getattr(feat, "topic_slug", "") or ""
        label = getattr(feat, "topic_label", "") or ""
        if is_sensitive_topic(slug) or is_sensitive_topic(label):
            continue
        w = float(getattr(feat, "weight", 0.5) or 0.5)
        _add(encode_text_topic_vector(f"{slug} {label}", is_query=True, apply_trained=False), 0.7 * w)

    # 2. Active qualified usage profile affinities (weight >= 0.10 only).
    if context_enabled:
        for entry in usage_entries:
            topic = str(entry.get("topic_key") or "")
            if not topic or is_sensitive_topic(topic):
                continue
            if not entry.get("active_in_feed"):
                continue
            w = float(entry.get("weight") or 0.0)
            if w < SURFACE_THRESHOLD:
                continue
            _add(
                encode_text_topic_vector(
                    topic,
                    area_coarse=str(entry.get("area_coarse") or "unknown"),
                    is_query=True,
                    apply_trained=False,
                ),
                0.9 * w,
            )

    # 3. 30-min half-life decayed recent session interactions.
    now_dt = datetime.now(timezone.utc)
    for ev in recent_events:
        topic = str(ev.get("topic_key") or "")
        etype = str(ev.get("event_type") or "")
        if not topic or is_sensitive_topic(topic):
            continue
        if etype == "lower":
            continue
        created = _parse_iso_dt(ev.get("created_at"))
        age_min = max(0.0, (now_dt - created).total_seconds() / 60.0) if created else 0.0
        decay = 0.5 ** (age_min / 30.0)
        if etype in ("downvote", "hide"):
            _add(encode_text_topic_vector(topic, is_query=True, apply_trained=False), -0.45 * decay)
        else:
            ev_w = {"bookmark": 1.3, "reply": 1.2, "repost": 1.1, "upvote": 1.0, "dwell": 0.5}.get(etype, 0.5)
            _add(encode_text_topic_vector(topic, is_query=True, apply_trained=False), 0.65 * ev_w * decay)

    # 4. Ephemeral context vector (area, device, time_bucket, user_state).
    if context_enabled and context:
        ctx_vec = np.zeros(DIM, dtype=np.float32) if np is not None else [0.0] * DIM
        area = normalize_area_coarse(str(context.get("area_coarse") or "unknown"))
        if area != "unknown":
            _hash_feature(ctx_vec, f"area:{area.lower()}", 1.0)
        ustate = str(context.get("user_state") or "unknown").lower()
        dclass = str(context.get("device_class") or "unknown").lower()
        if ustate in ("walking", "running", "driving") or dclass in ("mobile_ios", "mobile_android", "mobile_web"):
            _hash_feature(ctx_vec, "fmt:short", 0.5)
        elif ustate in ("sitting", "stationary") and dclass == "desktop":
            _hash_feature(ctx_vec, "fmt:long", 0.4)
        _add(ctx_vec, 0.35)

    raw_list = _l2_normalize_np(acc).tolist() if np is not None else _l2_normalize_list(list(acc))
    if all(abs(x) < 1e-12 for x in raw_list):
        return [0.0] * DIM
    return _apply_matrix(raw_list, "W_user")


def _parse_iso_dt(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


# ---------------------------------------------------------------- Embedding Store & Fast Stage-1 Matrix
def _upsert_post_embedding(
    store,
    post_id: str,
    text: str,
    *,
    group_name: str = "",
    area_coarse: str = "unknown",
    flair: str = "",
    tags: Sequence[str] = (),
    updated_at: str = "",
) -> dict[str, Any]:
    vec, topic_path, resolved_area = encode_item_vector(
        text, tags=tags, group_name=group_name, area_coarse=area_coarse, flair=flair
    )
    vec_json = json.dumps([round(float(x), 6) for x in vec])
    stamp = updated_at or cm.now()
    tlen = len(text or "")
    existing = store.db.execute("SELECT 1 FROM cm_post_embeddings WHERE post_id=?", (post_id,)).fetchone()
    if existing:
        store.db.execute(
            "UPDATE cm_post_embeddings SET vec_json=?,topic_path=?,area_coarse=?,flair=?,text_len=?,updated_at=? WHERE post_id=?",
            (vec_json, topic_path, resolved_area, flair, tlen, stamp, post_id),
        )
    else:
        store.db.execute(
            "INSERT INTO cm_post_embeddings (post_id,vec_json,topic_path,area_coarse,flair,text_len,updated_at) VALUES (?,?,?,?,?,?,?)",
            (post_id, vec_json, topic_path, resolved_area, flair, tlen, stamp),
        )
    if getattr(store, "_pgvector_ready", False):
        try:
            literal = "[" + ",".join(f"{float(v):.6f}" for v in vec) + "]"
            store.db.execute("UPDATE cm_post_embeddings SET vec=?::vector WHERE post_id=?", (literal, post_id))
        except Exception:
            pass
    return {
        "post_id": post_id,
        "vec": vec,
        "topic_path": topic_path,
        "area_coarse": resolved_area,
        "flair": flair,
        "text_len": tlen,
        "updated_at": stamp,
    }


def ensure_post_embeddings(store, post_rows: Sequence[tuple[Any, ...]], group_names: Mapping[str, str]) -> dict[str, dict[str, Any]]:
    """Ensure every active post has a cached 128-d embedding in `cm_post_embeddings`."""
    setup_recommender(store)
    existing_rows = store.db.execute(
        "SELECT post_id,vec_json,topic_path,area_coarse,flair,text_len,updated_at FROM cm_post_embeddings"
    ).fetchall()
    existing_map = {r[0]: r for r in existing_rows}

    to_insert: list[tuple[Any, ...]] = []
    meta_map: dict[str, dict[str, Any]] = {}
    for p in post_rows:
        pid = p[0]
        text = p[3] or ""
        gid = p[2]
        updated_at = p[9] or p[8] or ""
        cached = existing_map.get(pid)
        if cached and cached[6] >= updated_at:
            meta_map[pid] = {
                "post_id": pid,
                "vec_json": cached[1],
                "topic_path": cached[2],
                "area_coarse": cached[3],
                "flair": cached[4],
                "text_len": int(cached[5]),
                "updated_at": cached[6],
            }
            continue
        gname = group_names.get(gid, "") if gid else ""
        vec, topic_path, resolved_area = encode_item_vector(text, group_name=gname)
        vec_json = json.dumps([round(float(x), 6) for x in vec])
        tlen = len(text)
        stamp = updated_at or cm.now()
        if cached:
            store.db.execute(
                "UPDATE cm_post_embeddings SET vec_json=?,topic_path=?,area_coarse=?,flair='',text_len=?,updated_at=? WHERE post_id=?",
                (vec_json, topic_path, resolved_area, tlen, stamp, pid),
            )
        else:
            to_insert.append((pid, vec_json, topic_path, resolved_area, "", tlen, stamp))
        meta_map[pid] = {
            "post_id": pid,
            "vec": vec,
            "vec_json": vec_json,
            "topic_path": topic_path,
            "area_coarse": resolved_area,
            "flair": "",
            "text_len": tlen,
            "updated_at": stamp,
        }
    if to_insert:
        store.db.conn.executemany(
            "INSERT INTO cm_post_embeddings (post_id,vec_json,topic_path,area_coarse,flair,text_len,updated_at) VALUES (?,?,?,?,?,?,?)",
            to_insert,
        ) if hasattr(store.db, "conn") and getattr(store.db, "dialect", "sqlite") == "sqlite" else [
            store.db.execute(
                "INSERT OR IGNORE INTO cm_post_embeddings (post_id,vec_json,topic_path,area_coarse,flair,text_len,updated_at) VALUES (?,?,?,?,?,?,?)",
                row,
            )
            for row in to_insert
        ]
        store.db.commit()
    elif any(pid not in existing_map for pid in meta_map):
        store.db.commit()
    return meta_map


def _get_post_matrix(store, post_rows: Sequence[tuple[Any, ...]], meta_map: Mapping[str, dict[str, Any]]) -> tuple[list[str], Any]:
    """Return `(post_ids, matrix_Nx128)` cached on `store` for <150ms Stage-1 latency."""
    n_rows = len(post_rows)
    sig = max((meta_map[p[0]]["updated_at"] for p in post_rows), default="") if post_rows else ""
    head = tuple(p[0] for p in post_rows[:3])
    cached = getattr(store, "_recommender_matrix_cache", None)
    if cached and cached[0] == n_rows and cached[1] == sig and cached[2] == head:
        return cached[3], cached[4]

    pids: list[str] = []
    vecs: list[list[float]] = []
    for p in post_rows:
        pid = p[0]
        m = meta_map[pid]
        v = m.get("vec")
        if v is None:
            v = json.loads(m["vec_json"])
            m["vec"] = v
        pids.append(pid)
        vecs.append(v)

    mat = np.asarray(vecs, dtype=np.float32) if (np is not None and vecs) else vecs
    store._recommender_matrix_cache = (n_rows, sig, head, pids, mat)
    return pids, mat


# ---------------------------------------------------------------- Stage 2 Hard Filters
def _optional_table_set(store, sql: str, params: tuple[Any, ...]) -> set[str]:
    try:
        return {r[0] for r in store.db.execute(sql, params).fetchall() if r[0]}
    except Exception:
        return set()


def _load_policy_fences(store, owner: str) -> dict[str, Any]:
    blocked_owners = _optional_table_set(store, "SELECT blocked_owner FROM cm_user_blocks WHERE owner=?", (owner,))
    blocked_by = _optional_table_set(store, "SELECT owner FROM cm_user_blocks WHERE blocked_owner=?", (owner,))
    muted_owners = _optional_table_set(store, "SELECT target FROM cm_user_mutes WHERE owner=? AND kind='owner'", (owner,))
    muted_groups = _optional_table_set(store, "SELECT target FROM cm_user_mutes WHERE owner=? AND kind='group'", (owner,))
    muted_tags = {t.lower().lstrip("#") for t in _optional_table_set(store, "SELECT target FROM cm_user_mutes WHERE owner=? AND kind='tag'", (owner,))}
    removed_posts: set[str] = set()
    try:
        rows = store.db.execute(
            "SELECT target_id, target_state FROM cm_moderation_events WHERE target_type='post' ORDER BY created_at ASC"
        ).fetchall()
        latest_state: dict[str, str] = {}
        for tid, state in rows:
            latest_state[tid] = state
        removed_posts = {tid for tid, st in latest_state.items() if st == "removed"}
    except Exception:
        pass
    active_groups = {
        r[0]
        for r in store.db.execute("SELECT group_id FROM cm_group_members WHERE owner=? AND status='active'", (owner,)).fetchall()
    }
    return {
        "blocked_owners": blocked_owners | blocked_by,
        "muted_owners": muted_owners,
        "muted_groups": muted_groups,
        "muted_tags": muted_tags,
        "removed_posts": removed_posts,
        "active_groups": active_groups,
    }


def _check_is_minor(request, store, owner: str) -> bool:
    principal = getattr(getattr(request, "state", None), "community_principal", None) if request is not None else None
    if principal is not None and getattr(principal, "is_minor_protected", True):
        return True
    prof = profile_by_owner(store, owner)
    if prof is not None:
        return is_minor_age_band(prof[6])
    # Fail-closed when no profile exists unless a verified adult principal is attached.
    if principal is not None and not principal.is_minor_protected:
        return False
    return True


def _post_visible_to_owner(
    post_row: tuple[Any, ...],
    owner: str,
    groups_by_id: Mapping[str, tuple[Any, ...]],
    fences: Mapping[str, Any],
    *,
    allow_own: bool = False,
) -> bool:
    pid, author, gid, text, _rev, _pinned, deleted, *_ = post_row
    if deleted:
        return False
    if not allow_own and author == owner:
        return False
    if pid in fences["removed_posts"]:
        return False
    if author in fences["blocked_owners"] or author in fences["muted_owners"]:
        return False
    if gid:
        if gid in fences["muted_groups"]:
            return False
        g = groups_by_id.get(gid)
        if g and g[4] == "private" and gid not in fences["active_groups"]:
            return False
    if fences["muted_tags"]:
        tags = {m.lower() for m in _HASHTAG_RE.findall(text or "")}
        if tags & fences["muted_tags"]:
            return False
    return True


# ---------------------------------------------------------------- Engagement Priors + ContextFit + Re-Ranker
def _load_engagement_priors(store) -> dict[str, dict[str, float]]:
    priors: dict[str, dict[str, float]] = {}
    for pid, cnt in store.db.execute(
        "SELECT target_id, COUNT(*) FROM cm_reactions WHERE target_type='post' GROUP BY target_id"
    ).fetchall():
        priors.setdefault(pid, {})["upvote"] = float(cnt)
    for pid, cnt in store.db.execute(
        "SELECT post_id, COUNT(*) FROM cm_comments GROUP BY post_id"
    ).fetchall():
        priors.setdefault(pid, {})["reply"] = float(cnt)
    for pid, cnt in store.db.execute(
        "SELECT post_id, COUNT(*) FROM cm_bookmarks GROUP BY post_id"
    ).fetchall():
        priors.setdefault(pid, {})["bookmark"] = float(cnt)
    try:
        for pid, etype, cnt in store.db.execute(
            "SELECT post_id, event_type, COUNT(*) FROM cm_interaction_events WHERE post_id <> '' GROUP BY post_id, event_type"
        ).fetchall():
            d = priors.setdefault(pid, {})
            d[etype] = d.get(etype, 0.0) + float(cnt)
    except Exception:
        pass
    return priors


def _load_bridge_features(request, is_minor: bool) -> list[Any]:
    if request is None or is_minor:
        return []
    try:
        from .memory import bridge_of

        bridge = bridge_of(request)
        principal = getattr(getattr(request, "state", None), "community_principal", None)
        if bridge is None or principal is None:
            return []
        return list(bridge.read_community_interest_features(principal))
    except Exception:
        return []


def _format_why_this(reasons: Sequence[str], *, cold_start: bool = False) -> str:
    if reasons:
        return " · ".join(reasons[:2])
    if cold_start:
        return "Cold start: public post"
    return "Popular public community post"


def _diversify_top_k(candidates: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    """Stage 4: enforce author (<=2) / group (<=3) caps in top 20 and 1-in-5 diversity slot."""
    if not candidates:
        return []
    cap_n = min(limit, 20)
    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    author_counts: dict[str, int] = {}
    group_counts: dict[str, int] = {}
    seen_clusters: set[str] = set()

    def _can_pick(item: dict[str, Any], enforce_caps: bool) -> bool:
        if item["id"] in selected_ids:
            return False
        if not enforce_caps:
            return True
        if len(selected) < cap_n:
            auth = item.get("owner") or ""
            gid = item.get("group_id")
            if auth and author_counts.get(auth, 0) >= 2:
                return False
            if gid and group_counts.get(gid, 0) >= 3:
                return False
        return True

    def _add(item: dict[str, Any]) -> None:
        selected.append(item)
        selected_ids.add(item["id"])
        auth = item.get("owner") or ""
        gid = item.get("group_id")
        if auth:
            author_counts[auth] = author_counts.get(auth, 0) + 1
        if gid:
            group_counts[gid] = group_counts.get(gid, 0) + 1
        tp = item.get("topic_path") or ""
        if tp:
            seen_clusters.add(tp.split("/")[0])

    # Reserve 1-in-5 slot for diverse topic/cluster when available.
    idx = 0
    while len(selected) < limit and idx < len(candidates):
        pos = len(selected) + 1
        picked = None
        if pos % 5 == 0:
            for cand in candidates:
                if not _can_pick(cand, True):
                    continue
                tp = cand.get("topic_path") or ""
                root = tp.split("/")[0] if tp else ""
                if root and root not in seen_clusters:
                    picked = cand
                    cand["diversity_slot"] = True
                    break
        if picked is None:
            for cand in candidates:
                if _can_pick(cand, True):
                    picked = cand
                    break
        if picked is None:
            break
        _add(picked)
        idx += 1

    # Backfill if strict author/group caps left fewer than limit.
    if len(selected) < limit:
        for cand in candidates:
            if len(selected) >= limit:
                break
            if _can_pick(cand, False):
                _add(cand)
    return selected


# ---------------------------------------------------------------- Public API
def rank_discovery(
    request,
    store,
    owner: str,
    limit: int = 20,
    *,
    base_items: list[dict[str, Any]] | None = None,
    context_override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute the 4-stage Two-Tower Recommender and return full discovery payload."""
    setup_recommender(store)
    is_minor = _check_is_minor(request, store, owner)
    ctx_enabled = False if is_minor else is_context_aware_enabled(store, owner)

    raw_ctx = context_override if context_override is not None else (get_ephemeral_context(owner) if ctx_enabled else None)
    if is_minor or not ctx_enabled:
        context_used = None
    else:
        tb, wk = compute_time_bucket()
        if raw_ctx:
            context_used = {
                "area_coarse": normalize_area_coarse(raw_ctx.get("area_coarse")),
                "device_class": str(raw_ctx.get("device_class") or "unknown").lower(),
                "time_bucket": str(raw_ctx.get("time_bucket") or tb),
                "is_weekend": bool(raw_ctx.get("is_weekend") if raw_ctx.get("is_weekend") is not None else wk),
                "user_state": str(raw_ctx.get("user_state") or "unknown").lower(),
            }
        else:
            context_used = {
                "area_coarse": "unknown",
                "device_class": "unknown",
                "time_bucket": tb,
                "is_weekend": wk,
                "user_state": "unknown",
            }
    driving_safe_mode = bool(context_used and context_used.get("user_state") == "driving")

    # Load groups & Stage 2 policy fences.
    groups = store.db.execute(
        "SELECT id,name,handle,description,visibility,owner,provenance,created_at FROM cm_groups"
    ).fetchall()
    groups_by_id = {g[0]: g for g in groups}
    group_names = {g[0]: g[1] for g in groups}
    fences = _load_policy_fences(store, owner)

    # Load all active non-deleted posts.
    post_rows = store.db.execute(
        "SELECT id,owner,group_id,text,revision,pinned,deleted,provenance,created_at,updated_at FROM cm_posts WHERE deleted=0 ORDER BY created_at DESC, id DESC"
    ).fetchall()
    post_by_id = {p[0]: p for p in post_rows}
    meta_map = ensure_post_embeddings(store, post_rows, group_names)

    # Personalization signals (strictly disabled when minor-protected).
    interests: list[str] = []
    profile_area = "unknown"
    follows_set: set[str] = set()
    follow_handles: dict[str, str] = {}
    usage_entries: list[dict[str, Any]] = []
    usage_by_topic: dict[str, list[dict[str, Any]]] = {}
    recent_events: list[dict[str, Any]] = []
    bridge_features: list[Any] = []

    if not is_minor:
        prof = profile_by_owner(store, owner)
        if prof:
            profile_area = normalize_area_coarse(prof[4])
            try:
                interests = [
                    str(i).strip().lower()
                    for i in json.loads(prof[5] or "[]")
                    if str(i).strip() and not is_sensitive_topic(str(i))
                ]
            except Exception:
                interests = []
        for fid, handle in store.db.execute(
            "SELECT f.followee, p.handle FROM cm_follows f LEFT JOIN cm_profiles p ON p.owner=f.followee WHERE f.follower=?",
            (owner,),
        ).fetchall():
            follows_set.add(fid)
            if handle:
                follow_handles[fid] = handle
        bridge_features = _load_bridge_features(request, is_minor=False)
        if ctx_enabled:
            from .context_profile import list_usage_profile

            usage_entries = list_usage_profile(store, owner, include_lowered=False)
            for u in usage_entries:
                if u["active_in_feed"] and not is_sensitive_topic(u["topic_key"]):
                    usage_by_topic.setdefault(u["topic_key"], []).append(u)
            ev_rows = store.db.execute(
                "SELECT topic_key,event_type,value,created_at FROM cm_interaction_events WHERE owner=? ORDER BY created_at DESC LIMIT 50",
                (owner,),
            ).fetchall()
            recent_events = [
                {"topic_key": r[0], "event_type": r[1], "value": float(r[2]), "created_at": r[3]}
                for r in ev_rows
                if not is_sensitive_topic(r[0])
            ]

    user_vec = encode_user_context_vector(
        store,
        owner,
        interests=interests,
        profile_area=profile_area,
        bridge_features=bridge_features,
        usage_entries=usage_entries,
        recent_events=recent_events,
        context=context_used,
        is_minor=is_minor,
        context_enabled=ctx_enabled,
    )
    has_personal_vec = any(abs(x) > 1e-9 for x in user_vec)

    # ---------------- Stage 1: Multi-channel Candidate Generation ----------------
    stage1_scores: dict[str, float] = {}
    channel_tags: dict[str, set[str]] = {}
    pids, mat = _get_post_matrix(store, post_rows, meta_map)

    if has_personal_vec and pids:
        if getattr(store, "_pgvector_ready", False):
            try:
                lit = "[" + ",".join(f"{float(v):.6f}" for v in user_vec) + "]"
                pg_rows = store.db.execute(
                    "SELECT post_id, 1.0 - (vec <=> ?::vector) AS sim FROM cm_post_embeddings WHERE vec IS NOT NULL ORDER BY vec <=> ?::vector LIMIT 120",
                    (lit, lit),
                ).fetchall()
                for pid, sim in pg_rows:
                    stage1_scores[pid] = float(sim)
                    channel_tags.setdefault(pid, set()).add("tower")
            except Exception:
                pass
        if not stage1_scores:
            if np is not None and isinstance(mat, np.ndarray) and len(pids) > 0:
                u_arr = np.asarray(user_vec, dtype=np.float32)
                sims = mat @ u_arr
                k = min(120, len(pids))
                if k == len(pids):
                    top_idx = np.argsort(-sims)
                else:
                    part = np.argpartition(-sims, k - 1)[:k]
                    top_idx = part[np.argsort(-sims[part])]
                for idx in top_idx:
                    pid = pids[int(idx)]
                    stage1_scores[pid] = float(sims[int(idx)])
                    channel_tags.setdefault(pid, set()).add("tower")
            else:
                scored = [
                    (pids[i], sum(float(mat[i][j]) * user_vec[j] for j in range(DIM)))
                    for i in range(len(pids))
                ]
                scored.sort(key=lambda pair: -pair[1])
                for pid, sim in scored[:120]:
                    stage1_scores[pid] = float(sim)
                    channel_tags.setdefault(pid, set()).add("tower")

    # Channel B: Follow-graph recents (top 40).
    if follows_set:
        follow_count = 0
        for p in post_rows:
            if p[1] in follows_set:
                stage1_scores.setdefault(p[0], 0.0)
                channel_tags.setdefault(p[0], set()).add("follow")
                follow_count += 1
                if follow_count >= 40:
                    break

    # Channel C: Public cold-start / trending (top 40).
    priors = _load_engagement_priors(store)
    cold_pool = []
    for p in post_rows:
        pr = priors.get(p[0], {})
        pop = pr.get("upvote", 0.0) + 1.3 * pr.get("reply", 0.0) + 1.5 * pr.get("bookmark", 0.0)
        cold_pool.append((pop, p[8] or "", p[0]))
    cold_pool.sort(key=lambda x: (-x[0], x[1], x[2]), reverse=False)
    for _pop, _ts, pid in cold_pool[:40]:
        stage1_scores.setdefault(pid, 0.0)
        channel_tags.setdefault(pid, set()).add("trending")

    # ---------------- Stage 2 + Stage 3: Policy Filter & Multi-Task + ContextFit ----------------
    weights_cfg = load_trained_weights() or {}
    tw = {**DEFAULT_TASK_WEIGHTS, **(weights_cfg.get("task_weights") or {})}
    scored_items: list[dict[str, Any]] = []

    for pid, tower_sim in stage1_scores.items():
        p = post_by_id.get(pid)
        if not p:
            continue
        if not _post_visible_to_owner(p, owner, groups_by_id, fences):
            continue

        _pid, author, gid, text, _rev, _pinned, _deleted, prov, created_at, updated_at = p
        meta = meta_map.get(pid, {})
        topic_path = meta.get("topic_path") or ""
        post_area = meta.get("area_coarse") or "unknown"
        text_len = int(meta.get("text_len") or len(text or ""))
        hay = (text or "").lower()

        # Multi-task normalized engagement priors.
        pr = priors.get(pid, {})
        p_up = math.log1p(pr.get("upvote", 0.0)) / 3.0
        p_rep = math.log1p(pr.get("reply", 0.0)) / 3.0
        p_save = math.log1p(pr.get("bookmark", 0.0)) / 3.0
        p_rep_share = math.log1p(pr.get("repost", 0.0)) / 3.0
        p_dwell = math.log1p(pr.get("dwell", 0.0)) / 3.0
        p_down = math.log1p(pr.get("downvote", 0.0) + pr.get("hide", 0.0)) / 3.0

        mt_score = (
            tw["upvote"] * p_up
            + tw["reply"] * p_rep
            + tw["bookmark"] * p_save
            + tw["repost"] * p_rep_share
            + tw["dwell"] * p_dwell
            - tw["downvote"] * p_down
        )

        features_used: list[str] = []
        why_reasons: list[str] = []
        context_fit = 0.0
        personal_boost = 0.0
        origin = "cold_start"

        if not is_minor:
            if tower_sim > 0.08:
                features_used.append("tower:semantic")
                origin = "two_tower"

            # Profile interests (non-sensitive only).
            matched_interests = [i for i in interests if i in hay and not is_sensitive_topic(i)]
            if matched_interests:
                personal_boost += 0.25 * min(2, len(matched_interests))
                for mi in matched_interests[:2]:
                    features_used.append(f"interest:{mi}")
                why_reasons.append(f"You picked {matched_interests[0]} when you joined")
                origin = "two_tower"

            # Follow graph.
            if author in follows_set:
                personal_boost += 0.30
                fhandle = follow_handles.get(author) or author
                features_used.append(f"follow:{fhandle}")
                why_reasons.append(f"You follow @{fhandle}")
                origin = "two_tower"

            # Consented MemoryBridge InterestFeature.
            matched_bridge = []
            for bf in bridge_features:
                slug = (getattr(bf, "topic_slug", "") or "").lower()
                label = (getattr(bf, "topic_label", "") or "").lower()
                if is_sensitive_topic(slug) or is_sensitive_topic(label):
                    continue
                if (slug and slug in hay) or (label and label in hay):
                    matched_bridge.append(bf)
            if matched_bridge:
                personal_boost += 0.22
                for bf in matched_bridge:
                    fid = getattr(bf, "feature_id", "")
                    if fid:
                        features_used.append(fid)
                why_reasons.append("From interests you share from Dubai-io, with consent")
                origin = "interest_feature"

            # Active qualified cm_usage_profile (>= 0.10, never lowered/aged-below).
            matched_usage: list[tuple[float, str, bool]] = []
            for tkey, entries in usage_by_topic.items():
                if tkey in hay or (topic_path and tkey in topic_path.lower()):
                    best_w = 0.0
                    ctx_bonus = False
                    for ent in entries:
                        w = float(ent["weight"])
                        if context_used and (
                            ent["time_bucket"] == context_used["time_bucket"]
                            or (
                                context_used["area_coarse"] != "unknown"
                                and ent["area_coarse"] == context_used["area_coarse"]
                            )
                        ):
                            ctx_bonus = True
                        if w > best_w:
                            best_w = w
                    if best_w >= SURFACE_THRESHOLD:
                        matched_usage.append((best_w, tkey, ctx_bonus))
            if matched_usage:
                matched_usage.sort(reverse=True)
                top_w, top_t, has_ctx = matched_usage[0]
                context_fit += 0.35 * top_w + (0.12 * top_w if has_ctx else 0.0)
                features_used.append(f"usage:{top_t}")
                why_reasons.append(f"Matched your #{top_t} activity")
                origin = "two_tower"

            # ContextFit: area + time_bucket + device/user_state format fit.
            if ctx_enabled and context_used:
                c_area = context_used.get("area_coarse", "unknown")
                c_tb = context_used.get("time_bucket", "workday")
                c_state = context_used.get("user_state", "unknown")
                c_dev = context_used.get("device_class", "unknown")
                c_wknd = bool(context_used.get("is_weekend"))
                if c_area != "unknown" and post_area == c_area:
                    area_boost = 0.35 if (c_tb in ("commute_am", "commute_pm", "lunch", "evening") or c_state == "walking" or c_wknd) else 0.25
                    context_fit += area_boost
                    features_used.append(f"area:{c_area}")
                    features_used.append(f"time:{c_tb}")
                    tb_label = c_tb.replace("_", " ").title()
                    why_reasons.insert(0, f"Matched {c_area} · {tb_label}")
                if text_len <= 280 and (c_state in ("walking", "running", "driving") or c_dev in ("mobile_ios", "mobile_android", "mobile_web")):
                    context_fit += 0.22
                    features_used.append(f"state:{c_state}")
                    if not any("Matched" in r for r in why_reasons):
                        why_reasons.append(f"Adapted for {c_state.title()} · {c_dev}")
                elif (text_len > 280 or pr.get("reply", 0.0) >= 3) and (
                    c_state in ("sitting", "stationary") and (c_tb in ("evening", "late_night") or c_wknd or c_dev == "desktop")
                ):
                    context_fit += 0.22
                    features_used.append(f"state:{c_state}")
                    if not any("Matched" in r for r in why_reasons):
                        why_reasons.append("Deep thread for stationary reading")

        # Driving safety mode: collapse & deprioritize long reading posts (>280 chars).
        driving_collapsed = False
        short_summary = None
        safety_notice = None
        driving_penalty = 0.0
        if driving_safe_mode and text_len > 280:
            driving_collapsed = True
            driving_penalty = 2.5
            short_summary = (text or "")[:120].rstrip() + "..."
            safety_notice = "Collapsed while driving — listen or view when parked."
            why_reasons = ["Shortened for driving safety"] + why_reasons

        total_score = (
            tw["tower"] * max(0.0, tower_sim)
            + mt_score
            + tw["context_fit"] * context_fit
            + personal_boost
            - driving_penalty
        )
        cold_item = origin == "cold_start"
        why_this = _format_why_this(why_reasons, cold_start=cold_item)
        scored_items.append({
            "kind": "post",
            "type": "post",
            "id": pid,
            "post_id": pid,
            "owner": author,
            "group_id": gid,
            "text": text,
            "topic_path": topic_path,
            "area_coarse": post_area,
            "score": round(float(total_score), 6),
            "tower_similarity": round(float(tower_sim), 6),
            "context_fit": round(float(context_fit), 6),
            "features_used": list(dict.fromkeys(features_used)),
            "why_this": why_this,
            "why_chip": "Why this?",
            "origin": origin,
            "driving_collapsed": driving_collapsed,
            "collapsed": driving_collapsed,
            "short_summary": short_summary,
            "safety_notice": safety_notice,
            "provenance": prov,
            "as_of": updated_at or created_at,
        })

    # Include optional caller-supplied base_items (deduped by id) if provided.
    if base_items:
        seen_ids = {it["id"] for it in scored_items}
        for bi in base_items:
            bid = bi.get("id")
            if not bid or bid in seen_ids:
                continue
            item = dict(bi)
            item.setdefault("why_chip", "Why this?")
            item.setdefault("features_used", [])
            item.setdefault("score", 0.0)
            scored_items.append(item)
            seen_ids.add(bid)

    scored_items.sort(key=lambda x: (-float(x["score"]), x.get("id", "")))
    final_items = _diversify_top_k(scored_items, limit)

    # Cold-start fallback to public groups if no posts are visible.
    reason = None
    if not final_items:
        pub_groups = [g for g in groups if g[4] == "public" and g[0] not in fences["muted_groups"]]
        for g in pub_groups[:limit]:
            final_items.append({
                "kind": "group",
                "type": "group",
                "id": g[0],
                "group_id": g[0],
                "owner": g[5],
                "name": g[1],
                "handle": g[2],
                "description": g[3],
                "score": 0.0,
                "features_used": [],
                "why_this": "Cold start: public community",
                "why_chip": "Why this?",
                "origin": "cold_start",
                "provenance": g[6],
                "as_of": g[7],
            })
        reason = "Cold start: public communities, not personalised." if final_items else "Cold start: no public posts or communities yet."
    elif is_minor:
        reason = "Adults-only personalisation disabled (fail-closed minor protection)."
    elif all(it.get("origin") == "cold_start" for it in final_items):
        reason = "Cold start: public posts, not personalised."

    all_features = sorted({f for it in final_items for f in (it.get("features_used") or [])})
    if is_minor or not all_features:
        source = "cold_start"
    elif context_used and any(f.startswith(("area:", "usage:", "state:")) for f in all_features):
        source = "two_tower+context"
    else:
        source = "two_tower"

    # Log recommendation events (never store raw lat/lng or minor personal traits).
    stamp = cm.now()
    for it in final_items:
        store.db.execute(
            "INSERT INTO cm_recommendation_events (id,owner,candidate_type,candidate_id,features,why_this,reason,created_at) VALUES (?,?,?,?,?,?,?,?)",
            (uuid4().hex, owner, it.get("kind"), it.get("id"), json.dumps(it.get("features_used") or []), it.get("why_this") or "", reason or "", stamp),
        )
    store.db.commit()

    return {
        "items": final_items,
        "candidates": final_items,
        "reason": reason,
        "empty": len(final_items) == 0,
        "features_used": all_features,
        "source": source,
        "why_chip": "Why this?",
        "context_used": context_used,
        "driving_safe_mode": driving_safe_mode,
        "is_minor_protected": is_minor,
    }


def recall_lowered_and_boost(store, owner: str, query_text: str) -> dict[str, Any]:
    """D19b explicit query recall: 100% callable even for lowered (0.01) or aged (0.05) topics.

    Boosts matching usage profile weights back >= 0.35 and returns matching visible posts + recalled entries.
    """
    setup_recommender(store)
    clean_q = (query_text or "").strip()
    if not clean_q:
        return {"query": clean_q, "recalled": [], "boosted_topics": [], "items": [], "count": 0}

    q_norm = clean_q.lower().lstrip("#")
    recalled_entries = recall_usage_topic(store, owner, q_norm)

    # Also match individual tokens if multi-word query.
    if not recalled_entries:
        seen_keys: set[tuple[str, str, str, str]] = set()
        for tok in _TOKEN_RE.findall(q_norm):
            clean_tok = tok.lstrip("#")
            for entry in recall_usage_topic(store, owner, clean_tok):
                k = (entry["topic_key"], entry["time_bucket"], entry["area_coarse"], entry["format_bucket"])
                if k not in seen_keys:
                    seen_keys.add(k)
                    recalled_entries.append(entry)

    boosted_topics = sorted({e["topic_key"] for e in recalled_entries})

    # Find matching visible posts respecting Stage 2 fences.
    groups = store.db.execute(
        "SELECT id,name,handle,description,visibility,owner,provenance,created_at FROM cm_groups"
    ).fetchall()
    groups_by_id = {g[0]: g for g in groups}
    fences = _load_policy_fences(store, owner)
    post_rows = store.db.execute(
        "SELECT id,owner,group_id,text,revision,pinned,deleted,provenance,created_at,updated_at FROM cm_posts WHERE deleted=0 ORDER BY created_at DESC"
    ).fetchall()

    needles = {q_norm} | {t.lower() for t in boosted_topics} | {t.lstrip("#") for t in _TOKEN_RE.findall(q_norm)}
    matched_posts: list[dict[str, Any]] = []
    for p in post_rows:
        if not _post_visible_to_owner(p, owner, groups_by_id, fences, allow_own=True):
            continue
        hay = (p[3] or "").lower()
        hits = [n for n in needles if n and n in hay]
        if hits:
            matched_posts.append({
                "kind": "post",
                "type": "post",
                "id": p[0],
                "post_id": p[0],
                "owner": p[1],
                "group_id": p[2],
                "text": p[3],
                "matched_topics": hits,
                "why_this": f"Explicitly recalled: {clean_q}",
                "why_chip": "Why this?",
                "as_of": p[9] or p[8],
            })

    return {
        "query": clean_q,
        "recalled": recalled_entries,
        "recalled_profiles": recalled_entries,
        "boosted_topics": boosted_topics,
        "items": matched_posts,
        "count": len(recalled_entries),
    }
