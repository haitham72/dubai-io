"""Prayer-times tests with a stubbed provider. Offline."""
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app import ml_rag, prayer


@pytest.fixture
def client():
    ml_rag._mem_cache.clear()
    try:  # a live local Redis would otherwise leak cached prayers across runs
        import redis
        from app.config import settings
        handle = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=1, socket_timeout=1)
        for key in handle.scan_iter("prayer:*"):
            handle.delete(key)
    except Exception:
        pass
    app = FastAPI()
    app.include_router(prayer.router)
    return TestClient(app)


class Resp:
    def raise_for_status(self):
        pass

    def json(self):
        return {"data": {"date": {"readable": "23 Oct 2026"},
                         "timings": {"Fajr": "05:10", "Sunrise": "06:30", "Dhuhr": "12:05", "Asr": "15:20",
                                     "Maghrib": "17:45", "Isha": "19:05", "Midnight": "23:55"}}}


def test_ok_and_cached(client, monkeypatch):
    calls = []

    def fake_get(*args, **kwargs):
        calls.append(1)
        return Resp()

    monkeypatch.setattr(prayer.httpx, "get", fake_get)
    first = client.get("/api/prayer-times").json()
    second = client.get("/api/prayer-times").json()
    assert first["status"] == "ok" and first["timings"]["Fajr"] == "05:10" and first["source"] == "Aladhan"
    assert len(calls) == 1 and second == first


def test_unavailable_without_raise(client, monkeypatch):
    def boom(*args, **kwargs):
        raise TimeoutError()

    monkeypatch.setattr(prayer.httpx, "get", boom)
    body = client.get("/api/prayer-times", params={"city": "Nowhere"}).json()
    assert body["status"] == "unavailable"
