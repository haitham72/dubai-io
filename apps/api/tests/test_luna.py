"""Luna tests.
Offline: validation clamps and the stated-fact store (no network).
Live golden set: runs only with RUN_LIVE=1 and a key, because every case calls the model.
  cd apps/api && RUN_LIVE=1 .venv/Scripts/python -m pytest -q
"""
import os

import pytest

from app.luna import graph as luna
from app.actions import ActionStore
from app.luna.graph import validate
from app.user_profile import ProfileStore


def base(**kw):
    u = {"intent": "places_near", "confidence": 0.9, "item": None, "where_lost": None, "service": None, "category": "pets",
         "subcategory": "Grooming", "terminal": None, "stated_facts": [], "reply": "Here you go.", "clarify": None}
    u.update(kw)
    return {"understanding": u}


def test_low_confidence_becomes_a_question():
    out = validate(base(confidence=0.4))["understanding"]
    assert out["intent"] == "unclear" and out["clarify"]


def test_slots_outside_the_intent_are_dropped():
    out = validate(base(intent="lost_item", item="wallet", category="pets", subcategory="Vet"))["understanding"]
    assert out["category"] is None and out["subcategory"] is None and out["item"] == "wallet"


def test_unknown_subcategory_is_dropped():
    out = validate(base(subcategory="Spa"))["understanding"]
    assert out["subcategory"] is None


def test_reply_never_carries_links_or_phone_numbers():
    out = validate(base(reply="Call +971 4 000 0000 or see https://example.com now"))["understanding"]
    assert "http" not in out["reply"] and "000" not in out["reply"]


def test_greeting_is_not_gated_by_confidence():
    out = validate(base(intent="greeting", confidence=0.3, category=None, subcategory=None))["understanding"]
    assert out["intent"] == "greeting"


def test_task_suggestions_are_dropped_outside_task_help_or_below_confidence():
    edits = [{"field":"due_at","value":"2026-10-24T09:00:00+04:00"}]
    assert validate(base(intent="greeting",task_edits=edits))["understanding"]["task_edits"] == []
    assert validate(base(intent="task_help",confidence=.3,task_edits=edits))["understanding"]["task_edits"] == []
    assert validate(base(intent="task_help",task_edits=edits))["understanding"]["task_edits"] == edits


def test_fact_store_supersedes_and_forgets(tmp_path):
    store = ActionStore(tmp_path / "a.sqlite3")
    s = ProfileStore(lambda: store)
    s.add("u", "area", "JLT", "I live in JLT")
    s.add("u", "area", "Dubai Marina", "I moved to the Marina")
    cur = s.current("u")
    assert [f["value"] for f in cur] == ["Dubai Marina"] and cur[0]["provenance"] == "user_supplied"
    assert len(s.history("u", "area")) == 2  # history kept
    assert s.forget("u", "area") == 2 and s.current("u") == []


GOLDEN = [
    ("lost my wallet", "lost_item", {"item": "wallet"}),
    ("I left my phone in the taxi from the airport", "lost_item", {"where_lost": "taxi"}),
    ("lost my walet in teh taksi", "lost_item", {}),
    ("ضاعت محفظتي في التاكسي", "lost_item", {}),
    ("guide me through the airport, I just landed at terminal 3", "airport_guide", {"terminal": "3"}),
    ("home cleaning prices for tomorrow", "service_offers", {"service": "cleaning"}),
    ("my AC is not cooling", "service_offers", {"service": "ac"}),
    ("I need someone to groom my dog at home", "service_offers", {"service": "grooming"}),
    ("is there a vet near me", "places_near", {"category": "pets"}),
    ("good coffee nearby", "places_near", {"category": "coffee"}),
    ("hi", "greeting", {}),
]


@pytest.mark.skipif(not (os.getenv("RUN_LIVE") and luna.settings.openai_api_key), reason="live model calls; set RUN_LIVE=1")
@pytest.mark.parametrize("text,intent,slots", GOLDEN)
def test_golden(text, intent, slots):
    out = luna.turn(thread_id=f"golden-{abs(hash(text))}", user_id="golden", text=text)
    assert out["intent"] == intent, out
    for k, v in slots.items():
        assert (out.get(k) or "").lower().startswith(v.lower()), (k, out)


def test_display_text_cannot_claim_execution_or_price():
    out = validate(base(reply="I booked it for AED 50", clarify="Your report was filed"))["understanding"]
    assert out["reply"] == "How can I help with your next step?"
    assert out["clarify"] == "How can I help with your next step?"


def test_thread_key_is_scoped_to_user(monkeypatch):
    calls = []
    def invoke(state, config):
        calls.append(config["configurable"]["thread_id"])
        return {"understanding": base()["understanding"], "history": []}
    monkeypatch.setattr(luna.graph, "invoke", invoke)
    monkeypatch.setattr(luna.facts, "current", lambda _: [])
    luna.turn("same-thread", "alice", "hi")
    luna.turn("same-thread", "bob", "hi")
    assert len(set(calls)) == 2 and all(len(key) == 64 for key in calls)
    luna.turn("b:c", "a", "hi")
    luna.turn("c", "a:b", "hi")
    assert calls[-1] != calls[-2]


def test_requests_and_incidents_are_not_stored_as_user_facts():
    from app.luna.graph import EVENT
    assert EVENT.search("Left their bag in a taxi") and EVENT.search("Needs a shirt pressed")
    assert not EVENT.search("Meeting at 9am") and not EVENT.search("leftover rice")
