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
    assert "Because you explored seafood this visit" == result["results"][0]["reason"]
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


def test_edit_is_explicit_durable_and_does_not_transfer_evidence(client):
    from app.user_profile import ProfileStore
    c,store = client
    owner = c.get("/api/session").json()["user_id"]
    c.put("/api/profile/interests/food.restaurants",json={"action":"confirm"})
    record(c,event("old-item",topic="food.restaurants"),event("new-item",topic="food.seafood"))
    rank(c)
    response = c.put("/api/profile/interests/food.restaurants",json={"action":"edit","replacement_topic":"food.seafood"})
    assert response.status_code == 200
    reopened = TestClient(c.app)
    reopened.cookies.update(c.cookies)
    rows = reopened.get("/api/profile/interests?session_id=session-one").json()["interests"]
    old = next(r for r in rows if r["topic"] == "food.restaurants")
    new = next(r for r in rows if r["topic"] == "food.seafood")
    assert old["status"] == "forgotten" and old["learning_state"] == "paused"
    assert new["status"] == "confirmed" and new["provenance"] == "user_supplied"
    assert new["evidence_count"] == 0 and new["evidence"] == []
    assert record(c,event("old-again",topic="food.restaurants")) == 0
    assert store.db.execute("SELECT COUNT(*) FROM recommendation_runs WHERE owner=?",(owner,)).fetchone()[0] == 0
    facts = ProfileStore(lambda:store).current(owner)
    assert [(f["key"],f["value"],f["status"]) for f in facts] == [("interest:food.seafood","seafood","confirmed")]
    assert rank(c)["results"][0]["reason"] == "Because you confirmed an interest in seafood"


def test_edit_and_evidence_do_not_affect_another_owner(client):
    c,store = client
    other = TestClient(c.app)
    other.get("/api/session")
    record(other,event("other-private-item",topic="food.restaurants"))
    record(c,event("own-item",topic="food.restaurants"))
    c.put("/api/profile/interests/food.restaurants",json={"action":"edit","replacement_topic":"food.seafood"})
    mine = c.get("/api/profile/interests").json()
    theirs = other.get("/api/profile/interests").json()
    assert "other-private-item" not in str(mine)
    assert theirs["interests"][0]["topic"] == "food.restaurants"
    assert theirs["interests"][0]["evidence"][0]["entity_id"] == "other-private-item"


@pytest.mark.parametrize("body",[
    {"action":"edit"},
    {"action":"edit","replacement_topic":"health.condition"},
    {"action":"edit","replacement_topic":"food.restaurants"},
    {"action":"confirm","replacement_topic":"food.seafood"},
])
def test_invalid_edits_do_not_purge_conversation_or_profile(client,monkeypatch,body):
    from app.luna import graph as luna
    c,_ = client
    record(c,event("own-item",topic="food.restaurants"))
    monkeypatch.setattr(luna,"clear_conversation",lambda _:pytest.fail("Invalid edit purged history"))
    assert c.put("/api/profile/interests/food.restaurants",json=body).status_code == 422
    assert c.put("/api/profile/interests/unknown",json={"action":"forget"}).status_code == 404
    assert c.get("/api/profile/interests").json()["interests"][0]["evidence_count"] == 1


def test_edit_rolls_back_projection_and_canonical_fact_together(client,monkeypatch):
    from app.user_profile import ProfileStore
    c,store = client
    owner = c.get("/api/session").json()["user_id"]
    c.put("/api/profile/interests/food.restaurants",json={"action":"confirm"})
    record(c,event("old-item",topic="food.restaurants"))
    rank(c)
    original_add = ProfileStore.add
    def fail_after_fact_write(self,*args,**kwargs):
        original_add(self,*args,**kwargs)
        raise RuntimeError("Injected storage failure")
    monkeypatch.setattr(ProfileStore,"add",fail_after_fact_write)
    with pytest.raises(RuntimeError,match="Injected storage failure"):
        c.put("/api/profile/interests/food.restaurants",json={"action":"edit","replacement_topic":"food.seafood"})
    rows = c.get("/api/profile/interests").json()["interests"]
    assert [(r["topic"],r["status"]) for r in rows] == [("food.restaurants","confirmed")]
    assert ProfileStore(lambda:store).current(owner)[0]["key"] == "interest:food.restaurants"
    assert store.db.execute("SELECT COUNT(*) FROM recommendation_events WHERE owner=?",(owner,)).fetchone()[0] == 1
    assert store.db.execute("SELECT COUNT(*) FROM recommendation_runs WHERE owner=?",(owner,)).fetchone()[0] == 1


def test_evidence_shows_visit_scope_dates_and_bounded_recent_observations(client,monkeypatch):
    c,_ = client
    at = 1792500000.
    monkeypatch.setattr(rec,"clock",lambda:at)
    for n in range(7):
        record(c,event("g:item-"+str(n),session="session-one" if n < 3 else "session-two"))
        at += 1
    rows = c.get("/api/profile/interests?session_id=session-one").json()["interests"]
    session = next(r for r in rows if r["scope"] == "session")
    long = next(r for r in rows if r["scope"] == "long_term")
    assert session["evidence_count"] == 3 and long["evidence_count"] == 7
    assert len(long["evidence"]) == 5 and len(session["evidence"]) == 3
    assert all(e["entity_id"] in {"g:item-0","g:item-1","g:item-2"} for e in session["evidence"])
    assert all(e["at"].endswith("+00:00") and e["kind"] == "detail" for e in long["evidence"])
    assert session["half_life_seconds"] == 1800 and long["half_life_seconds"] == 30*rec.DAY
    assert session["expires_at"] < long["expires_at"]
    assert session["learning_state"] == "ready"


