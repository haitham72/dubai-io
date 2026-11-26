"""Messenger "Save to memory": one explicit tap per message, consent-scoped, honest about every refusal.

Messages are never memories on their own. The preview lists exactly what would be shared; the save needs
`confirmed: true`; the server reads the message text itself (the client cannot supply or alter it).
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Body, Depends, HTTPException, Request

from app.identity.deps import require_app_principal
from app.identity.models import VerifiedPrincipal
from app.memory_bridge import sensitive
from app.memory_bridge.models import MemoryBridgeError, SensitiveContentError
from app.messenger import memory_client
from app.messenger.store import ChatError

router = APIRouter()
_member = require_app_principal("messenger", frozenset({"messenger:chat"}))
_writer = require_app_principal("messenger", frozenset({"messenger:chat", "memory:write:chat"}))
_forgetter = require_app_principal("messenger", frozenset({"messenger:chat", "memory:forget:chat"}))

_REASONS = {
    "confirm_required": "Needs your explicit approval.",
    "ai_default_off": "Memory is off for this chat. Nothing is saved until you turn it on.",
    "group_off": "Not every member of this chat has memory on, so nothing from it can be saved.",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _bridge(request: Request):
    bridge = getattr(request.app.state, "memory_bridge", None)
    if bridge is None:
        raise HTTPException(503, detail={"code": "memory_unavailable", "message": "Memory is not configured on this server."})
    return bridge


def _bridge_error(exc: MemoryBridgeError) -> HTTPException:
    detail = {"code": getattr(exc, "code", "memory_error"), "message": str(exc)}
    if isinstance(exc, SensitiveContentError):
        detail["held_back"] = True
    status = getattr(exc, "status_code", 400)
    return HTTPException(status if status in (400, 403, 409, 422, 503) else 400, detail=detail)


def _message(request: Request, conversation_id: str, message_id: str, user_id: str) -> dict:
    try:
        message = request.app.state.chat_store.get_message(conversation_id, user_id, message_id)
    except ChatError as exc:
        raise HTTPException(exc.status, exc.code) from exc
    if message is None or message["deleted"]:
        raise HTTPException(404, detail={"code": "message_not_found", "message": "That message is not available."})
    return message


def _blockers(request: Request, principal: VerifiedPrincipal, conversation_id: str, message: dict) -> list[dict]:
    out: list[dict] = []
    if sensitive.pre_write(message["body"]) is not None:
        out.append({"code": "held_back", "message": "Held back: this looks sensitive, so it is never offered for memory."})
    modes = request.app.state.chat_store.ai_modes(conversation_id)
    if modes.get(principal.user_id, "off") != "save":
        out.append({"code": "ai_default_off", "message": _REASONS["ai_default_off"]})
    elif not (modes and all(m == "save" for m in modes.values())):
        out.append({"code": "group_off", "message": _REASONS["group_off"]})
    bridge = getattr(request.app.state, "memory_bridge", None)
    if bridge is None:
        out.append({"code": "memory_unavailable", "message": "Memory is not configured on this server."})
    elif not bridge.get_consent(principal, "source", "messenger").enabled:
        out.append({"code": "source_off", "message": "Messenger memory is switched off in Settings > Memory."})
    return out


@router.get("/api/messenger/conversations/{conversation_id}/messages/{message_id}/memory-preview")
def memory_preview(conversation_id: str, message_id: str, request: Request, principal: VerifiedPrincipal = Depends(_member)):
    message = _message(request, conversation_id, message_id, principal.user_id)
    mine = message["sender_id"] == principal.user_id
    blockers = _blockers(request, principal, conversation_id, message)
    held = any(b["code"] == "held_back" for b in blockers)
    return {
        "offerable": not held,  # sensitive content is never offered; other blockers the user can fix
        "can_save_now": not blockers,
        "blockers": blockers,
        "fields": [] if held else [
            {"name": "Message text", "value": message["body"]},
            {"name": "Written by", "value": "You" if mine else "Another member of this chat"},
            {"name": "Sent at", "value": message["created_at"]},
            {"name": "Scope", "value": "This conversation only (not shared with other apps)"},
        ],
        "provenance": "user_supplied" if mine else None,
        "as_of": message["created_at"],
    }


@router.post("/api/messenger/conversations/{conversation_id}/messages/{message_id}/memory")
def save_to_memory(conversation_id: str, message_id: str, request: Request, body: dict = Body(default={}), principal: VerifiedPrincipal = Depends(_writer)):
    bridge = _bridge(request)
    message = _message(request, conversation_id, message_id, principal.user_id)
    if body.get("confirmed") is not True:
        raise HTTPException(403, detail={"code": "confirm_required", "message": _REASONS["confirm_required"]})
    if sensitive.pre_write(message["body"]) is not None:
        raise HTTPException(422, detail={"code": "held_back", "held_back": True, "message": "Held back: this looks sensitive and was not saved."})
    try:
        receipt = memory_client.save_approved(request.app.state.chat_store, bridge, principal, conversation_id, message, confirmed=True)
    except PermissionError as exc:
        code = str(exc)
        raise HTTPException(403, detail={"code": code, "message": _REASONS.get(code, "Not allowed.")}) from exc
    except MemoryBridgeError as exc:
        raise _bridge_error(exc) from exc
    return {
        "saved": bool(receipt.ok and receipt.status in ("applied", "queued")),
        "status": receipt.status,
        "held_back": receipt.status == "quarantined",
        "record_id": receipt.record_id,
        "as_of": receipt.recorded_at or _now(),
    }


@router.get("/api/messenger/memory")
def memory_state(request: Request, principal: VerifiedPrincipal = Depends(_member)):
    bridge = _bridge(request)
    chat = request.app.state.chat_store
    source = bridge.get_consent(principal, "source", "messenger")
    items = []
    lowered = bridge.client.lowered_record_ids(principal.user_id)
    for ref in bridge.list_record_refs(principal, "messenger"):
        conv = ref["source_id"].split(":", 1)[-1]
        text = None
        if ref["record_id"].startswith("mgmsg:"):
            try:
                msg = chat.get_message(conv, principal.user_id, ref["record_id"][len("mgmsg:"):])
            except ChatError:
                msg = None
            text = msg["body"] if msg and not msg["deleted"] else None
        items.append({
            "record_id": ref["record_id"],
            "lowered": ref["record_id"] in lowered,
            "conversation_id": conv,
            "text": text,
            "saved_at": ref["saved_at"],
            "provenance": "user_supplied" if ref["author_is_owner"] else None,
            "written_by_you": ref["author_is_owner"],
        })
    return {"enabled": source.enabled, "as_of": source.updated_at, "items": items}


@router.put("/api/messenger/memory/consent")
def set_consent(request: Request, body: dict = Body(...), principal: VerifiedPrincipal = Depends(_writer)):
    """Master switch for Messenger extraction. Off never deletes anything: Lower is separate."""
    if not isinstance(body.get("enabled"), bool):
        raise HTTPException(422, detail={"code": "enabled_required", "message": "enabled must be true or false."})
    enabled = body["enabled"]
    bridge = _bridge(request)
    try:
        grant, _receipt = bridge.set_source_consent(principal, "messenger", enabled=enabled, forget_on_revoke=False)
        bridge.set_app_consent(principal, "messenger", read_enabled=enabled, write_enabled=enabled)
    except MemoryBridgeError as exc:
        raise _bridge_error(exc) from exc
    return {"enabled": grant.enabled, "as_of": grant.updated_at}


@router.put("/api/messenger/conversations/{conversation_id}/memory-mode")
def set_mode(conversation_id: str, request: Request, body: dict = Body(...), principal: VerifiedPrincipal = Depends(_writer)):
    mode = body.get("mode")
    if mode not in ("off", "session", "save"):
        raise HTTPException(422, detail={"code": "bad_mode", "message": "mode must be off, session or save."})
    bridge = _bridge(request)
    try:
        request.app.state.chat_store.set_ai_mode(conversation_id, principal.user_id, mode)
        grant, _ = bridge.set_conversation_consent(principal, conversation_id, ai_mode=mode)
    except ChatError as exc:
        raise HTTPException(exc.status, exc.code) from exc
    except MemoryBridgeError as exc:
        raise _bridge_error(exc) from exc
    return {"conversation_id": conversation_id, "mode": mode, "as_of": grant.updated_at}


@router.post("/api/messenger/memory/lower")
@router.post("/api/messenger/memory/forget", include_in_schema=False)
def lower_item(request: Request, body: dict = Body(...), principal: VerifiedPrincipal = Depends(_forgetter)):
    record_id = body.get("record_id")
    if not isinstance(record_id, str) or not record_id.startswith("mgmsg:"):
        raise HTTPException(422, detail={"code": "record_id_required", "message": "A Messenger record is required."})
    lower = body.get("lower", True)
    if type(lower) is not bool:
        raise HTTPException(422, detail="lower must be a boolean")
    try:
        bridge = _bridge(request)
        if record_id not in {item["record_id"] for item in bridge.list_record_refs(principal, "messenger")}:
            raise HTTPException(404, detail="Saved Messenger memory not found")
        result = bridge.client.set_memory_lowered(principal.user_id, lower=lower, record_ids=[record_id])
    except MemoryBridgeError as exc:
        raise _bridge_error(exc) from exc
    return {**result, "as_of": _now(), "provenance": "provider_confirmed"}
