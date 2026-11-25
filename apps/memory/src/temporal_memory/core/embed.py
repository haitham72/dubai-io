"""Local multilingual semantic embeddings (BAAI/bge-m3 1024-d ONNX int8) and batch backfill (U4)."""
from __future__ import annotations

from collections import OrderedDict
import logging
import os
import re
import threading
import time
from typing import Any, Sequence

from temporal_memory.config import get_settings
from temporal_memory.db.db import Database

log = logging.getLogger(__name__)

EMBED_MODEL = "BAAI/bge-m3"
EMBED_DIM = 1024
_ONNX_REPO = "Xenova/bge-m3"
_ONNX_FILE = "onnx/model_int8.onnx"
_TOKENIZER_REPO = "BAAI/bge-m3"
_TOKENIZER_FILE = "onnx/tokenizer.json"
_QUERY_CACHE_MAX = 2048

_LOAD_LOCK = threading.Lock()
_CACHE_LOCK = threading.Lock()
_LOADED_MODEL_NAME: str | None = None
_SESSION: Any = None
_TOKENIZER: Any = None
_INPUT_NAMES: tuple[str, ...] = ()
_QUERY_CACHE: OrderedDict[tuple[str, str], list[float]] = OrderedDict()
# E11b: a failed model load/download is cached for a backoff window so offline
# callers fail fast instead of retrying a ~570 MB download on every call.
_LOAD_RETRY_AT = 0.0
_LOAD_BACKOFF_S_DEFAULT = 60.0

_ARABIZI_DIGIT_WORD_RE = re.compile(r"\b(?:[a-zA-Z]+[2356789][a-zA-Z0-9]*|[2356789][a-zA-Z]+[a-zA-Z0-9]*)\b")
_ARABIZI_PARTICLES = frozenset({
    "el", "al", "fe", "fi", "min", "men", "emta", "fein", "fen", "bekam", "kam",
    "elli", "elly", "menen", "mnin", "kan", "eyh", "eih", "eh", "w", "enta", "enti",
    "ana", "mesh", "mish", "howa", "heya", "delwa2ty", "delwati", "ezay", "leh",
})
_PARTICLE_AR = {
    "el": "ال", "al": "ال", "fe": "في", "fi": "في", "min": "من", "men": "من",
    "emta": "امتى", "fein": "فين", "fen": "فين", "bekam": "بكام", "kam": "كم",
    "elli": "اللي", "elly": "اللي", "menen": "منين", "mnin": "منين", "kan": "كان",
    "eyh": "ايه", "eih": "ايه", "eh": "ايه", "w": "و", "enta": "انت", "enti": "انتي",
    "ana": "انا", "mesh": "مش", "mish": "مش", "howa": "هو", "heya": "هي",
    "delwa2ty": "دلوقتي", "delwati": "دلوقتي", "ezay": "ازاي", "leh": "ليه",
    "3ala": "على", "ba3d": "بعد", "3an": "عن", "ma3a": "مع",
}
_ARABIZI_DIGRAPHS: tuple[tuple[str, str], ...] = (
    ("3'", "غ"), ("7'", "خ"), ("sh", "ش"), ("ch", "ش"), ("kh", "خ"), ("gh", "غ"),
    ("th", "ث"), ("dh", "ذ"), ("ph", "ف"), ("ee", "ي"), ("oo", "و"), ("ou", "و"),
    ("ei", "ي"), ("ai", "ي"), ("aa", "ا"),
)
_ARABIZI_CHARS = {
    "2": "ء", "3": "ع", "5": "خ", "6": "ط", "7": "ح", "8": "ق", "9": "ص",
    "b": "ب", "t": "ت", "g": "ج", "j": "ج", "d": "د", "r": "ر", "z": "ز",
    "s": "س", "f": "ف", "q": "ق", "k": "ك", "l": "ل", "m": "م", "n": "ن",
    "h": "ه", "w": "و", "y": "ي", "i": "ي", "o": "و", "u": "و",
}


