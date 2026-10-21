"""Temporal behavior, privacy, repetition caps and explicit intent precedence."""
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app import actions, recommendations as rec
from app.actions import ActionEngine, ActionStore


@pytest.fixture
def client(tmp_path, monkeypatch):
    store = ActionStore(tmp_path / "rec.sqlite3")
    monkeypatch.setattr(actions,"_engine",ActionEngine(store))
    app = FastAPI()
    app.include_router(actions.router)
    app.include_router(rec.router)
    c = TestClient(app)
    c.get("/api/session")
    yield c,store
    store.db.close()


def event(entity="one", kind="detail", topic="food.seafood", key=None, session="session-one"):
    return {"event_key":key or "event-key-"+entity,"session_id":session,"kind":kind,"topic":topic,"entity_id":entity}


def record(c,*events):
    response = c.post("/api/recommendation-events",json={"events":events})
    assert response.status_code == 200,response.text
    return response.json()["recorded"]


def rank(c, **kw):
    body = {"session_id":"session-one","surface":"maps","candidates":[
        {"id":"coffee","topics":["food.cafes"]},{"id":"fish","topics":["food.seafood"]}]}
    body.update(kw)
    response = c.post("/api/recommendations",json=body)
    assert response.status_code == 200,response.text
    return response.json()


def test_two_distinct_choices_adapt_this_visit_and_have_a_reason(client):
    c,_ = client
    assert rank(c)["results"][0]["id"] == "coffee"
    record(c,event("one",kind="choose"),event("two",kind="choose"))
    result = rank(c)
    assert result["results"][0]["id"] == "fish"
    assert "Because you explored seafood" == result["results"][0]["reason"]
    # User's explicit next request wins and closest/price modes preserve supplied order.
    assert rank(c,intent="food.cafes")["results"][0]["id"] == "coffee"
    assert rank(c,sort="closest")["results"][0]["id"] == "coffee"
    assert rank(c,sort="price")["results"][0]["id"] == "coffee"
    rows = c.get("/api/profile/interests?session_id=session-one").json()["interests"]
    assert {r["scope"] for r in rows} == {"session","long_term"}
    assert all(r["provenance"] == "inferred" and r["usage_class"] == "organic_only" for r in rows)


def test_replays_and_repeated_same_item_do_not_inflate(client):
    c,_ = client
    assert record(c,event()) == 1
    before = c.get("/api/profile/interests?session_id=session-one").json()["interests"]
    assert record(c,event()) == 0
    record(c,event(key="fresh-key-123"))
    after = c.get("/api/profile/interests?session_id=session-one").json()["interests"]
    assert before == after
    assert rank(c)["results"][0]["id"] == "coffee"  # One item is insufficient.


def test_decay_and_session_expiry(client,monkeypatch):
    c,_ = client
    at = 1792500000.
    monkeypatch.setattr(rec,"clock",lambda:at)
    record(c,event("one",kind="choose"),event("two",kind="choose"))
    before = c.get("/api/profile/interests?session_id=session-one").json()["interests"]
    at += 1800
    after = c.get("/api/profile/interests?session_id=session-one").json()["interests"]
    assert next(r for r in after if r["scope"]=="session")["signal"] < next(r for r in before if r["scope"]=="session")["signal"]
    at += rec.DAY
    assert {r["scope"] for r in c.get("/api/profile/interests?session_id=session-one").json()["interests"]} == {"long_term"}
    assert {r["scope"] for r in c.get("/api/profile/interests?session_id=another-session").json()["interests"]} == {"long_term"}


@pytest.mark.parametrize("topic",["health.diabetes","politics.party","religion","nationality"])
def test_sensitive_topics_and_untrusted_scores_cannot_enter(client,topic):
    c,_ = client
    assert c.post("/api/recommendation-events",json={"events":[event(topic=topic)]}).status_code == 422
    assert c.post("/api/recommendation-events",json={"events":[{**event(),"weight":100}]}).status_code == 422
    assert c.post("/api/recommendation-events",json={"events":[event(kind="completed")]}).status_code == 422


def test_no_click_or_item_dismissal_is_not_topic_dislike(client):
    c,_ = client
    record(c,event(kind="dismiss"))
    assert c.get("/api/profile/interests").json()["interests"] == []


def test_forget_erases_evidence_runs_and_stops_relearning_until_resume(client):
    c,store = client
    record(c,event("one",kind="choose"),event("two",kind="choose"))
    rank(c)
    assert c.put("/api/profile/interests/food.seafood",json={"action":"forget"}).status_code == 200
    assert store.db.execute("SELECT COUNT(*) FROM recommendation_events").fetchone()[0] == 0
    assert store.db.execute("SELECT COUNT(*) FROM recommendation_runs").fetchone()[0] == 0
    assert record(c,event("three",kind="save")) == 0
    assert rank(c)["results"][0]["reason"] is None
    c.put("/api/profile/interests/food.seafood",json={"action":"resume"})
    assert record(c,event("three",kind="save")) == 1


def test_confirmation_is_explicit_and_owner_is_never_client_supplied(client):
    c,store = client
    other = TestClient(c.app)
    assert other.get("/api/profile/interests").status_code == 401
    other.get("/api/session")
    record(c,event("one"))
    assert other.get("/api/profile/interests").json()["interests"] == []
    assert c.post("/api/recommendation-events",json={"events":[{**event(),"owner":"victim"}]}).status_code == 422
    assert c.put("/api/profile/interests/food.seafood",json={"action":"confirm"}).status_code == 200
    from app.user_profile import ProfileStore
    owner = c.get("/api/session").json()["user_id"]
    assert ProfileStore(lambda:store).current(owner)[0]["provenance"] == "user_supplied"
    assert rank(c)["results"][0]["reason"] == "Because you confirmed an interest in seafood"
    c.put("/api/profile/interests/food.seafood",json={"action":"reject"})
    assert ProfileStore(lambda:store).current(owner) == []


def test_concurrent_duplicate_observations_record_once(client):
    c,store = client
    rec.setup(store)
    owner = c.get("/api/session").json()["user_id"]
    recommender = rec.Recommender(store)
    with ThreadPoolExecutor(max_workers=4) as pool:
        counts = list(pool.map(lambda _:recommender.record(owner,[rec.Event(**event())]),range(8)))
    assert sum(counts) == 1
    assert recommender.interests(owner,"session-one")[0]["evidence_count"] == 1
