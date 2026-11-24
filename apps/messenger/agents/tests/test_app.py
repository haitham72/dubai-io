"""HTTP + WebSocket surface with fakes and an in-memory store (no Redis, no network)."""
import json
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from messenger_agents.app import Services, build_app
from messenger_agents.config import Settings
from messenger_agents.store import MemoryStore


@pytest.fixture
def client(tmp_path):
    cfg = replace(Settings(), live=False, watch_enabled=False, data_dir=tmp_path, budget_usd=1.0,
                  gmail_client_file=tmp_path / "none.json", gmail_token_file=tmp_path / "token.json")
    with TestClient(build_app(Services(cfg, MemoryStore()))) as c:
        yield c


def test_health_reports_offline_mode(client):
    h = client.get("/agents/health").json()
    assert h["live"] == {"decisions": False, "stt": False, "research": False} and h["mail"]["mode"] == "demo"


def test_voice_socket_streams_events(client, contacts):
    with client.websocket_connect("/agents/voice?sid=t") as ws:
        ws.send_text(json.dumps({"type": "start", "contacts": [c.__dict__ for c in contacts], "audio": False}))
        assert json.loads(ws.receive_text())["type"] == "ready"
        ws.send_text(json.dumps({"type": "text", "text": "text Mazen I'm on my way"}))
        ws.send_text(json.dumps({"type": "end"}))
        msgs = []
        while not msgs or msgs[-1]["type"] != "done":
            msgs.append(json.loads(ws.receive_text()))
    undo = next(m for m in msgs if m["type"] == "undo")
    assert undo["args"]["contactId"] == "mazen" and undo["undoMs"] == 3000


def test_research_and_watchlist(client):
    r = client.post("/agents/research", json={"topic": "best new supercars this week"}).json()
    assert r["mode"] == "demo" and r["sources"] and r["findings"]
    topics = {w["id"] for w in client.get("/agents/watch").json()}
    assert topics == {"phones", "supercars"}
    assert client.post("/agents/watch/supercars/refresh").json()["watch"] == "supercars"


def test_mail_demo_mode_and_send_needs_confirmation(client):
    assert client.get("/agents/mail/messages").json() == {"mode": "demo", "messages": []}
    assert client.post("/agents/mail/send", json={"to": "a@b.co", "subject": "s", "body": "b"}).status_code == 428


def test_memory_facts_round_trip(client):
    client.put("/agents/memory/facts", json={"facts": ["Prefers aisle seats", " "]})
    assert client.get("/agents/memory/facts").json() == {"facts": ["Prefers aisle seats"]}