def _looks_like_arabizi(text: str) -> bool:
    if _ARABIZI_DIGIT_WORD_RE.search(text):
        return True
    words = re.findall(r"[0-9a-zA-Z']+", text.lower())
    return sum(1 for w in words if w in _ARABIZI_PARTICLES) >= 2


def _transliterate_arabizi_token(tok: str) -> str:
    low = tok.lower()
    if low in _PARTICLE_AR:
        return _PARTICLE_AR[low]
    out: list[str] = []
    i = 0
    n = len(low)
    while i < n:
        matched = False
        for dg, ar in _ARABIZI_DIGRAPHS:
            if low.startswith(dg, i):
                out.append(ar)
                i += len(dg)
                matched = True
                break
        if matched:
            continue
        ch = low[i]
        if ch in ("a", "e") and i == 0:
            out.append("ا")
        elif ch in ("a", "e"):
            # Short medial a/e is omitted in unvocalized Arabic consonantal spelling; trailing e -> ي.
            if ch == "e" and i == n - 1:
                out.append("ي")
        elif ch in _ARABIZI_CHARS:
            out.append(_ARABIZI_CHARS[ch])
        else:
            out.append(ch)
        i += 1
    return "".join(out)


def _normalize_query_text(text: str) -> str:
    clean = " ".join((text or "").split())
    if not clean:
        return clean
    if os.environ.get("TM_ARABIZI_TRANSLIT", "1").strip() == "0":
        return clean
    if not _looks_like_arabizi(clean):
        return clean
    tokens = re.findall(r"[0-9a-zA-Z']+", clean)
    ar_tokens: list[str] = []
    attach_al = False
    for t in tokens:
        if not t:
            continue
        low = t.lower()
        if low in ("el", "al"):
            attach_al = True
            continue
        ar = _transliterate_arabizi_token(t)
        if attach_al:
            ar = "ال" + ar
            attach_al = False
        ar_tokens.append(ar)
    if attach_al:
        ar_tokens.append("ال")
    ar_phrase = " ".join(ar_tokens)
    return f"{ar_phrase} / {clean}" if ar_phrase else clean


def _download_asset(repo_id: str, filename: str) -> str:
    from huggingface_hub import hf_hub_download

    try:
        return hf_hub_download(repo_id=repo_id, filename=filename, local_files_only=True)
    except Exception:
        return hf_hub_download(repo_id=repo_id, filename=filename)


def _load_backoff_s() -> float:
    try:
        return max(0.0, float(os.environ.get("TM_EMBED_LOAD_BACKOFF_S", _LOAD_BACKOFF_S_DEFAULT)))
    except ValueError:
        return _LOAD_BACKOFF_S_DEFAULT


def _ensure_loaded(model_name: str | None = None) -> tuple[Any, Any, tuple[str, ...]]:
    global _LOADED_MODEL_NAME, _SESSION, _TOKENIZER, _INPUT_NAMES, _LOAD_RETRY_AT

    target = model_name or get_settings().semantic_model or EMBED_MODEL
    if _SESSION is not None and _LOADED_MODEL_NAME == target:
        return _SESSION, _TOKENIZER, _INPUT_NAMES

    with _LOAD_LOCK:
        if _SESSION is not None and _LOADED_MODEL_NAME == target:
            return _SESSION, _TOKENIZER, _INPUT_NAMES
        if time.monotonic() < _LOAD_RETRY_AT:
            raise RuntimeError("embedder model load skipped: previous failure still in backoff")

        try:
            import onnxruntime as ort
            from tokenizers import Tokenizer

            if target == EMBED_MODEL:
                tok_repo, onnx_repo, onnx_file = _TOKENIZER_REPO, _ONNX_REPO, _ONNX_FILE
            else:
                tok_repo, onnx_repo, onnx_file = target, target, "onnx/model.onnx"

            tok_path = _download_asset(tok_repo, _TOKENIZER_FILE)
            model_path = _download_asset(onnx_repo, onnx_file)

            tok = Tokenizer.from_file(tok_path)
            pad_id = tok.token_to_id("<pad>")
            if pad_id is None:
                pad_id = tok.token_to_id("[PAD]") or 0
            pad_tok = tok.id_to_token(pad_id) or "<pad>"
            tok.enable_truncation(max_length=512)
            tok.enable_padding(pad_id=pad_id, pad_token=pad_tok)

            so = ort.SessionOptions()
            so.intra_op_num_threads = max(1, min(6, os.cpu_count() or 4))
            so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            sess = ort.InferenceSession(model_path, sess_options=so, providers=["CPUExecutionProvider"])
            input_names = tuple(i.name for i in sess.get_inputs())
        except Exception:
            _LOAD_RETRY_AT = time.monotonic() + _load_backoff_s()
            raise

        _LOAD_RETRY_AT = 0.0
        _LOADED_MODEL_NAME = target
        _SESSION = sess
        _TOKENIZER = tok
        _INPUT_NAMES = input_names
        return _SESSION, _TOKENIZER, _INPUT_NAMES


