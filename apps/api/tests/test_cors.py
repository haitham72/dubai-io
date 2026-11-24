"""E9a: the Dubai-io website (Expo web :8081) may call apps/api; nobody else may."""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.cors import install_cors, web_origins
from app.main import app as main_app


def _preflight(client, origin, method="POST", headers="content-type,x-app-session"):
    return client.options(
        "/api/health",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": method,
            "Access-Control-Request-Headers": headers,
        },
    )


def test_preflight_from_expo_web_origin_succeeds():
    r = _preflight(TestClient(main_app), "http://localhost:8081")
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == "http://localhost:8081"
    assert "x-app-session" in r.headers["access-control-allow-headers"].lower()
    assert r.headers["access-control-allow-origin"] != "*"


def test_preflight_from_disallowed_origin_gets_no_allow_origin():
    c = TestClient(main_app)
    for origin in ("http://evil.example", "http://localhost:9999"):
        r = _preflight(c, origin)
        assert "access-control-allow-origin" not in r.headers
    r = c.get("/api/health", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in r.headers


def test_extra_origins_from_env_and_no_wildcard(monkeypatch):
    monkeypatch.setenv("PUBLIC_WEB_ORIGINS", "http://192.168.1.20:8081/, *,http://127.0.0.1:8081")
    origins = web_origins()
    assert "http://192.168.1.20:8081" in origins
    assert "*" not in origins
    assert origins.count("http://127.0.0.1:8081") == 1
    app = FastAPI()
    install_cors(app)

    @app.get("/x")
    def x():
        return {}

    c = TestClient(app)
    ok = _preflight(c, "http://192.168.1.20:8081")
    assert ok.headers["access-control-allow-origin"] == "http://192.168.1.20:8081"
    assert "access-control-allow-origin" not in _preflight(c, "http://192.168.1.21:8081").headers


def test_disallowed_method_rejected():
    r = _preflight(TestClient(main_app), "http://localhost:8081", method="TRACE")
    assert r.status_code == 400
