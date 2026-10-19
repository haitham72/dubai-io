"""Unconfigured OAuth must never create connections, redirects or tokens."""
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.auth import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def test_connections_are_truthfully_unconfigured():
    response = client.get("/api/auth/connections")
    assert response.status_code == 200
    assert response.json() == {"providers": [{
        "id": "google", "label": "Google", "status": "not_configured",
        "can_connect": False, "scopes": ["openid", "email", "profile"],
        "account_label": None,
    }]}


def test_start_fails_closed_without_redirect_or_cookie():
    response = client.get("/api/auth/google/start", follow_redirects=False)
    assert response.status_code == 503
    assert "location" not in response.headers
    assert "set-cookie" not in response.headers


def test_unregistered_provider_is_rejected():
    assert client.get("/api/auth/unknown/start").status_code == 404