def is_loaded(model_name: str | None = None) -> bool:
    """True when the embedder is already loaded in this process. Never triggers a load or download."""
    target = model_name or get_settings().semantic_model or EMBED_MODEL
    return _SESSION is not None and _LOADED_MODEL_NAME == target


def load_model(model_name: str | None = None) -> None:
    """Explicitly load (and download on first run) the embedder. For warmup, workers and scripts only."""
    _ensure_loaded(model_name)


def clear_query_cache() -> None:
    """Clear the bounded query embedding LRU cache (used in benchmarks/tests)."""
    with _CACHE_LOCK:
        _QUERY_CACHE.clear()


def _encode_batch(texts: Sequence[str], *, model_name: str | None = None) -> list[list[float]]:
    if not texts:
        return []
    import numpy as np

    target = model_name or get_settings().semantic_model or EMBED_MODEL
    sess, tok, input_names = _ensure_loaded(target)
    use_e5 = "e5" in target.lower()
    encoded = tok.encode_batch(list(texts))
    ids = np.asarray([e.ids for e in encoded], dtype=np.int64)
    mask = np.asarray([e.attention_mask for e in encoded], dtype=np.int64)
    feed: dict[str, Any] = {"input_ids": ids, "attention_mask": mask}
    if "token_type_ids" in input_names:
        feed["token_type_ids"] = np.zeros_like(ids)

    token_emb = sess.run(None, feed)[0]
    if use_e5:
        mask_f = mask[:, :, None].astype(np.float32)
        pooled = (token_emb * mask_f).sum(axis=1) / np.clip(mask_f.sum(axis=1), 1e-9, None)
    else:
        # BGE-M3 dense embedding uses normalized CLS token representation.
        pooled = token_emb[:, 0, :]
    norms = np.clip(np.linalg.norm(pooled, axis=1, keepdims=True), 1e-12, None)
    normed = (pooled / norms).astype(np.float32)
    return [row.tolist() for row in normed]


def embed_query(text: str, *, model_name: str | None = None) -> list[float]:
    """Embed one search query with Arabizi phonetic expansion (if detected) and LRU cache.

    Never loads or downloads the model: callers on a request path must run after the
    E9d admin warmup. Raises RuntimeError when the embedder is not loaded yet.
    """
    target = model_name or get_settings().semantic_model or EMBED_MODEL
    if not is_loaded(target):
        raise RuntimeError("semantic embedder is not loaded; run the admin warmup first")
    clean = _normalize_query_text(text)
    key = (target, clean, os.environ.get("TM_ARABIZI_TRANSLIT", "1"))
    with _CACHE_LOCK:
        cached = _QUERY_CACHE.get(key)  # type: ignore[arg-type]
        if cached is not None:
            _QUERY_CACHE.move_to_end(key)  # type: ignore[arg-type]
            return cached

    prompted = f"query: {clean}" if "e5" in target.lower() else clean
    vec = _encode_batch([prompted], model_name=target)[0]
    with _CACHE_LOCK:
        _QUERY_CACHE[key] = vec  # type: ignore[assignment]
        _QUERY_CACHE.move_to_end(key)  # type: ignore[arg-type]
        while len(_QUERY_CACHE) > _QUERY_CACHE_MAX:
            _QUERY_CACHE.popitem(last=False)
    return vec