@pytest.mark.parametrize("kinds",[
    ["category","detail","choose","save"],
    ["save","choose","detail","category"],
])
def test_reclassifying_one_item_is_capped_at_its_strongest_signal(client,kinds):
    c,store = client
    record(c,*(event("same-item",kind=k,key="kind-key-"+k) for k in kinds))
    record(c,*(event("same-item",kind=k,key="replay-key-"+k) for k in kinds))
    assert store.db.execute("SELECT SUM(weight) FROM recommendation_events").fetchone()[0] == 1.5
    rows = c.get("/api/profile/interests").json()["interests"]
    assert rows[0]["evidence_count"] == 1
    assert rank(c)["results"][0]["reason"] is None


def test_projection_rebuild_reconciles_old_weights_without_discarding_evidence(client):
    c,store = client
    record(c,*(event("same-item",kind=k,key="old-event-"+k) for k in ["category","detail","choose","save"]))
    for kind,weight in rec.WEIGHTS.items():
        store.db.execute("UPDATE recommendation_events SET weight=? WHERE kind=?",(weight,kind))
    store.db.execute("UPDATE profile_interests SET positive=100")
    store.db.commit()
    assert rec.Recommender(store).rebuild() == 1
    assert store.db.execute("SELECT COUNT(*) FROM recommendation_events").fetchone()[0] == 4
    assert store.db.execute("SELECT SUM(weight) FROM recommendation_events").fetchone()[0] == 1.5
    assert c.get("/api/profile/interests").json()["interests"][0]["evidence_count"] == 1


def test_failed_ingestion_does_not_leave_half_written_evidence(client,monkeypatch):
    c,store = client
    def fail(*args):
        raise RuntimeError("Injected projection failure")
    monkeypatch.setattr(rec.Recommender,"_rebuild_topic",fail)
    with pytest.raises(RuntimeError,match="Injected projection failure"):
        record(c,event())
    assert store.db.execute("SELECT COUNT(*) FROM recommendation_events").fetchone()[0] == 0


def test_one_visit_or_simultaneous_tabs_cannot_establish_long_term_taste(client,monkeypatch):
    c,_ = client
    at = 1792500000.
    monkeypatch.setattr(rec,"clock",lambda:at)
    record(c,event("fish-one"),event("fish-two"),event("fish-three",session="parallel-tab"))
    rows = c.get("/api/profile/interests?session_id=session-one").json()["interests"]
    assert next(r for r in rows if r["scope"] == "session")["learning_state"] == "ready"
    long = next(r for r in rows if r["scope"] == "long_term")
    assert long["visit_count"] == 2 and long["learning_state"] == "learning"
    assert rank(c,session_id="new-unrelated-visit")["results"][0]["id"] == "coffee"
    at += rec.DAY+1
    assert rank(c)["results"][0]["id"] == "coffee"


def test_repeated_separated_visits_qualify_then_fade_and_expire(client,monkeypatch):
    c,_ = client
    at = 1792500000.
    monkeypatch.setattr(rec,"clock",lambda:at)
    record(c,event("fish-one"))
    at += rec.LONG_TERM_VISIT_GAP
    record(c,event("fish-two",session="second-visit"))
    result = rank(c,session_id="third-visit")
    assert result["results"][0]["id"] == "fish"
    assert result["results"][0]["reason"] == "Because you explored seafood across visits"
    at += 30*rec.DAY
    faded = rank(c,session_id="third-visit")["results"]
    assert next(r for r in faded if r["id"] == "fish")["influence"] < result["results"][0]["influence"]
    at += 61*rec.DAY
    assert rank(c,session_id="third-visit")["results"][0]["id"] == "coffee"


def test_recent_negative_feedback_can_reverse_inferred_influence(client):
    c,_ = client
    record(c,event("positive-one"),event("positive-two"))
    assert rank(c)["results"][0]["id"] == "fish"
    record(c,event("negative-one",kind="less_like_this"),event("negative-two",kind="less_like_this"))
    result = rank(c)["results"]
    fish = next(r for r in result if r["id"] == "fish")
    assert result[0]["id"] == "coffee"
    assert fish["influence"] < 0 and "fewer seafood" in fish["reason"]


def test_category_taps_alone_are_not_distinct_option_evidence(client):
    c,_ = client
    record(c,event("category-food",kind="category"),event("category-seafood",kind="category"))
    assert all(r["evidence_count"] == 0 for r in c.get("/api/profile/interests").json()["interests"])
    assert rank(c)["results"][0]["reason"] is None


def test_explicit_intent_is_eligibility_even_against_confirmed_history(client):
    c,_ = client
    c.put("/api/profile/interests/food.seafood",json={"action":"confirm"})
    record(c,event("one",kind="save"),event("two",kind="save"))
    assert [r["id"] for r in rank(c,intent="food.cafes")["results"]] == ["coffee"]
