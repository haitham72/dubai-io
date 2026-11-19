import sqlite3
import pytest
from app.memory.store import MemoryStore

def test_add_chat_turn_saves_event_and_exports_pattern():
    conn = sqlite3.connect(":memory:")
    store = MemoryStore(conn)
    owner = "test-user-haitham"

    # Human message + AI message paired turn
    turn_res = store.add_chat_turn(
        owner,
        human_message="I prefer minimal reports in ide-companio, and please include gaming news.",
        ai_message="Understood! Updating your memory profile to reflect minimal logs and high gaming affinity.",
        source="quest_chat",
        proactive=False,
        extracted_facts=[
            {
                "statement": "User prefers minimal report format for developer sessions",
                "confidence": 0.95,
                "status": "confirmed",
            },
            {
                "statement": "User has high affinity for gaming news (GTA 6, PS5)",
                "confidence": 0.90,
                "status": "confirmed",
            }
        ]
    )

    assert turn_res["turn_id"]
    assert turn_res["event_id"]
    assert turn_res["deduped"] is False
    assert turn_res["exported_patterns_count"] == 2

    # Check that events are recorded in timeline
    events = store.timeline(owner)
    assert len(events) == 1
    assert "Human: I prefer minimal reports" in events[0]["text"]
    assert events[0]["kind"] == "chat_turn"

    # Check search over chat memory
    hits = store.search(owner, "ide-companio")
    assert len(hits) == 1
    assert "gaming news" in hits[0]["text"]

def test_add_proactive_ping_turn():
    conn = sqlite3.connect(":memory:")
    store = MemoryStore(conn)
    owner = "test-user-haitham"

    ping_res = store.add_chat_turn(
        owner,
        human_message="[Autonomous Ping Prompted]",
        ai_message="Hey Haitham, I apologize for earlier. I've updated your permanent preferences.",
        source="quest_proactive",
        proactive=True,
        ping_type="empathy_apology",
        extracted_facts=[
            {
                "statement": "Agent apologized for missing gaming preferences and fixed routing",
                "confidence": 1.0,
                "status": "confirmed",
            }
        ]
    )

    assert ping_res["proactive"] is True
    assert ping_res["ping_type"] == "empathy_apology"
    events = store.timeline(owner)
    assert events[0]["provenance"] == "agent_proactive"