def embed_passages(
    texts: Sequence[str], *, batch_size: int = 64, model_name: str | None = None
) -> list[list[float]]:
    """Embed passages in batches with L2 normalization."""
    if not texts:
        return []
    target = model_name or get_settings().semantic_model or EMBED_MODEL
    use_e5 = "e5" in target.lower()
    out: list[list[float]] = []
    step = max(1, int(batch_size))
    for i in range(0, len(texts), step):
        chunk = [
            f"passage: {t.strip()}" if use_e5 else t.strip()
            for t in texts[i : i + step]
        ]
        out.extend(_encode_batch(chunk, model_name=target))
    return out


def format_fact_text(text: str, text_orig: str | None) -> str:
    """Combine English fact text with optional original-language span for multilingual embedding."""
    base = (text or "").strip()
    orig = (text_orig or "").strip()
    if orig and orig.casefold() != base.casefold():
        return f"{base}\n{orig}" if base else orig
    return base


def vector_literal(vec: Sequence[float]) -> str:
    """Serialize a float vector to pgvector text literal `[v1,v2,...]`."""
    return "[" + ",".join(f"{float(v):.5f}" for v in vec) + "]"


def is_available() -> bool:
    """Return True if local embedding dependencies load cleanly."""
    try:
        _ensure_loaded()
        return True
    except Exception as exc:
        log.debug("Semantic embedder unavailable: %s", exc)
        return False


def _select_pending(
    db: Database,
    *,
    owner: str | None,
    model_name: str,
    limit: int | None,
    only_ids: Sequence[str] | None = None,
) -> list[dict[str, Any]]:
    """Visible, non-quarantined, non-held-back facts still missing the current model vector."""
    owner_clause = "AND f.owner = %s" if owner is not None else ""
    id_clause = "AND f.id = ANY(%s)" if only_ids is not None else ""
    lim_clause = "LIMIT %s" if limit is not None else ""
    params: list[Any] = []
    if owner is not None:
        params.append(owner)
    if only_ids is not None:
        params.append(list(only_ids))
    params.append(model_name)
    if limit is not None:
        params.append(max(1, int(limit)))

    with db.connection() as conn:
        return conn.execute(
            f"""
            SELECT f.owner, f.id, f.text, f.text_orig
            FROM facts f
            LEFT JOIN subjects s ON s.owner = f.owner AND s.id = f.subject_id
            WHERE f.erased_at IS NULL
              AND f.status <> 'history'
              {owner_clause}
              {id_clause}
              AND (f.embedding IS NULL OR f.embedding_model IS DISTINCT FROM %s)
              AND (
                  s.id IS NULL
                  OR (s.sensitive_cat IS NULL AND split_part(s.path, '/', 1) NOT IN ('health', 'faith'))
                  OR f.provenance IN ('user_supplied', 'provider_confirmed')
              )
              AND NOT EXISTS (
                  SELECT 1
                  FROM fact_evidence fe
                  JOIN records r ON r.id = fe.record_id AND r.owner = fe.owner
                  WHERE fe.owner = f.owner AND fe.fact_id = f.id
                    AND (r.erased_at IS NOT NULL OR r.generation > fe.record_generation)
              )
              AND NOT EXISTS (
                  SELECT 1
                  FROM fact_evidence fe
                  JOIN quarantine q ON q.owner = fe.owner AND q.status = 'held'
                  WHERE fe.owner = f.owner AND fe.fact_id = f.id
                    AND q.record_ids ? fe.record_id
              )
              AND NOT EXISTS (
                  SELECT 1
                  FROM forget_rules fr
                  WHERE fr.owner = f.owner
                    AND (
                        (fr.kind = 'item' AND fr.value = f.id)
                        OR (fr.kind = 'text' AND position(lower(fr.value) IN lower(f.text)) > 0)
                    )
              )
            ORDER BY f.owner, f.valid_from DESC, f.id
            {lim_clause}
            """,
            tuple(params),
        ).fetchall()


