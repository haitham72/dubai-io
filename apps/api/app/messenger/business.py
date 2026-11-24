"""Chat-to-action chain. The model proposes. A tap is the only side effect, and it stays blocked without an adapter."""

from __future__ import annotations

from app.actions import ActionEngine, InputValue, PrepareIn
from app.messenger.capabilities import TASK
from app.messenger.store import ChatStore

_JOKE = ("haha", "lol", "good one")


def summarise(store: ChatStore, user_id: str, conversation_id: str) -> dict:
    messages = store.since(conversation_id, user_id, 0)
    return {
        "scope": conversation_id,
        "citations": [item["id"] for item in messages if not item["deleted"]],
        "decision_written": False,
    }


def decision_from_messages(messages: list[dict]) -> dict | None:
    usable = [item for item in messages if not item["deleted"]]
    if len(usable) < 2:
        return None
    blob = " ".join(item["body"].lower() for item in usable)
    if any(token in blob for token in _JOKE) and "deadline" not in blob and "agree" not in blob:
        return None
    if "agree" not in blob and "deadline" not in blob:
        return None
    return {
        "text": usable[-1]["body"],
        "evidence_ids": [item["id"] for item in usable],
        "status": "candidate",
    }


def propose_decision(store: ChatStore, user_id: str, conversation_id: str) -> dict | None:
    found = decision_from_messages(store.since(conversation_id, user_id, 0))
    if found is None:
        return None
    return store.save_decision(conversation_id, user_id, found["text"], found["evidence_ids"], recorded=False)


def note_model_text(text: str) -> dict:
    return {"text": text, "status": None}


def reminder_for(caller_id: str, target_id: str) -> None:
    if caller_id != target_id:
        raise PermissionError("no_reminder_for_another_member")


def prepare_task(engine: ActionEngine, owner: str, *, title: str, assignee: str, due: str, evidence_ids: list[str], key: str) -> dict:
    body = PrepareIn(
        capability_id=TASK,
        fields={
            "title": InputValue(value=title),
            "assignee": InputValue(value=assignee),
            "due": InputValue(value=due),
            "evidence_message_ids": InputValue(value=",".join(evidence_ids)),
        },
        preparation_key=key,
    )
    return engine.prepare(owner, body)
