"""Trusted retrieval, hard constraints, evolving preferences and provider failure."""
from fastapi.testclient import TestClient
import httpx
import pytest

from app import discovery, google_maps, recommendations as rec
from .test_recommendations import client, event, record


def place(pid, kind="restaurant", lat=25.081, open_now=True):
    return {"id":pid,"name":"Private listing "+pid,"type":kind,"types":[kind],"lat":lat,"lng":55.1403,
            "open_now":open_now,"provenance":"provider_confirmed"}


@pytest.fixture
def source(client,monkeypatch):
    c,store = client
    c.app.include_router(discovery.router)
    monkeypatch.setattr(discovery.settings,"google_key","test-not-a-secret")
    data = [place("bistro"),place("seafood","seafood_restaurant",lat=25.084),place("cafe","cafe",lat=25.082)]
    calls = []
    async def search(query,lat,lng,**options):
        calls.append((query,lat,lng,options))
        return {"places":data,"as_of":"2026-10-22T12:00:00+00:00"}
    monkeypatch.setattr(google_maps,"search_places",search)
    return c,store,data,calls


def discover(c,**kw):
    return c.post("/api/discovery/places",json={"session_id":"session-one","category":"food",**kw})


def test_live_candidates_adapt_with_visible_reason_without_persisting_listings(source):
    c,store,data,calls = source
    assert [p["id"] for p in discover(c).json()["places"]] == ["bistro","seafood"]
    record(c,event("g:fish-one"),event("g:fish-two"))
    response = discover(c)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-store"
    assert response.json()["places"][0]["id"] == "seafood"
    assert response.json()["places"][0]["recommendation"]["reason"] == "Because you explored seafood this visit"
    assert len(calls) == 2  # One provider batch for each deliberate request.
    saved = " ".join(r[0] for r in store.db.execute("SELECT results FROM recommendation_runs").fetchall())
    assert "Private listing" not in saved and "types" not in saved and "open_now" not in saved
    assert discover(c,sort="closest").json()["places"][0]["id"] == "bistro"
    assert discover(c,category="coffee").json()["places"][0]["id"] == "cafe"


def test_explicit_filters_exclude_closed_unknown_distant_and_unverified_types(source):
    c,store,data,calls = source
    data[:] = [place("closed","seafood_restaurant",open_now=False),place("unknown","seafood_restaurant",open_now=None),
               place("too-far","seafood_restaurant",lat=25.8),place("wrong-type"),place("right","seafood_restaurant"),
               {**place("missing-coordinates","seafood_restaurant"),"lat":None}]
    record(c,event("one"),event("two"))
    result = discover(c,subcategory="Seafood",open_now=True,radius_km=1).json()
    assert [p["id"] for p in result["places"]] == ["right"]
    assert result["excluded"] == {"distance_unknown":1,"outside_radius":1,"not_open":2,"type_unverified":1,"dismissed":0}


def test_dismissal_hides_only_that_item_for_seven_days_and_is_owner_scoped(source,monkeypatch):
    c,store,data,calls = source
    at = 1792500000.
    monkeypatch.setattr(rec,"clock",lambda:at)
    monkeypatch.setattr(discovery,"clock",lambda:at)
    record(c,event("g:bistro",kind="dismiss",topic="food.restaurants"))
    assert [p["id"] for p in discover(c).json()["places"]] == ["seafood"]
    assert c.get("/api/profile/interests").json()["interests"] == []
    other = TestClient(c.app)
    other.get("/api/session")
    assert discover(other).json()["places"][0]["id"] == "bistro"
    at += 7*rec.DAY+1
    assert discover(c).json()["places"][0]["id"] == "bistro"


def test_item_dismissal_still_works_when_topic_learning_is_paused(source):
    c,store,data,calls = source
    c.put("/api/profile/interests/food.restaurants",json={"action":"forget"})
    record(c,event("g:bistro",kind="dismiss",topic="food.restaurants"))
    assert all(p["id"] != "bistro" for p in discover(c).json()["places"])
    rows = c.get("/api/profile/interests").json()["interests"]
    assert rows[0]["learning_state"] == "paused" and rows[0]["evidence"] == []


def test_variety_is_deterministic_and_never_bypasses_constraints(source):
    c,store,data,calls = source
    data[:] = [place("bistro")] + [place("fish"+str(n),"seafood_restaurant",lat=25.083+n*.0001) for n in range(6)]
    record(c,event("one"),event("two"))
    first = discover(c).json()["places"]
    second = discover(c).json()["places"]
    assert [p["id"] for p in first] == [p["id"] for p in second]
    assert first[4]["id"] == "bistro" and first[4]["recommendation"]["variety"]
    assert all(p["id"] != "bistro" for p in discover(c,subcategory="Seafood").json()["places"])


def test_correction_during_provider_wait_is_applied_before_scoring(source,monkeypatch):
    c,store,data,calls = source
    owner = c.get("/api/session").json()["user_id"]
    record(c,event("one"),event("two"))
    async def correcting(*args,**kwargs):
        rec.Recommender(store).control(owner,"food.seafood","forget")
        return {"places":data,"as_of":"2026-10-22T12:00:00+00:00"}
    monkeypatch.setattr(google_maps,"search_places",correcting)
    result = discover(c).json()
    assert result["places"][0]["id"] == "bistro"
    assert all(not p["recommendation"]["reason"] for p in result["places"])


def test_provider_timeout_is_honest_and_unauthenticated_call_does_not_reach_provider(source,monkeypatch):
    c,store,data,calls = source
    async def failed(*args,**kwargs):
        raise httpx.ReadTimeout("simulated provider failure")
    monkeypatch.setattr(google_maps,"search_places",failed)
    assert discover(TestClient(c.app)).status_code == 401
    response = discover(c)
    assert response.status_code == 502 and "unavailable" in response.json()["detail"]
    assert store.db.execute("SELECT COUNT(*) FROM recommendation_runs").fetchone()[0] == 0


@pytest.mark.parametrize("extra",[{"candidates":[]},{"budget_aed":50},{"date":"2026-11-01"},{"owner":"other"},
                                  {"category":"coffee","subcategory":"Seafood"},{"lat":91},{"radius_km":100}])
def test_unsupported_or_tampered_claims_are_rejected_before_retrieval(source,extra):
    c,store,data,calls = source
    assert discover(c,**extra).status_code == 422
    assert calls == []