def _embed_rows(
    db: Database,
    rows: list[dict[str, Any]],
    *,
    batch_size: int,
    model_name: str,
    time_budget_s: float | None,
) -> dict[str, int]:
    """Embed `rows` in batches, stopping between batches once `time_budget_s` is spent.

    Always finishes the in-flight batch, so each call makes progress. Returns
    embedded/batches plus `consumed` (rows attempted — a prefix of `rows`).
    """
    embedded = 0
    batches = 0
    consumed = 0
    step = max(1, int(batch_size))
    t0 = time.monotonic()
    for i in range(0, len(rows), step):
        chunk = rows[i : i + step]
        texts = [format_fact_text(r["text"], r["text_orig"]) for r in chunk]
        vecs = embed_passages(texts, batch_size=step, model_name=model_name)
        updates = [
            (vector_literal(vec), model_name, r["owner"], r["id"])
            for r, vec in zip(chunk, vecs)
        ]
        with db.transaction() as conn:
            with conn.cursor() as cur:
                cur.executemany(
                    """
                    UPDATE facts
                    SET embedding = %s::public.vector,
                        embedding_model = %s,
                        embedded_at = now()
                    WHERE owner = %s AND id = %s AND erased_at IS NULL AND status <> 'history'
                    """,
                    updates,
                )
        embedded += len(updates)
        batches += 1
        consumed += len(chunk)
        if time_budget_s is not None and time.monotonic() - t0 >= time_budget_s:
            break

    return {"embedded": embedded, "batches": batches, "consumed": consumed}


def embed_pending_facts(
    db: Database,
    *,
    owner: str | None = None,
    batch_size: int = 64,
    limit: int | None = None,
    model_name: str | None = None,
    time_budget_s: float | None = None,
) -> dict[str, int]:
    """Backfill embeddings for visible, non-quarantined, non-held-back facts missing the current model vector.

    With `time_budget_s`, stops between batches once the budget is spent (always finishes the
    in-flight batch, so each call makes progress). Returns embedded/batches plus `fetched`
    (pending rows selected, capped by `limit`) and `remaining` (fetched rows left unembedded);
    callers that passed `limit` must treat a full page as "possibly more pending".
    """
    target = model_name or get_settings().semantic_model or EMBED_MODEL
    rows = _select_pending(db, owner=owner, model_name=target, limit=limit)
    if not rows:
        return {"embedded": 0, "batches": 0, "fetched": 0, "remaining": 0}

    stats = _embed_rows(
        db, rows, batch_size=batch_size, model_name=target, time_budget_s=time_budget_s
    )
    return {
        "embedded": stats["embedded"],
        "batches": stats["batches"],
        "fetched": len(rows),
        "remaining": len(rows) - stats["consumed"],
    }


_BACKFILLED_AT: dict[str, int] = {}
_LAST_SWEEP_AT: dict[str, float] = {}
# Per-owner queue of pending rows fetched by _select_pending. The pending scan is
# expensive at scale (several NOT EXISTS + an ORDER BY over all live facts), so it
# runs once per fetch_limit rows instead of once per sweep; each sweep then only
# pays for the embed batches inside its time budget.
_PENDING: dict[str, dict[str, Any]] = {}
_LAZY_BATCH_SIZE = 8
_LAZY_FETCH_FACTOR = 16
_LAZY_INTERVAL_S_DEFAULT = 5.0


def _lazy_budget_s() -> float:
    try:
        return max(0.0, float(os.environ.get("TM_SEMANTIC_LAZY_BUDGET_S", "0.04")))
    except ValueError:
        return 0.04


def _lazy_interval_s() -> float:
    try:
        return max(0.0, float(os.environ.get("TM_SEMANTIC_LAZY_INTERVAL_S", _LAZY_INTERVAL_S_DEFAULT)))
    except ValueError:
        return _LAZY_INTERVAL_S_DEFAULT


