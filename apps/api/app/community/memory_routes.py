"""Consent, Lower (D19), and Forget for Community. Default is off. There is no messenger here."""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict

from app.memory_bridge.models import ConsentDeniedError, MinorProtectionError

from . import store as cm
from .memory import bridge_of
from .routes import scope

router = APIRouter(tags=["community-memory"])


class ConsentIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    read_enabled: bool | None = None
    write_enabled: bool | None = None
    allow_interest_export: bool | None = None
    remember_saved_discussions: bool | None = None
    remember_public_posts: bool | None = None


class LowerIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    target_id: str | None = None
    topic: str | None = None
    source_id: str | None = None
    kind: str | None = None


def _get_split_prefs(store, owner: str) -> tuple[bool, bool]:
    with store.lock:
        cm.setup(store)
        row = store.db.execute(
            "SELECT remember_saved_discussions, remember_public_posts FROM cm_memory_preferences WHERE owner=?",
            (owner,),
        ).fetchone()
    if not row:
        return False, False
    return bool(row[0]), bool(row[1])


def _save_split_prefs(store, owner: str, remember_saved: bool, remember_public: bool) -> None:
    stamp = cm.now()
    with store.lock:
        cm.setup(store)
        store.db.execute(
            """INSERT INTO cm_memory_preferences (owner, remember_saved_discussions, remember_public_posts, updated_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(owner) DO UPDATE SET
                   remember_saved_discussions=excluded.remember_saved_discussions,
                   remember_public_posts=excluded.remember_public_posts,
                   updated_at=excluded.updated_at""",
            (owner, int(bool(remember_saved)), int(bool(remember_public)), stamp),
        )
        store.db.commit()


def _state(grant, source_enabled: bool, remember_saved: bool = False, remember_public: bool = False) -> dict:
    return {
        "read_enabled": grant.read_enabled,
        "write_enabled": grant.write_enabled,
        "allow_interest_export": grant.allow_interest_export,
        "remember_saved_discussions": remember_saved,
        "remember_public_posts": remember_public,
        "default_off": not (
            grant.read_enabled
            or grant.write_enabled
            or grant.allow_interest_export
            or remember_saved
            or remember_public
        ),
        "source_enabled": source_enabled,
        "generation": grant.generation,
        "as_of": grant.updated_at,
        "provenance": "user_supplied",
    }


@router.get("/api/community/memory/consent")
def get_consent(request: Request):
    """Current server-side consent. Nothing is assumed: the UI shows only what this returns."""
    store, owner = scope(request)
    bridge = bridge_of(request)
    principal = getattr(request.state, "community_principal", None)
    if bridge is None or principal is None:
        raise HTTPException(503, "Memory bridge is not configured")
    if principal.is_minor_protected:
        raise HTTPException(403, detail={"code": "adults_only", "message": "Community is adults only (18+)."})
    app = bridge.get_consent(principal, "app", "community")
    source = bridge.get_consent(principal, "source", "community")
    remember_saved, remember_public = _get_split_prefs(store, owner)
    return _state(app, source.enabled, remember_saved, remember_public)


