"""Admin endpoints for shared vocabulary proposals (E13b, D21).

Mounted at `/v1/admin/vocab` via the minimal 2-line `mount_onto` call at the
end of `api/vault.py` (app.py's fixed module list is not owned by this work
package). This module deliberately never imports `api.vault` at module level:
the dependency wrappers below delegate to vault's `get_auth`/`require_admin`
lazily at request time, which breaks the circular import in both directions.

Every endpoint is admin-only: vault's `require_admin` returns 403 for
owner/worker/cross-owner tokens; `get_auth` returns 401 without a valid
bearer token.
"""
from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Path as FPath, Query
from pydantic import BaseModel

router = APIRouter(prefix="/v1/admin/vocab", tags=["vocab-admin"])


def _require_admin(authorization: str | None = Header(default=None)) -> Any:
    """Lazy delegate to vault's get_auth + require_admin (401/403 semantics)."""
    from temporal_memory.api.vault import get_auth, require_admin

    return require_admin(get_auth(authorization))


def _get_store() -> Any:
    from temporal_memory.api.vault import get_store

    return get_store()


def mount_onto(parent: APIRouter) -> None:
    """Include this router at absolute `/v1/admin/vocab/*` on `parent`.

    FastAPI composes the parent router's prefix into every route path at
    include time, so the owner prefix is neutralized for the include only
    and restored immediately after (E13b Phase A mount).
    """
    saved = parent.prefix
    parent.prefix = ""
    parent.include_router(router)
    parent.prefix = saved


class DecideIn(BaseModel):
    decision: Literal["approve", "reject"]


@router.post("/propose")
def propose(_: Any = Depends(_require_admin), store: Any = Depends(_get_store)) -> dict[str, Any]:
    """Cluster multi-owner signals and stage pending shared-vocab candidates."""
    from temporal_memory.vocab.shared_proposer import propose_shared_vocab_promotions

    with _db(store).transaction() as conn:
        result = propose_shared_vocab_promotions(conn)
    return {"ok": True, **result}


@router.get("/proposals")
def list_proposals(
    status: str | None = Query(default=None, pattern="^(pending|approved|rejected)$"),
    _: Any = Depends(_require_admin),
    store: Any = Depends(_get_store),
) -> dict[str, Any]:
    """List shared-vocab proposals (aggregate fields only; optional status filter)."""
    sql = (
        "SELECT id, canonical_term, aliases_en_ar, parent_path, rationale, distinct_owners, "
        "status, decided_at, decided_by, created_at FROM shared_vocab_proposals"
    )
    params: tuple[Any, ...] = ()
    if status:
        sql += " WHERE status = %s"
        params = (status,)
    sql += " ORDER BY created_at DESC, id DESC LIMIT 200"
    with _db(store).connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    items = [
        {
            "id": int(r["id"]),
            "canonical_term": r["canonical_term"],
            "aliases_en_ar": list(r["aliases_en_ar"] or []),
            "parent_path": r["parent_path"],
            "rationale": r["rationale"],
            "distinct_owners": int(r["distinct_owners"]),
            "status": r["status"],
            "decided_at": r["decided_at"],
            "decided_by": r["decided_by"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]
    return {"items": items, "count": len(items)}


@router.post("/proposals/{proposal_id}/decide")
def decide(
    proposal_id: int = FPath(..., ge=1),
    body: DecideIn = ...,
    auth: Any = Depends(_require_admin),
    store: Any = Depends(_get_store),
) -> dict[str, Any]:
    """Human approve/reject of one pending proposal (admin is the approval)."""
    from temporal_memory.live.topics import eligible_subject
    from temporal_memory.vocab.loader import get_vocab_with_approved
    from temporal_memory.vocab.shared_proposer import _prefix_blocked
    from temporal_memory.vocab.similarity import passes_privacy

    with _db(store).transaction() as conn:
        row = conn.execute(
            "SELECT * FROM shared_vocab_proposals WHERE id = %s", (proposal_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="proposal not found")
        if row["status"] != "pending":
            raise HTTPException(status_code=409, detail=f"proposal already {row['status']}")

        new_status = "approved" if body.decision == "approve" else "rejected"
        if body.decision == "approve":
            # Fail-closed revalidation at the human decision point.
            canonical = str(row["canonical_term"]).strip()
            parent = str(row["parent_path"])
            tree = get_vocab_with_approved(conn)
            parent_node = tree.by_path.get(parent)
            if (
                not passes_privacy(canonical)
                or parent_node is None
                or parent_node.sensitive
                or parent_node.blocks_proposals
                or _prefix_blocked(tree, parent)
                or not eligible_subject(f"{parent}/{canonical}", canonical)
            ):
                raise HTTPException(status_code=400, detail="proposal fails privacy or branch checks")

        cur = conn.execute(
            "UPDATE shared_vocab_proposals SET status = %s, decided_at = now(), decided_by = %s "
            "WHERE id = %s AND status = 'pending' RETURNING id, status",
            (new_status, getattr(auth, "token_id", "") or "admin", proposal_id),
        )
        updated = cur.fetchone()
        if updated is None:
            raise HTTPException(status_code=409, detail="proposal already decided")
    return {
        "id": proposal_id,
        "status": new_status,
        "decided_by": getattr(auth, "token_id", "") or "admin",
    }


def _db(store: Any):
    db = getattr(store, "db", None)
    if db is None:
        raise HTTPException(status_code=503, detail="GraphStore has no database")
    return db