def status() -> dict[str, Any]:
    """Cheap health signal (no model load): is semantic recall configured, installed and loaded in this process."""
    import importlib.util

    cfg = get_settings()
    deps = all(importlib.util.find_spec(m) is not None for m in ("onnxruntime", "tokenizers", "huggingface_hub", "numpy"))
    return {"enabled": bool(cfg.semantic_enabled), "deps_installed": deps, "loaded": _SESSION is not None,
            "model": cfg.semantic_model}


def ensure_embeddings(
    db: Database,
    owner: str,
    *,
    batch_size: int = _LAZY_BATCH_SIZE,
    once_per_version: bool = True,
    time_budget_s: float | None = None,
) -> str | None:
    """Best-effort lazy backfill of embeddings for `owner`'s visible facts (E11b).

    Runs on the query path, so it never loads or downloads the model: until the E9d
    admin warmup has loaded the embedder it returns "embedder_unavailable". Each call
    embeds within a small time budget (TM_SEMANTIC_LAZY_BUDGET_S, default 0.04 s) instead of a
    fixed slice of the newest facts, sweeps are paced to one per TM_SEMANTIC_LAZY_INTERVAL_S
    (default 5 s) per owner, and the owner's facts_version is marked done only
    when a sweep finds nothing left — older facts keep embedding on later queries until
    the backlog is clear. Never raises; returns None when fine, else "disabled" /
    "embedder_unavailable".
    """
    cfg = get_settings()
    if not cfg.semantic_enabled:
        return "disabled"
    try:
        # facts_version is read on every call (cheap PK lookup): it both gates the
        # once-per-version fast path and invalidates the queued _PENDING rows when
        # facts changed since they were selected.
        with db.connection() as conn:
            row = conn.execute("SELECT facts_version FROM owners WHERE id = %s", (owner,)).fetchone()
        ver = int(row["facts_version"]) if row else 0
        if once_per_version and _BACKFILLED_AT.get(owner) == ver:
            return None
        if not is_loaded(cfg.semantic_model or EMBED_MODEL):
            return "embedder_unavailable"
        # Sweeps are paced per owner: even a budgeted sweep costs tens of ms on the
        # query path, so at most one runs per TM_SEMANTIC_LAZY_INTERVAL_S (default 5 s).
        interval = _lazy_interval_s()
        now = time.monotonic()
        if interval > 0 and now - _LAST_SWEEP_AT.get(owner, float("-inf")) < interval:
            return None
        _LAST_SWEEP_AT[owner] = now
        budget = _lazy_budget_s() if time_budget_s is None else time_budget_s
        step = max(1, int(batch_size))
        fetch_limit = step * _LAZY_FETCH_FACTOR
        target = cfg.semantic_model or EMBED_MODEL
        state = _PENDING.get(owner)
        if state is not None and state.get("ver") != ver:
            # Facts changed since the queue was fetched: drop it and rescan so
            # newly pending facts are picked up and stale rows are not embedded.
            _PENDING.pop(owner, None)
            state = None
        if state is None or not state["rows"]:
            rows = _select_pending(db, owner=owner, model_name=target, limit=fetch_limit)
            state = {"rows": rows, "eof": len(rows) < fetch_limit, "ver": ver}
            _PENDING[owner] = state
        # Queued rows may have been quarantined, erased or forgotten since the
        # scan; re-verify eligibility (id-scoped, cheap) before embedding them.
        state["rows"] = _select_pending(
            db, owner=owner, model_name=target, limit=None,
            only_ids=[r["id"] for r in state["rows"]],
        )
        stats = _embed_rows(
            db,
            state["rows"],
            batch_size=step,
            model_name=target,
            time_budget_s=budget,
        )
        del state["rows"][: stats["consumed"]]
        done = not state["rows"] and state["eof"]
        if done:
            _PENDING.pop(owner, None)
        if once_per_version and done:
            _BACKFILLED_AT[owner] = ver
        return None
    except Exception as exc:  # embedding must never break extraction or retrieval
        log.warning("ensure_embeddings failed: %s", exc)
        return "embedder_unavailable"
