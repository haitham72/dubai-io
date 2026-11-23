"""MG-B6 business-agent chain over mg_messages. No adapter, so the task stays blocked."""

import json
from pathlib import Path

import pytest
from fastapi import HTTPException

from app.actions import ActionEngine, ActionStore, ApprovalIn
from app.messenger.business import (
    decision_from_messages,
    note_model_text,
    prepare_task,
    propose_decision,
    reminder_for,
    summarise,
)
from app.messenger.store import ChatError, ChatStore

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "messenger" / "marina" / "week12.json"


def _seed(tmp_path):
    script = json.loads(FIXTURE.read_text(encoding="utf-8"))
    store = ChatStore(tmp_path / "chat.sqlite3")
    members = {name: f"usr_{name.lower()}" for name in script["members"]}
    conv = store.create_conversation(members["Rana"], [members["Layla"], members["Omar"]], kind="group", title=script["title"])
    sent = []
    for item in script["messages"]:
        sent.append(store.send(conv, members[item["sender"]], item["client_msg_id"], item["text"]))
    return store, conv, members, sent


def test_messenger_demo_chain_and_denial(tmp_path):
    store, conv, members, sent = _seed(tmp_path)
    summary = summarise(store, members["Rana"], conv)
    assert summary["decision_written"] is False
    assert summary["citations"] == [item["id"] for item in sent]
    engine = ActionEngine(ActionStore(tmp_path / "actions.sqlite3"))
    draft = prepare_task(
        engine,
        members["Rana"],
        title="Order the Friday panels",
        assignee="Omar",
        due="Friday",
        evidence_ids=[item["id"] for item in sent],
        key="prep-marina-1",
    )
    assert draft["status"] == "BLOCKED"
    assert draft["blocked_reason"]
    with pytest.raises(ChatError) as denied:
        summarise(store, "usr_noor", conv)
    assert denied.value.status == 404


def test_messenger_ai_side_effect_needs_approval(tmp_path):
    store, conv, members, sent = _seed(tmp_path)
    noted = note_model_text("Completed and Paid")
    assert noted["status"] is None
    engine = ActionEngine(ActionStore(tmp_path / "actions.sqlite3"))
    draft = prepare_task(
        engine,
        members["Rana"],
        title="Order the Friday panels",
        assignee="Omar",
        due="Friday",
        evidence_ids=[sent[0]["id"]],
        key="prep-marina-2",
    )
    with pytest.raises(HTTPException) as blocked:
        engine.approve(
            members["Rana"],
            draft["id"],
            ApprovalIn(snapshot_hash=draft["snapshot_hash"], revision=draft["revision"]),
            "approve-1",
        )
    assert blocked.value.status_code == 409
    kept = engine.get(members["Rana"], draft["id"])
    assert kept["status"] == "BLOCKED"
    assert kept["status"] not in {"COMPLETED", "CONFIRMED", "PAID", "Confirmed", "Paid"}
    assert store.count_messages(conv) == 3


def test_messenger_joke_is_not_an_obligation():
    found = decision_from_messages([
        {"id": "j1", "body": "haha good one", "deleted": False},
        {"id": "j2", "body": "lol", "deleted": False},
    ])
    assert found is None


def test_messenger_no_reminder_for_another_member():
    with pytest.raises(PermissionError):
        reminder_for("usr_rana", "usr_omar")


def test_messenger_decision_stays_candidate_until_tap(tmp_path):
    store, conv, members, _sent = _seed(tmp_path)
    candidate = propose_decision(store, members["Rana"], conv)
    assert candidate["status"] == "candidate"
    recorded = store.record_decision(conv, members["Layla"], candidate["id"])
    assert recorded["status"] == "recorded"
