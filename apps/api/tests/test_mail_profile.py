import os

from fastapi.testclient import TestClient

from app import main


def test_mail_needs_reply_demo(monkeypatch):
    monkeypatch.setenv("DEMO_MAIL", "1")
    client = TestClient(main.app)
    assert client.get("/api/session").status_code == 200
    r = client.get("/api/mail/needs-reply")
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "demo"
    assert body["items"][0]["title"].startswith("IDC Technologies")
    assert body["items"][0]["demo"] is True


def test_mail_status_blocker_without_oauth(monkeypatch):
    monkeypatch.delenv("DEMO_MAIL", raising=False)
    client = TestClient(main.app)
    assert client.get("/api/session").status_code == 200
    r = client.get("/api/mail/status")
    assert r.status_code == 200
    assert r.json()["oauth_configured"] is False
    assert "blocker" in r.json()
