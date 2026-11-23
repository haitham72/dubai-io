"""Admin Operations endpoint GET /v1/ops/memory (WP-B)."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import os
from typing import Any

from fastapi import APIRouter, Depends

from temporal_memory.api.vault import AuthContext, call_opt, get_store, require_admin
from temporal_memory.models import Attempt, GraphStore, Job, Worker

router = APIRouter(prefix="/v1/ops", tags=["ops"])


def _cloud_rates() -> tuple[float, float]:
    rate_in = float(os.environ.get("TM_CLOUD_RATE_IN_PER_1M", "1.00"))
    rate_out = float(os.environ.get("TM_CLOUD_RATE_OUT_PER_1M", "5.00"))
    return rate_in, rate_out


@router.get("/memory")
def ops_memory(
    _: AuthContext = Depends(require_admin),
    store: GraphStore = Depends(get_store),
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    jobs: list[Job] = call_opt(store, "list_jobs", default=[])
    workers: list[Worker] = call_opt(store, "list_workers", default=[])
    attempts: list[Attempt] = call_opt(store, "list_attempts", default=[])

    # Queue depth by priority (active/pending states)
    depth: dict[str, int] = {"P0": 0, "P1": 0, "P2": 0, "P3": 0}
    oldest_age_s = 0.0
    for j in jobs:
        if j.state in ("queued", "leased", "submitted"):
            key = f"P{j.priority}"
            depth[key] = depth.get(key, 0) + 1
            created = getattr(j, "created_at", None) or getattr(store, "job_created_at", lambda _id: None)(j.id)
            if created:
                try:
                    dt = datetime.fromisoformat(str(created).replace("Z", "+00:00"))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    oldest_age_s = max(oldest_age_s, max(0.0, (now - dt).total_seconds()))
                except ValueError:
                    pass

    # Online workers grouped by model
    workers_by_model: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for w in workers:
        is_online = getattr(w, "status", "online") == "online"
        if is_online:
            workers_by_model[w.model].append({
                "id": w.id,
                "kind": w.kind,
                "runner": w.runner,
                "owner": w.owner,
                "released": w.released,
            })

    # Attempts by verdict per model + cost per owner per week + demo cost saved
    verdicts_per_model: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    cost_owner_week: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    jobs_by_id = {j.id: j for j in jobs}
    rate_in, rate_out = _cloud_rates()
    saved_usd = 0.0
    saved_in = 0
    saved_out = 0

    for a in attempts:
        verdict = getattr(a, "verdict", None) or "unknown"
        verdicts_per_model[a.model][verdict] += 1
        job = jobs_by_id.get(a.job_id)
        if job:
            wk = (job.day or (a.started_at or now.isoformat())[:10])[:10]
            try:
                y, w, _ = datetime.fromisoformat(wk).date().isocalendar()
                week_key = f"{y}-W{w:02d}"
            except ValueError:
                week_key = "unknown"
            cost_owner_week[job.owner][week_key] = round(cost_owner_week[job.owner][week_key] + (a.cost_usd or 0.0), 6)

        if a.worker_kind in ("owner-hook", "agent-cli"):
            saved_in += a.tokens_in
            saved_out += a.tokens_out
            saved_usd += (a.tokens_in / 1_000_000.0) * rate_in + (a.tokens_out / 1_000_000.0) * rate_out

    return {
        "queue_depth_by_priority": depth,
        "oldest_job_age_seconds": round(oldest_age_s, 2),
        "workers_online_by_model": dict(workers_by_model),
        "attempts_by_verdict_per_model": {m: dict(vs) for m, vs in verdicts_per_model.items()},
        "cost_per_owner_per_week": {o: dict(ws) for o, ws in cost_owner_week.items()},
        "demo_cost_saved_usd": round(saved_usd, 6),
        "demo_cost_saved_tokens": {"tokens_in": saved_in, "tokens_out": saved_out},
        "provenance": "provider_confirmed",
        "as_of": now.isoformat(),
    }