@router.post("/api/community/memory/consent")
@router.put("/api/community/memory/consent")
def set_consent(body: ConsentIn, request: Request):
    store, owner = scope(request)
    bridge = bridge_of(request)
    principal = getattr(request.state, "community_principal", None)
    if bridge is None or principal is None:
        raise HTTPException(503, "Memory bridge is not configured")
    if principal.is_minor_protected:
        raise HTTPException(403, detail={"code": "adults_only", "message": "Community is adults only (18+)."})
    cur_app = bridge.get_consent(principal, "app", "community")
    cur_saved, cur_public = _get_split_prefs(store, owner)
    split_passed = (body.remember_saved_discussions is not None) or (body.remember_public_posts is not None)
    remember_saved = bool(body.remember_saved_discussions) if body.remember_saved_discussions is not None else cur_saved
    remember_public = bool(body.remember_public_posts) if body.remember_public_posts is not None else cur_public
    if split_passed:
        write_enabled = remember_saved or remember_public
    elif body.write_enabled is not None:
        write_enabled = bool(body.write_enabled)
    else:
        write_enabled = cur_app.write_enabled
    read_enabled = bool(body.read_enabled) if body.read_enabled is not None else cur_app.read_enabled
    allow_interest_export = (
        bool(body.allow_interest_export)
        if body.allow_interest_export is not None
        else cur_app.allow_interest_export
    )
    try:
        # Switching a toggle off must never erase anything: Forget is its own explicit action.
        source = bridge.set_source_consent(
            principal, "community",
            enabled=write_enabled or read_enabled or allow_interest_export,
            allow_interest_export=allow_interest_export,
            forget_on_revoke=False,
        )
        app = bridge.set_app_consent(
            principal,
            "community",
            read_enabled=read_enabled,
            write_enabled=write_enabled,
            allow_interest_export_to_community=allow_interest_export,
        )
    except (ConsentDeniedError, MinorProtectionError) as exc:
        raise HTTPException(403, str(exc)) from exc
    if split_passed:
        _save_split_prefs(store, owner, remember_saved, remember_public)
    elif body.write_enabled is False:
        remember_saved, remember_public = False, False
        _save_split_prefs(store, owner, False, False)
    return _state(app, source[0].enabled, remember_saved, remember_public) | {
        "allow_interest_export": source[0].allow_interest_export,
    }


@router.post("/api/community/memory/lower")
def lower_memory(request: Request, body: LowerIn | None = None):
    """D19: Lower usage-profile weights to 0.01 without deleting history (real write)."""
    store, owner = scope(request)
    principal = getattr(request.state, "community_principal", None)
    if principal is not None and principal.is_minor_protected:
        raise HTTPException(403, detail={"code": "adults_only", "message": "Community is adults only (18+)."})

    from .context_profile import WEIGHT_MIN, lower_usage_topic, setup_context_profile

    topic = None
    if body is not None:
        topic = (body.topic or body.target_id or body.source_id or "").strip() or None

    with store.lock:
        setup_context_profile(store)
        updated = 0
        if topic:
            result = lower_usage_topic(store, owner, topic)
            updated = int(result.get("updated") or 0)
        else:
            topics = [
                r[0]
                for r in store.db.execute(
                    "SELECT DISTINCT topic_key FROM cm_usage_profile WHERE owner=? AND topic_key <> ''",
                    (owner,),
                ).fetchall()
            ]
            for tkey in topics:
                updated += int(lower_usage_topic(store, owner, tkey).get("updated") or 0)

    payload = {
        "lowered": updated > 0,
        "weight": WEIGHT_MIN,
        "w_min": WEIGHT_MIN,
        "weights_lowered": updated,
        "updated": updated,
        "as_of": datetime.now(timezone.utc).isoformat(),
        "provenance": "user_supplied",
    }
    if body is not None:
        if body.target_id is not None:
            payload["target_id"] = body.target_id
        if body.topic is not None:
            payload["topic"] = body.topic
        if body.source_id is not None:
            payload["source_id"] = body.source_id
    return payload


@router.post("/api/community/memory/forget")
def forget(request: Request):
    store, owner = scope(request)
    del store, owner
    bridge = bridge_of(request)
    principal = getattr(request.state, "community_principal", None)
    if bridge is None or principal is None:
        raise HTTPException(503, "Memory bridge is not configured")
    receipt = bridge.forget_source(principal, "community", host_app="community", idempotency_key=f"forget-community-{principal.user_id}")
    return {
        "forgotten": True,
        "records_forgotten": receipt.records_forgotten,
        "facts_erased": receipt.facts_erased,
        "as_of": datetime.now(timezone.utc).isoformat(),
        "provenance": "provider_confirmed",
    }
