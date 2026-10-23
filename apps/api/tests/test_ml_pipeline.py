"""ML pipeline tests: analysis labels, hybrid search,Broker fallback. Offline.

A deterministic fake backend stands in for the Faz3 models; no weights are
downloaded and no broker is required (except the guarded fallback test).
"""
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app import actions, communities, ml_api, ml_models, ml_rag, ml_tasks
from app.actions import ActionEngine, ActionStore


class FakeBackend:
    available = True
    TOPICS = {"rent_housing": {"rent", "landlord", "deposit", "apartment", "lease"},
              "jobs_hiring": {"interview", "salary", "job", "hiring", "offer"},
              "food_dining": {"shawarma", "restaurant", "food", "dinner", "cafe"}}
    HARSH = {"terrible", "awful", "hate", "worst", "scam"}

    def analyze(self, text):
        words = set(ml_rag.tokenize(text))
        neg = 0.9 if words & self.HARSH else (0.4 if "bad" in words else 0.05)
        topics = [{"topic": t, "score": round(len(words & ks) / len(ks), 4)}
                  for t, ks in self.TOPICS.items() if words & ks][:2]
        sentiment = "negative" if neg >= 0.8 else ("neutral" if neg >= 0.2 else "positive")
        return {"available": True, "sentiment": sentiment, "neg": neg, "neu": 0.1, "pos": 0.05,
                "topics": topics, "harsh": neg >= 0.8, "harsh_basis": "sentiment_negative",
                "model": "fake"}

    def embed(self, texts):
        vecs = []
        for text in texts:
            words = set(ml_rag.tokenize(text))
            vec = [float(len(words & ks) or 0.01) for ks in self.TOPICS.values()]
            norm = sum(vec) or 1.0
            vecs.append([v / norm for v in vec])
        return vecs


class Unavailable:
    available = False

    def analyze(self, text):
        return {"available": False}

    def embed(self, texts):
        return None


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(communities.social.settings, "nararouter_api_key", "")
    monkeypatch.setattr(ml_tasks.settings, "ml_eager", True)
    ml_models.set_backend(FakeBackend())
    store = ActionStore(tmp_path / "ml.sqlite3")
    monkeypatch.setattr(actions, "_engine", ActionEngine(store))
    app = FastAPI()
    for router in (actions.router, communities.router, ml_api.router):
        app.include_router(router)
    c = TestClient(app)
    c.get("/api/session")
    yield c, store
    ml_models.set_backend(None)
    store.db.close()


def _post_and_comment(c, text):
    c.post("/api/communities/marina-foodies/join")
    post = c.post("/api/communities/marina-foodies/posts", json={"text": "hello"}).json()
    return c.post(f"/api/posts/{post['id']}/comments", json={"text": text}).json()["id"]


def test_comment_analysis_is_stored_and_served(client):
    c, store = client
    cid = _post_and_comment(c, "terrible landlord raised the rent again")
    row = store.db.execute("SELECT sentiment,harsh,topics FROM comment_labels WHERE comment_id=?", (cid,)).fetchone()
    assert row[0] == "negative" and row[1] == 1 and "rent_housing" in row[2]
    assert store.db.execute("SELECT dim FROM comment_embeddings WHERE comment_id=?", (cid,)).fetchone()[0] == 3
    post_id = store.db.execute("SELECT post_id FROM comments WHERE id=?", (cid,)).fetchone()[0]
    comments = c.get(f"/api/posts/{post_id}/comments").json()["comments"]
    mine = next(m for m in comments if m["id"] == cid)
    assert mine["analysis"]["sentiment"] == "negative" and mine["analysis"]["harsh"] is True


def test_unavailable_backend_leaves_analysis_null(client):
    c, store = client
    ml_models.set_backend(Unavailable())
    cid = _post_and_comment(c, "terrible landlord raised the rent again")
    assert store.db.execute("SELECT 1 FROM comment_labels WHERE comment_id=?", (cid,)).fetchone() is None
    post_id = store.db.execute("SELECT post_id FROM comments WHERE id=?", (cid,)).fetchone()[0]
    comments = c.get(f"/api/posts/{post_id}/comments").json()["comments"]
    assert next(m for m in comments if m["id"] == cid)["analysis"] is None


def test_hybrid_search_ranks_relevant_first(client):
    c, _ = client
    _post_and_comment(c, "my landlord raised the rent, deposit dispute ongoing")
    _post_and_comment(c, "interview went well, salary offer accepted")
    _post_and_comment(c, "best shawarma near the metro station")
    found = c.get("/api/community/search", params={"q": "apartment rent deposit"}).json()
    assert found["method"] == "hybrid" and found["semantic"] is True
    assert "rent" in found["results"][0]["text"] and found["results"][0]["provenance"] == "user_supplied"


def test_search_degrades_to_keyword_without_embeddings(client):
    c, store = client
    _post_and_comment(c, "my landlord raised the rent, deposit dispute ongoing")

    class NoEmbed(FakeBackend):
        def embed(self, texts):
            return None

    ml_models.set_backend(NoEmbed())
    ml_rag._mem_cache.clear()
    found = c.get("/api/community/search", params={"q": "landlord rent"}).json()
    assert found["method"] == "keyword" and found["semantic"] is False
    assert found["results"] and "rent" in found["results"][0]["text"]


def test_search_rejects_blank_query(client):
    assert client[0].get("/api/community/search", params={"q": "  "}).status_code == 400


def test_ml_status_reports_models_without_secrets(client):
    body = client[0].get("/api/ml/status").json()
    assert body["models"]["sentiment"].startswith("cardiffnlp/")
    assert body["models"]["embeddings"].startswith("sentence-transformers/")
    assert "guest:guest" not in json.dumps(body) and body["eager"] is True


def test_rrf_prefers_top_ranks():
    assert ml_rag.rrf(1) > ml_rag.rrf(2) > ml_rag.rrf(10) > 0


def test_broker_failure_falls_back_to_inline(client, monkeypatch):
    pytest.importorskip("celery")
    c, store = client
    monkeypatch.setattr(ml_tasks.settings, "ml_eager", False)
    monkeypatch.setattr(ml_tasks.settings, "rabbitmq_url", "amqp://guest:guest@localhost:5999//")
    cid = _post_and_comment(c, "rent discussion")
    assert store.db.execute("SELECT sentiment FROM comment_labels WHERE comment_id=?", (cid,)).fetchone() is not None
