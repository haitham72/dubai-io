from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
import httpx
import pytest

from app import actions, reading, recommendations
from app.actions import ActionEngine, ActionStore


@pytest.fixture
def client(tmp_path, monkeypatch):
    store = ActionStore(tmp_path / "reading.sqlite3")
    monkeypatch.setattr(actions, "_engine", ActionEngine(store))
    reading._cache.clear(); reading._recent.clear()
    app = FastAPI()
    for router in (actions.router, recommendations.router, reading.router):
        app.include_router(router)
    c = TestClient(app); c.get("/api/session")
    yield c, store
    store.db.close()


def article(at=None, **kw):
    return {"title": "Dubai culture update", "url": "https://www.thenationalnews.com/uae/culture?utm_source=test#part",
            "published_date": (at or datetime.now(timezone.utc)).isoformat(), **kw}


def test_owner_and_topic_guard_before_network(client, monkeypatch):
    c, _ = client
    monkeypatch.setattr(reading, "fetch_headlines", lambda *_: pytest.fail("No network"))
    assert TestClient(c.app).get("/api/reading").status_code == 401
    assert c.get("/api/reading?topic=private-chat-text").status_code == 422


def test_only_admitted_https_dated_deduplicated_metadata_survives():
    at = datetime.now(timezone.utc)
    hits = [article(), article(url="https://www.thenationalnews.com/uae/culture?utm_source=other"),
            article(url="https://thenationalnews.com.evil.test/x", title="Bad host"),
            article(url="https://user:secret@thenationalnews.com/x", title="Credentials"),
            article(url="http://thenationalnews.com/x", title="HTTP"),
            article(url="https://thenationalnews.com/old", title="Old", at=at-timedelta(days=30)),
            article(url="https://thenationalnews.com/undated", title="Undated", published_date=None),
            article(url="https://thenationalnews.com/future", title="Future", at=at+timedelta(days=2))]
    rows = reading.headlines(hits, reading.PUBLISHERS, at)
    assert len(rows) == 1 and rows[0]["url"] == "https://www.thenationalnews.com/uae/culture"
    assert rows[0]["date_basis"] == "search_provider_reported"
    assert "content" not in rows[0] and "image" not in rows[0]


def test_fetch_uses_existing_key_public_topic_and_no_full_article_content(monkeypatch):
    monkeypatch.setenv("TVLY_API_KEY", "synthetic-test-key")
    seen = []
    def post(url, **kw):
        seen.append(kw["json"])
        return httpx.Response(200, json={"results": [article(content="Never retained", raw_content="Never retained")]}, request=httpx.Request("POST", url))
    monkeypatch.setattr(reading.httpx, "post", post)
    rows = reading.fetch_headlines(["arts"], reading.PUBLISHERS)
    body = seen[0]
    assert body["topic"] == "news" and body["query"] == reading.QUERIES["arts"]
    assert not body["include_raw_content"] and not body["include_images"] and not body["include_answer"]
    assert rows and "content" not in rows[0]


def test_short_cache_failure_and_owner_specific_relevance(client, monkeypatch):
    c, _ = client
    calls = []
    def fetch(topics, sources):
        calls.append(topics)
        return reading.headlines([article()], sources, datetime.now(timezone.utc))
    monkeypatch.setattr(reading, "fetch_headlines", fetch)
    one = c.get("/api/reading?topic=arts")
    assert one.status_code == 200 and one.headers["cache-control"] == "private, no-store"
    assert one.json()["articles"] and "selected Arts" in one.json()["reason"]
    assert not one.json()["polling"]
    assert c.get("/api/reading?topic=arts").json()["articles"] == one.json()["articles"]
    assert len(calls) == 1
    other = TestClient(c.app); other.get("/api/session")
    assert "general Dubai" in other.get("/api/reading").json()["reason"]
    monkeypatch.setattr(reading, "fetch_headlines", lambda *_: (_ for _ in ()).throw(RuntimeError("offline")))
    failed = c.get("/api/reading?topic=technology").json()
    assert failed["status"] == "unavailable" and failed["articles"] == []


def test_for_you_never_promotes_unqualified_long_term_or_negative_or_forgotten_interests():
    class Rec:
        rows = []
        def interests(self, *_): return self.rows
    rec = Rec()
    rec.rows = [{"topic":"food.restaurants","status":"active","learning_state":"learning","signal":.7}]
    assert reading.selection(rec,"owner","visit","for_you")[0] == ["dubai"]
    rec.rows[0].update(learning_state="ready", signal=-.5)
    assert reading.selection(rec,"owner","visit","for_you")[0] == ["dubai"]
    rec.rows[0].update(status="forgotten", learning_state="paused", signal=.7)
    assert reading.selection(rec,"owner","visit","for_you")[0] == ["dubai"]
    rec.rows[0].update(status="confirmed", learning_state="confirmed", signal=0)
    topics, reason, provenance = reading.selection(rec,"owner","visit","for_you")
    assert topics == ["food"] and provenance == "user_supplied" and "confirmed" in reason


def test_midflight_preference_change_drops_old_feed(client, monkeypatch):
    c, _ = client
    original = reading.selection
    calls = []
    def choose(*args):
        calls.append(1)
        return (["arts"], "Because of your confirmed interests", "user_supplied") if len(calls) == 1 else original(*args)
    monkeypatch.setattr(reading,"selection",choose)
    monkeypatch.setattr(reading,"fetch_headlines",lambda *args: reading.headlines([article()],reading.PUBLISHERS,datetime.now(timezone.utc)))
    result = c.get("/api/reading").json()
    assert result["status"] == "preferences_changed" and result["articles"] == []
