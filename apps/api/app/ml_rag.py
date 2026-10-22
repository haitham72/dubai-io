"""Hybrid search over comments: semantic cosine + keyword overlap, RRF fusion.

The semantic leg needs stored embeddings (written by the index path) and an
available embedding backend; otherwise search degrades to keyword-only and
says so. Results carry scores, method and provenance.
"""
import hashlib
import json
import re
import time

from .config import settings

CORPUS_LIMIT = 2000
CACHE_TTL_S = 60
_mem_cache = {}


def tokenize(text):
    return re.findall(r"(?u)\w{3,}", (text or "").lower())


def rrf(rank, k=60):
    return 1.0 / (k + rank)


def _redis_client():
    try:
        import redis
    except ImportError:
        return None
    try:
        return redis.Redis.from_url(settings.redis_url, socket_connect_timeout=1, socket_timeout=1)
    except Exception:
        return None


def cache_get(key):
    client = _redis_client()
    if client is not None:
        try:
            raw = client.get(key)
            if raw:
                return json.loads(raw)
        except Exception:
            pass
    hit = _mem_cache.get(key)
    if hit and hit[0] > time.time():
        return hit[1]
    return None


def cache_set(key, value, ttl=CACHE_TTL_S):
    client = _redis_client()
    if client is not None:
        try:
            client.set(key, json.dumps(value), ex=ttl)
        except Exception:
            pass
    if len(_mem_cache) > 256:
        _mem_cache.clear()
    _mem_cache[key] = (time.time() + ttl, value)


def _keyword_ranked(rows, qtokens):
    scored = []
    for row in rows:
        overlap = len(set(tokenize(row["text"])) & set(qtokens))
        if overlap:
            scored.append((overlap / len(qtokens), row))
    return [row for _, row in sorted(scored, key=lambda pair: -pair[0])]


def _semantic_ranked(rows, qvec):
    from .ml_models import cosine
    scored = []
    for row in rows:
        if row.get("vec") and qvec:
            scored.append((cosine(qvec, row["vec"]), row))
    return [row for _, row in sorted(scored, key=lambda pair: -pair[0])]


def search(store, owner, query, limit=10):
    from . import ml_models
    qtokens = tokenize(query)
    if not qtokens:
        return {"results": [], "method": "none", "semantic": False, "reason": "empty query"}
    cache_key = "ml:search:" + hashlib.sha256(f"{owner}|{query}|{limit}".encode()).hexdigest()
    cached = cache_get(cache_key)
    if cached is not None:
        return cached
    rows = [{
        "id": r[0], "post_id": r[1], "author": r[2], "text": r[3], "created_at": r[4],
        "provenance": r[5], "vec": json.loads(r[6]) if r[6] else None,
    } for r in store.db.execute(
        """SELECT m.id,m.post_id,m.author,m.text,m.created_at,m.provenance,e.vec FROM comments m
           LEFT JOIN comment_embeddings e ON e.comment_id=m.id
           WHERE (m.owner IS NULL OR m.owner=?) ORDER BY m.created_at DESC LIMIT ?""",
        (owner, CORPUS_LIMIT)).fetchall()]
    keyword_order = _keyword_ranked(rows, qtokens)
    qvec = None
    if ml_models.backend().available:
        qvec = (ml_models.backend().embed([query]) or [None])[0]
    semantic_order = _semantic_ranked(rows, qvec) if qvec else []
    fused, seen = {}, set()
    for rank, row in enumerate(keyword_order, 1):
        fused[row["id"]] = fused.get(row["id"], 0.0) + rrf(rank)
    for rank, row in enumerate(semantic_order, 1):
        fused[row["id"]] = fused.get(row["id"], 0.0) + rrf(rank)
    by_id = {row["id"]: row for row in rows}
    results = [{
        "id": cid, "post_id": by_id[cid]["post_id"], "author": by_id[cid]["author"],
        "text": by_id[cid]["text"][:400], "created_at": by_id[cid]["created_at"],
        "provenance": by_id[cid]["provenance"], "score": round(score, 6),
    } for cid, score in sorted(fused.items(), key=lambda pair: -pair[1])[:limit]]
    payload = {"results": results, "method": "hybrid" if qvec else "keyword",
               "semantic": bool(qvec), "count": len(results)}
    cache_set(cache_key, payload)
    return payload
