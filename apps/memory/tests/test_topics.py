"""Topic hypotheses require distinct owner-authored sessions."""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from temporal_memory.api import bridge, vault
from temporal_memory.live.topics import eligible_subject, match_topics
from temporal_memory.models import Owner, Subject
from tests.fixtures.fake_store import FakeGraphStore


def test_matching_uses_full_phrases_and_unambiguous_affiliations():
    subjects = [
        vars(Subject("agents", "o", "learning/ai-agents", "AI agents")),
        vars(Subject("dining", "o", "events/dining", "Dining")),
        vars(Subject("faith", "o", "faith/eid", "Eid")),
    ]
    aliases = [("a", "Zuma"), ("b", "Zuma"), ("c", "Blue Cafe")]
    assert match_topics("How do AI agents work?", subjects, aliases, []) == {"agents"}
    assert match_topics("Where is Zuma?", subjects, aliases, [("a", "dining")]) == set()
    assert match_topics("Where is Blue Cafe?", subjects, aliases, [("c", "dining"), ("c", "faith")]) == {"dining"}
    assert not eligible_subject("people-family/cousins", "Cousins")
    assert not eligible_subject("life/health/nutrition", "Nutrition")
    assert not eligible_subject("events/topics", "Public label", "health")


def test_fake_bridge_creates_one_hypothesis_and_requires_the_owner():
    store = FakeGraphStore()
    owner = "karim"
    store.owners[owner] = Owner(owner, "Synthetic")
    store.subjects[owner].extend([
        Subject("agents", owner, "learning/ai-agents", "AI agents"),
        Subject("family", owner, "people-family/cousins", "Cousins"),
    ])
    vault.configure(store=store, auth_verifier=lambda _: vault.AuthContext(role="owner-device", owner=owner))
    app = FastAPI()
    app.include_router(bridge.router)
    client = TestClient(app)

    def post(rid, session, text, author=owner):
        response = client.post("/v1/owners/karim/records", json={"records": [{
            "id": rid, "source": "live", "at": "2026-11-24T12:00:00+04:00",
            "author": author, "text": text, "meta": {"session_id": session},
        }]})
        assert response.status_code == 200, response.text
        return response.json()

    assert post("r1", "s1", "How do AI agents work?")["job_id"] is None
    assert not post("r2", "s1", "Tell me about AI agents")["fact_ids"]
    assert not post("r3", "s2", "Tell me about AI agents", "sara")["fact_ids"]
    assert not post("r4", "s2", "Do you know any cousins?")["fact_ids"]
    assert post("r5", "s2", "Tell me about AI agents again")["fact_ids"]
    assert not post("r6", "s3", "Tell me about AI agents again")["fact_ids"]
    hypothesis, = store.facts[owner]
    assert hypothesis.status == "hypothesis"
    assert hypothesis.provenance == "inferred"
    assert hypothesis.evidence == ["r1", "r5"]
    assert store.topic_session_count(owner, "family") == 0
