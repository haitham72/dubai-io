"""Offline Two-Tower Recommender Trainer (E14b).

Consumes consented organic `cm_interaction_events` joined with D19 lowered
weights in `cm_usage_profile`, optimizes dual-encoder projections (`W_user`,
`W_item`) via PyTorch InfoNCE + BPR (or NumPy InfoNCE + BPR fallback when
`torch` is not installed), fits multi-task ranker weights, evaluates
`Recall@20` and `NDCG@10`, and writes `cm_recommender_weights.json`.

Usage:
    python scripts/train_community_two_tower.py --synthetic-smoke
    python scripts/train_community_two_tower.py --db apps/api/data/community.sqlite3
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
import sys
import tempfile
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for extra in (
    ROOT / "apps" / "api",
    ROOT / "apps" / "memory" / "src",
    ROOT / "packages" / "contest-shared",
):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

from app.actions import ActionStore  # noqa: E402
from app.community import store as cm  # noqa: E402
from app.community.context_profile import (  # noqa: E402
    is_sensitive_topic,
    lower_usage_topic,
    record_interaction_event,
    setup_context_profile,
)
from app.community.moderation import owner_is_minor  # noqa: E402
from app.community.recommender import (  # noqa: E402
    DEFAULT_TASK_WEIGHTS,
    DIM,
    encode_item_vector,
    encode_text_topic_vector,
    setup_recommender,
)

def _safe_import_torch():
    """Import torch only when a subprocess probe succeeds.

    Broken Anaconda/Windows torch builds can abort the process on import, which
    cannot be caught with try/except in-process. Probe first, then import.
    """
    import os
    import subprocess

    if os.environ.get("CM_FORCE_NUMPY_TRAINER", "").strip().lower() in ("1", "true", "yes"):
        return None
    try:
        probe = subprocess.run(
            [sys.executable, "-c", "import torch; torch.zeros(1)"],
            capture_output=True,
            timeout=45,
            check=False,
        )
        if probe.returncode != 0:
            return None
        import torch as _torch  # noqa: WPS433

        return _torch
    except Exception:  # pragma: no cover - numpy fallback when torch is unavailable
        return None


torch = _safe_import_torch()

EVENT_SIGNAL_WEIGHTS: dict[str, float] = {
    "bookmark": 1.5,
    "reply": 1.3,
    "repost": 1.2,
    "upvote": 1.0,
    "dwell": 0.6,
    "downvote": -0.8,
    "hide": -1.2,
    "lower": -1.5,
}

# Google Limited Use: never train on Gmail / Calendar / YouTube / Takeout / generic Google rows.
_GOOGLE_LIMITED_USE_MARKERS: frozenset[str] = frozenset(
    {"gmail", "calendar", "youtube", "takeout", "google"}
)


def _is_google_limited_use_text(*parts: str | None) -> bool:
    blob = " ".join(str(p or "").lower() for p in parts)
    if not blob.strip():
        return False
    for marker in _GOOGLE_LIMITED_USE_MARKERS:
        if marker in blob:
            return True
    return False


def _populate_synthetic_db(store: ActionStore) -> None:
    setup_recommender(store)
    rng = np.random.default_rng(42)
    topics = [
        ("padel", "Dubai Marina", "Looking for doubles #padel partners in Dubai Marina tonight"),
        ("coffee", "DIFC", "Best specialty #coffee espresso bar in DIFC Gate Village"),
        ("startup", "Internet City", "AI founder #startup demo night at Dubai Internet City"),
        ("running", "JLT", "Early morning #running club around JLT lakes"),
        ("food", "Downtown Dubai", "Late lunch #food spots near Downtown Dubai boulevard"),
        ("cars", "Al Quoz", "Classic #cars detailing and weekend drive from Al Quoz"),
    ]
    now_dt = datetime.now(timezone.utc)
    stamp = now_dt.isoformat(timespec="seconds")

    # Create 12 synthetic adult users and 60 posts across the 6 topic clusters.
    for u_idx in range(12):
        owner = f"synth_user_{u_idx}"
        pref_idx = u_idx % len(topics)
        pref_topic, pref_area, _ = topics[pref_idx]
        store.db.execute(
            "INSERT OR IGNORE INTO cm_profiles (owner,handle,display_name,bio,area,interests,age_band,privacy,provenance,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (owner, owner, f"User {u_idx}", "", pref_area, json.dumps([pref_topic]), "18+", "public", "demo_fixture", stamp, stamp),
        )

    post_ids_by_topic: dict[str, list[str]] = {t[0]: [] for t in topics}
    for p_idx in range(60):
        t_idx = p_idx % len(topics)
        topic, area, template = topics[t_idx]
        pid = f"synth_post_{p_idx:03d}"
        author = f"synth_author_{p_idx % 8}"
        text = f"{template} — session #{p_idx} in {area}"
        store.db.execute(
            "INSERT OR IGNORE INTO cm_posts (id,owner,group_id,text,revision,pinned,deleted,provenance,created_at,updated_at) VALUES (?,?,?,?,1,0,0,'demo_fixture',?,?)",
            (pid, author, None, text, stamp, stamp),
        )
        post_ids_by_topic[topic].append(pid)

    # Organic interaction events + D19 lower signals.
    for u_idx in range(12):
        owner = f"synth_user_{u_idx}"
        pref_idx = u_idx % len(topics)
        pref_topic, pref_area, _ = topics[pref_idx]
        neg_topic, _, _ = topics[(pref_idx + 1) % len(topics)]
        pos_pids = post_ids_by_topic[pref_topic]
        neg_pids = post_ids_by_topic[neg_topic]
        for j, pid in enumerate(pos_pids[:6]):
            etype = ("upvote", "bookmark", "reply", "repost", "dwell", "upvote")[j % 6]
            record_interaction_event(
                store,
                owner,
                post_id=pid,
                topic_key=pref_topic,
                event_type=etype,
                value=1.0 if etype != "dwell" else 20.0,
                area_coarse=pref_area,
                session_id=f"sess_{u_idx}_{j % 3}",
                dedupe_key=f"synth:{owner}:pos:{pid}:{j}",
                created_at=(now_dt - timedelta(hours=j * 7)).isoformat(timespec="seconds"),
            )
        # Negative / D19 Lowered signal on off-topic cluster.
        neg_pid = neg_pids[int(rng.integers(0, len(neg_pids)))]
        record_interaction_event(
            store,
            owner,
            post_id=neg_pid,
            topic_key=neg_topic,
            event_type="downvote",
            value=1.0,
            area_coarse=pref_area,
            session_id=f"sess_{u_idx}_neg",
            dedupe_key=f"synth:{owner}:neg:{neg_pid}",
        )
        record_interaction_event(
            store,
            owner,
            post_id=neg_pids[0],
            topic_key=neg_topic,
            event_type="lower",
            value=1.0,
            area_coarse=pref_area,
            session_id=f"sess_{u_idx}_low",
            dedupe_key=f"synth:{owner}:low:{neg_pids[0]}",
        )
        lower_usage_topic(store, owner, neg_topic)
    store.db.commit()


def _load_training_data(store: ActionStore) -> tuple[np.ndarray, np.ndarray, list[tuple[int, int, float]], list[str]]:
    """Build item vectors, user vectors, and `(user_idx, item_idx, label_weight)` triplets."""
    setup_recommender(store)
    # Prefer provenance when present so Google Limited Use rows can be excluded.
    try:
        post_rows = store.db.execute(
            "SELECT id,owner,group_id,text,provenance FROM cm_posts WHERE deleted=0"
        ).fetchall()
    except Exception:
        post_rows = store.db.execute(
            "SELECT id,owner,group_id,text FROM cm_posts WHERE deleted=0"
        ).fetchall()
    if not post_rows:
        return np.zeros((0, DIM), dtype=np.float32), np.zeros((0, DIM), dtype=np.float32), [], []

    post_idx: dict[str, int] = {}
    item_vecs: list[list[float]] = []
    post_ids: list[str] = []
    post_meta: dict[str, tuple[str, str]] = {}
    for p in post_rows:
        pid, _owner, _gid, text = p[0], p[1], p[2], p[3]
        prov = str(p[4]) if len(p) > 4 else ""
        if _is_google_limited_use_text(text, prov):
            continue
        vec, _tp, _area = encode_item_vector(text or "")
        post_idx[pid] = len(post_ids)
        post_ids.append(pid)
        item_vecs.append(vec)
        post_meta[pid] = (text or "", prov)

    # Lowered topics per owner from D19 cm_usage_profile.
    lowered_map: dict[str, set[str]] = {}
    for owner, tkey, lowered_at, suppressed in store.db.execute(
        "SELECT owner, topic_key, lowered_at, suppressed FROM cm_usage_profile"
    ).fetchall():
        if lowered_at or suppressed:
            lowered_map.setdefault(owner, set()).add((tkey or "").lower())

    ev_rows = store.db.execute(
        "SELECT owner, post_id, topic_key, event_type, value, area_coarse FROM cm_interaction_events"
    ).fetchall()

    users: dict[str, int] = {}
    user_accum: dict[str, np.ndarray] = {}
    samples: list[tuple[int, int, float, str]] = []

    for owner, pid, tkey, etype, _val, area in ev_rows:
        if pid not in post_idx:
            continue
        if owner_is_minor(store, owner):
            continue
        if tkey and is_sensitive_topic(tkey):
            continue
        text_m, prov_m = post_meta.get(pid, ("", ""))
        if _is_google_limited_use_text(tkey, text_m, prov_m):
            continue
        if owner not in users:
            users[owner] = len(users)
            user_accum[owner] = np.zeros(DIM, dtype=np.float32)
        w = EVENT_SIGNAL_WEIGHTS.get(etype, 0.0)
        if tkey and tkey.lower() in lowered_map.get(owner, set()) and w > 0:
            w = -1.5  # D19 lowered override
        i_idx = post_idx[pid]
        samples.append((users[owner], i_idx, w, etype))
        if w > 0:
            # area_coarse is ephemeral — train without permanent geo traits.
            t_vec = np.asarray(
                encode_text_topic_vector(tkey or "", area_coarse="unknown", is_query=True, apply_trained=False),
                dtype=np.float32,
            )
            user_accum[owner] += w * t_vec

    # Also fold declared adult interests for cold/sparse interactions.
    user_vecs = np.zeros((len(users), DIM), dtype=np.float32)
    for owner, uidx in users.items():
        prof = store.db.execute("SELECT interests, area FROM cm_profiles WHERE owner=?", (owner,)).fetchone()
        vec = user_accum[owner].copy()
        if prof:
            try:
                ints = [str(x) for x in json.loads(prof[0] or "[]") if not is_sensitive_topic(str(x))]
            except Exception:
                ints = []
            if ints:
                vec += 0.8 * np.asarray(
                    encode_text_topic_vector(" ".join(ints), area_coarse=prof[1] or "unknown", is_query=True),
                    dtype=np.float32,
                )
        norm = float(np.linalg.norm(vec))
        if norm > 1e-12:
            user_vecs[uidx] = vec / norm

    item_mat = np.asarray(item_vecs, dtype=np.float32)
    triplets = [(u, i, w) for u, i, w, _ in samples]
    return user_vecs, item_mat, triplets, post_ids


def _train_numpy(
    user_vecs: np.ndarray,
    item_mat: np.ndarray,
    pos_pairs: list[tuple[int, int, float]],
    neg_pairs: list[tuple[int, int, float]],
    *,
    epochs: int = 25,
    lr: float = 0.08,
    tau: float = 0.20,
) -> tuple[np.ndarray, np.ndarray]:
    w_user = np.eye(DIM, dtype=np.float32)
    w_item = np.eye(DIM, dtype=np.float32)
    if not pos_pairs:
        return w_user, w_item

    u_idx_arr = np.array([p[0] for p in pos_pairs], dtype=np.int64)
    i_idx_arr = np.array([p[1] for p in pos_pairs], dtype=np.int64)
    u_batch = user_vecs[u_idx_arr]
    i_batch = item_mat[i_idx_arr]

    for _ep in range(max(1, epochs)):
        u_proj = u_batch @ w_user
        u_norm = np.clip(np.linalg.norm(u_proj, axis=1, keepdims=True), 1e-8, None)
        u_emb = u_proj / u_norm

        i_proj = i_batch @ w_item
        i_norm = np.clip(np.linalg.norm(i_proj, axis=1, keepdims=True), 1e-8, None)
        i_emb = i_proj / i_norm

        # In-batch InfoNCE logits: (B, B)
        logits = (u_emb @ i_emb.T) / tau
        logits -= logits.max(axis=1, keepdims=True)
        exp_l = np.exp(logits)
        probs = exp_l / np.clip(exp_l.sum(axis=1, keepdims=True), 1e-12, None)
        n = len(pos_pairs)
        grad_logits = probs.copy()
        grad_logits[np.arange(n), np.arange(n)] -= 1.0
        grad_logits /= (n * tau)

        grad_u_emb = grad_logits @ i_emb
        grad_i_emb = grad_logits.T @ u_emb

        # Pairwise BPR penalty for negative / D19 lowered interactions.
        if neg_pairs:
            nu_idx = np.array([p[0] for p in neg_pairs], dtype=np.int64)
            ni_idx = np.array([p[1] for p in neg_pairs], dtype=np.int64)
            nu_proj = user_vecs[nu_idx] @ w_user
            nu_emb = nu_proj / np.clip(np.linalg.norm(nu_proj, axis=1, keepdims=True), 1e-8, None)
            ni_proj = item_mat[ni_idx] @ w_item
            ni_emb = ni_proj / np.clip(np.linalg.norm(ni_proj, axis=1, keepdims=True), 1e-8, None)
            neg_scores = (nu_emb * ni_emb).sum(axis=1, keepdims=True)
            # Push negative / lowered similarity down smoothly.
            sig = 1.0 / (1.0 + np.exp(-np.clip(neg_scores * 3.0, -10.0, 10.0)))
            scale = (0.35 / max(1, len(neg_pairs))) * sig
            w_user -= lr * (user_vecs[nu_idx].T @ (scale * ni_emb))
            w_item -= lr * (item_mat[ni_idx].T @ (scale * nu_emb))

        reg = 0.02
        grad_wu = (u_batch.T @ grad_u_emb) + reg * (w_user - np.eye(DIM, dtype=np.float32))
        grad_wi = (i_batch.T @ grad_i_emb) + reg * (w_item - np.eye(DIM, dtype=np.float32))
        w_user -= lr * grad_wu
        w_item -= lr * grad_wi

    return w_user, w_item


def _train_torch(
    user_vecs: np.ndarray,
    item_mat: np.ndarray,
    pos_pairs: list[tuple[int, int, float]],
    neg_pairs: list[tuple[int, int, float]],
    *,
    epochs: int = 25,
    lr: float = 0.04,
    tau: float = 0.20,
) -> tuple[np.ndarray, np.ndarray]:  # pragma: no cover - used when torch is installed
    assert torch is not None
    wu = torch.nn.Parameter(torch.eye(DIM, dtype=torch.float32))
    wi = torch.nn.Parameter(torch.eye(DIM, dtype=torch.float32))
    opt = torch.optim.Adam([wu, wi], lr=lr, weight_decay=1e-3)

    u_t = torch.from_numpy(user_vecs)
    i_t = torch.from_numpy(item_mat)
    pos_u = torch.tensor([p[0] for p in pos_pairs], dtype=torch.long)
    pos_i = torch.tensor([p[1] for p in pos_pairs], dtype=torch.long)
    labels = torch.arange(len(pos_pairs), dtype=torch.long)

    for _ in range(max(1, epochs)):
        opt.zero_grad()
        ue = torch.nn.functional.normalize(u_t[pos_u] @ wu, dim=-1)
        ie = torch.nn.functional.normalize(i_t[pos_i] @ wi, dim=-1)
        logits = (ue @ ie.T) / tau
        loss = torch.nn.functional.cross_entropy(logits, labels)
        if neg_pairs:
            nu = torch.tensor([p[0] for p in neg_pairs], dtype=torch.long)
            ni = torch.tensor([p[1] for p in neg_pairs], dtype=torch.long)
            nue = torch.nn.functional.normalize(u_t[nu] @ wu, dim=-1)
            nie = torch.nn.functional.normalize(i_t[ni] @ wi, dim=-1)
            neg_sim = (nue * nie).sum(dim=-1)
            loss = loss + 0.35 * torch.nn.functional.softplus(neg_sim * 3.0).mean()
        loss.backward()
        opt.step()
    return wu.detach().cpu().numpy(), wi.detach().cpu().numpy()


def evaluate_ranking(
    user_vecs: np.ndarray,
    item_mat: np.ndarray,
    w_user: np.ndarray,
    w_item: np.ndarray,
    pos_pairs: list[tuple[int, int, float]],
) -> dict[str, float]:
    """Compute Recall@20 and NDCG@10 across users with positive interactions."""
    if len(user_vecs) == 0 or len(item_mat) == 0 or not pos_pairs:
        return {"recall_at_20": 0.0, "ndcg_at_10": 0.0}

    u_proj = user_vecs @ w_user
    u_emb = u_proj / np.clip(np.linalg.norm(u_proj, axis=1, keepdims=True), 1e-8, None)
    i_proj = item_mat @ w_item
    i_emb = i_proj / np.clip(np.linalg.norm(i_proj, axis=1, keepdims=True), 1e-8, None)

    positives_by_user: dict[int, set[int]] = {}
    for u, i, _w in pos_pairs:
        positives_by_user.setdefault(u, set()).add(i)

    recalls: list[float] = []
    ndcgs: list[float] = []
    scores_all = u_emb @ i_emb.T
    for u, rel in positives_by_user.items():
        if not rel:
            continue
        order = np.argsort(-scores_all[u])
        top20 = set(int(x) for x in order[:20])
        recalls.append(len(top20 & rel) / float(len(rel)))

        dcg = 0.0
        for rank, idx in enumerate(order[:10], start=1):
            if int(idx) in rel:
                dcg += 1.0 / math.log2(rank + 1.0)
        ideal_hits = min(10, len(rel))
        idcg = sum(1.0 / math.log2(r + 1.0) for r in range(1, ideal_hits + 1))
        ndcgs.append(dcg / idcg if idcg > 0 else 0.0)

    return {
        "recall_at_20": round(float(np.mean(recalls)) if recalls else 0.0, 4),
        "ndcg_at_10": round(float(np.mean(ndcgs)) if ndcgs else 0.0, 4),
    }


def train_two_tower(
    store: ActionStore,
    *,
    output_path: Path,
    epochs: int = 25,
) -> dict[str, Any]:
    user_vecs, item_mat, triplets, _post_ids = _load_training_data(store)
    pos_pairs = [t for t in triplets if t[2] > 0]
    neg_pairs = [t for t in triplets if t[2] < 0]

    eye = np.eye(DIM, dtype=np.float32)
    baseline = evaluate_ranking(user_vecs, item_mat, eye, eye, pos_pairs)

    backend = "torch" if torch is not None else "numpy"
    if torch is not None and pos_pairs:
        w_user, w_item = _train_torch(user_vecs, item_mat, pos_pairs, neg_pairs, epochs=epochs)
    else:
        w_user, w_item = _train_numpy(user_vecs, item_mat, pos_pairs, neg_pairs, epochs=epochs)

    trained = evaluate_ranking(user_vecs, item_mat, w_user, w_item, pos_pairs)
    task_weights = dict(DEFAULT_TASK_WEIGHTS)
    if pos_pairs or neg_pairs:
        task_weights["tower"] = round(DEFAULT_TASK_WEIGHTS["tower"] + 0.15 * trained["ndcg_at_10"], 4)

    artifact = {
        "version": 1,
        "dim": DIM,
        "backend": backend,
        "trained_at": cm.now(),
        "num_users": int(len(user_vecs)),
        "num_items": int(len(item_mat)),
        "num_positives": len(pos_pairs),
        "num_negatives": len(neg_pairs),
        "metrics": {
            "recall_at_20": trained["recall_at_20"],
            "ndcg_at_10": trained["ndcg_at_10"],
            "baseline_recall_at_20": baseline["recall_at_20"],
            "baseline_ndcg_at_10": baseline["ndcg_at_10"],
        },
        "task_weights": task_weights,
        "W_user": np.round(w_user, 6).tolist(),
        "W_item": np.round(w_item, 6).tolist(),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact), encoding="utf-8")
    return artifact


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Train Community Two-Tower Recommender weights.")
    parser.add_argument("--db", default="", help="SQLite file path or Postgres URL.")
    parser.add_argument(
        "--output",
        default=str(ROOT / "apps" / "api" / "data" / "cm_recommender_weights.json"),
        help="Path to write cm_recommender_weights.json.",
    )
    parser.add_argument("--epochs", type=int, default=25)
    parser.add_argument("--synthetic-smoke", action="store_true", help="Run synthetic CI smoke training.")
    args = parser.parse_args(argv)

    out_path = Path(args.output)
    if args.synthetic_smoke:
        with tempfile.TemporaryDirectory() as tmp:
            store = ActionStore(Path(tmp) / "smoke.sqlite3")
            try:
                _populate_synthetic_db(store)
                artifact = train_two_tower(store, output_path=out_path, epochs=args.epochs)
            finally:
                store.db.close()
    else:
        db_target = args.db or str(ROOT / "apps" / "api" / "data" / "actions.sqlite3")
        store = ActionStore(db_target)
        try:
            artifact = train_two_tower(store, output_path=out_path, epochs=args.epochs)
        finally:
            store.db.close()

    m = artifact["metrics"]
    print(
        f"[two-tower] backend={artifact['backend']} items={artifact['num_items']} "
        f"pos={artifact['num_positives']} neg={artifact['num_negatives']} "
        f"Recall@20={m['recall_at_20']:.4f} (baseline={m['baseline_recall_at_20']:.4f}) "
        f"NDCG@10={m['ndcg_at_10']:.4f} (baseline={m['baseline_ndcg_at_10']:.4f}) "
        f"saved={out_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
