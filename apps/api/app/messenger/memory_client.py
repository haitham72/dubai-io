"""Messenger memory client. Facts go through the bridge. Chat rows stay in mg_*."""

from __future__ import annotations

from app.memory_bridge.models import GroupConsentSnapshot, MemoryRecordInput
from app.messenger.store import ChatStore


def _group(store: ChatStore, conversation_id: str, caller_id: str) -> GroupConsentSnapshot:
    modes = store.ai_modes(conversation_id)
    caller_ok = caller_id in modes
    all_on = bool(modes) and all(mode in ("session", "save") for mode in modes.values())
    cited_save = bool(modes) and all(mode == "save" for mode in modes.values())
    return GroupConsentSnapshot(conversation_id, caller_ok, all_on, cited_save, 1)


def save_approved(store: ChatStore, bridge, principal, conversation_id: str, message: dict, *, confirmed: bool):
    if not confirmed:
        raise PermissionError("confirm_required")
    modes = store.ai_modes(conversation_id)
    if modes.get(principal.user_id, "off") != "save":
        raise PermissionError("ai_default_off")
    group = _group(store, conversation_id, principal.user_id)
    if not group.all_active_members_ai_enabled:
        raise PermissionError("group_off")
    return bridge.write_consented(
        principal,
        MemoryRecordInput(
            record_id=f"mgmsg:{message['id']}",
            source_kind="messenger",
            source_id=f"messenger:{conversation_id}",
            host_app="messenger",
            author_id=message["sender_id"],
            text=message["body"],
            valid_time=message["created_at"],
            explicit_user_confirm=message["sender_id"] == principal.user_id,
        ),
        group_consent=group,
    )


def model_may_read(store: ChatStore, conversation_id: str, caller_id: str) -> None:
    if not _group(store, conversation_id, caller_id).all_active_members_ai_enabled:
        raise PermissionError("group_off")


def forget_chat(bridge, principal, conversation_id: str, *, key: str):
    return bridge.forget_conversation(principal, conversation_id, idempotency_key=key)
