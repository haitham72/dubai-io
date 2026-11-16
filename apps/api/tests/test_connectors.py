"""Connector framework: registry honesty, sync, dedupe, retry, isolation, outbound gate."""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest
from cryptography.fernet import Fernet

from app.connectors.catalog import catalog
from app.connectors.hosts import public_https_origin
from app.connectors.plugins.imap_source import parse_imap_fetch
from app.connectors.plugins.whatsapp_evolution import instance_name, normalize_evolution_message
from app.connectors.registry import build_implementations
from app.connectors.schema import DDL, ensure_connector_schema
from app.connectors.service import ConnectorService
from app.connectors.store import ConnectorStore
from app.connectors.types import AuthFailed, DisabledConnector, PermanentFailure, PermissionDenied, UnavailableConnector
from app.db import connect

NOW = "2026-11-14T00:00:00+00:00"
ROOT = Path(__file__).resolve().parents[1]


def _service(tmp_path, transport=None, clock=None):
    db = connect(tmp_path / "connectors.db")
    store = ConnectorStore(db, key=Fernet.generate_key())
    service = ConnectorService(store, clock=clock or (lambda: NOW), transport=transport)
    return service, store, db


def _seed(store, owner, connector_id, credentials):
    store.save_credentials(owner, connector_id, credentials, NOW)
    store.upsert_connection(owner, connector_id, status="connected", health="unknown", updated_at=NOW, connected_at=NOW)


def _scripted(sequence):
    def handler(request: httpx.Request):
        url = str(request.url)
        if "/dm" in request.url.path or "download" in request.url.path or "alt=media" in url:
            raise AssertionError(f"content or DM fetch was not requested: {request.url.path}")
        if not sequence:
            raise AssertionError(f"unexpected {request.method} {url}")
        method, needle, status, body = sequence.pop(0)
        if request.method != method or needle not in url:
            raise AssertionError(f"want {method} {needle} got {request.method} {url}")
        headers = {}
        if status == 429:
            headers["Retry-After"] = "3"
        return httpx.Response(status, json=body, headers=headers)

    return httpx.MockTransport(handler)


CASES = {
    "gmail": {
        "credentials": {"access_token": "gmail-token"},
        "sequence": [
            ("GET", "/messages", 200, {"messages": [{"id": "m1"}]}),
            ("GET", "/messages/m1", 200, {
                "id": "m1",
                "snippet": "interview tomorrow",
                "internalDate": "1730000000000",
                "payload": {
                    "headers": [
                        {"name": "Subject", "value": "Interview"},
                        {"name": "From", "value": "hr@example.com"},
                        {"name": "Date", "value": "Fri, 14 Nov 2026 09:00:00 +0400"},
                    ],
                    "parts": [{"filename": "cv.pdf", "mimeType": "application/pdf"}],
                },
            }),
            ("GET", "/profile", 200, {"emailAddress": "a@b.c", "historyId": "10"}),
        ],
        "source_id": "m1",
        "timestamp": "Fri, 14 Nov 2026 09:00:00 +0400",
        "text": "interview tomorrow",
    },
    "google_calendar": {
        "credentials": {"access_token": "cal-token"},
        "sequence": [("GET", "/calendars/primary/events", 200, {
            "items": [{"id": "e1", "summary": "KHDA", "start": {"dateTime": "2026-11-15T09:00:00+04:00"}, "updated": "2026-11-01T00:00:00Z"}],
            "nextSyncToken": "sync1",
        })],
        "source_id": "e1",
        "timestamp": "2026-11-15T09:00:00+04:00",
        "text": "KHDA",
    },
    "google_drive": {
        "credentials": {"access_token": "drive-token"},
        "sequence": [("GET", "/drive/v3/files", 200, {"files": [{
            "id": "f1", "name": "lease.pdf", "modifiedTime": "2026-10-01T00:00:00.000Z", "mimeType": "application/pdf", "size": "10",
        }]})],
        "source_id": "f1",
        "timestamp": "2026-10-01T00:00:00.000Z",
        "text": "lease.pdf",
    },
    "youtube": {
        "credentials": {"access_token": "yt-token"},
        "sequence": [
            ("GET", "/youtube/v3/channels", 200, {"items": [{"contentDetails": {"relatedPlaylists": {"uploads": "UU1"}}}]}),
            ("GET", "/playlistItems", 200, {"items": [{"snippet": {
                "title": "Walk", "description": "marina", "publishedAt": "2026-11-01T00:00:00Z", "resourceId": {"videoId": "vid1"},
            }}]}),
        ],
        "source_id": "vid1",
        "timestamp": "2026-11-01T00:00:00Z",
        "text": "marina",
    },
    "outlook": {
        "credentials": {"access_token": "ol-token"},
        "sequence": [("GET", "/messages/delta", 200, {"value": [{
            "id": "msg1", "subject": "Visa", "receivedDateTime": "2026-11-02T00:00:00Z", "bodyPreview": "slot",
            "from": {"emailAddress": {"address": "rta@example.com"}},
        }], "@odata.deltaLink": "https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages/delta?$deltatoken=abc"})],
        "source_id": "msg1",
        "timestamp": "2026-11-02T00:00:00Z",
        "text": "slot",
    },
    "outlook_calendar": {
        "credentials": {"access_token": "olc-token"},
        "sequence": [("GET", "/events/delta", 200, {"value": [{
            "id": "ev1", "subject": "School", "start": {"dateTime": "2026-11-16T08:00:00.0000000"}, "bodyPreview": "",
        }]})],
        "source_id": "ev1",
        "timestamp": "2026-11-16T08:00:00.0000000",
        "text": "School",
    },
    "onedrive": {
        "credentials": {"access_token": "od-token"},
        "sequence": [("GET", "/drive/root/children", 200, {"value": [{
            "id": "od1", "name": "contract.docx", "lastModifiedDateTime": "2026-10-02T00:00:00Z", "size": 4,
            "file": {"mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
        }]})],
        "source_id": "od1",
        "timestamp": "2026-10-02T00:00:00Z",
        "text": "contract.docx",
    },
    "github": {
        "credentials": {"token": "gh-token"},
        "sequence": [("GET", "/notifications", 200, [{
            "id": "n1", "updated_at": "2026-11-01T00:00:00Z", "subject": {"title": "Review the PR"},
            "repository": {"full_name": "haitham72/dubai-io"},
        }])],
        "source_id": "n1",
        "timestamp": "2026-11-01T00:00:00Z",
        "text": "Review the PR",
    },
    "gitlab": {
        "credentials": {"token": "gl-token"},
        "sequence": [("GET", "/api/v4/events", 200, [{
            "id": 5, "created_at": "2026-11-03T00:00:00Z", "action_name": "opened", "target_title": "Fix gate",
        }])],
        "source_id": "5",
        "timestamp": "2026-11-03T00:00:00Z",
        "text": "Fix gate",
    },
    "jira": {
        "credentials": {"site": "https://acme.atlassian.net", "email": "a@b.c", "api_token": "jira-token"},
        "sequence": [("GET", "/rest/api/3/search/jql", 200, {"issues": [{
            "id": "100", "key": "DXB-1", "fields": {"summary": "Visa", "updated": "2026-11-02T00:00:00.000+0000", "status": {"name": "Open"}},
        }]})],
        "source_id": "DXB-1",
        "timestamp": "2026-11-02T00:00:00.000+0000",
        "text": "Visa",
    },
    "slack": {
        "credentials": {"token": "slack-token"},
        "sequence": [
            ("GET", "/conversations.list", 200, {"ok": True, "channels": [{"id": "C1"}]}),
            ("GET", "/conversations.history", 200, {"ok": True, "messages": [{"ts": "1730000000.000100", "text": "stand-up", "user": "U1"}]}),
        ],
        "source_id": "C1:1730000000.000100",
        "timestamp": "1730000000.000100",
        "text": "stand-up",
    },
    "telegram": {
        "credentials": {"bot_token": "12345:AAAbbb"},
        "sequence": [("GET", "/getUpdates", 200, {"ok": True, "result": [
            {"update_id": 7, "message": {"message_id": 3, "date": 1730000000, "chat": {"id": 9, "type": "private"}, "text": "ping"}},
            {"update_id": 8, "message": {"message_id": 4, "date": 1730000001, "chat": {"id": -100, "type": "group"}, "text": "group hi"}},
        ]})],
        "source_id": "9:3",
        "timestamp": "1730000000",
        "text": "ping",
    },
    "discord": {
        "credentials": {"token": "discord-token", "channel_id": "123"},
        "sequence": [("GET", "/channels/123/messages", 200, [{
            "id": "99", "timestamp": "2026-11-01T00:00:00.000000+00:00", "content": "hello", "channel_id": "123",
        }])],
        "source_id": "99",
        "timestamp": "2026-11-01T00:00:00.000000+00:00",
        "text": "hello",
    },
    "notion": {
        "credentials": {"token": "notion-token"},
        "sequence": [("POST", "/v1/search", 200, {"results": [{
            "id": "page1", "last_edited_time": "2026-11-01T00:00:00.000Z", "url": "https://www.notion.so/page1",
            "properties": {"Name": {"type": "title", "title": [{"plain_text": "Move notes"}]}},
        }]})],
        "source_id": "page1",
        "timestamp": "2026-11-01T00:00:00.000Z",
        "text": "Move notes",
    },
    "todoist": {
        "credentials": {"token": "todoist-token"},
        "sequence": [("GET", "/api/v1/tasks", 200, [{
            "id": "t1", "content": "Renew Salik", "updated_at": "2026-11-01T00:00:00Z", "description": "tag",
        }])],
        "source_id": "t1",
        "timestamp": "2026-11-01T00:00:00Z",
        "text": "Salik",
    },
    "trello": {
        "credentials": {"key": "trello-key", "token": "trello-token"},
        "sequence": [("GET", "/1/members/me/cards", 200, [{
            "id": "c1", "name": "Pack", "dateLastActivity": "2026-11-01T00:00:00.000Z", "desc": "boxes",
        }])],
        "source_id": "c1",
        "timestamp": "2026-11-01T00:00:00.000Z",
        "text": "boxes",
    },
    "linear": {
        "credentials": {"token": "linear-token"},
        "sequence": [("POST", "/graphql", 200, {"data": {"viewer": {"assignedIssues": {"nodes": [{
            "id": "iss1", "identifier": "DX-1", "title": "Memory", "updatedAt": "2026-11-01T00:00:00.000Z", "description": "schema",
        }]}}}})],
        "source_id": "DX-1",
        "timestamp": "2026-11-01T00:00:00.000Z",
        "text": "schema",
    },
    "reddit": {
        "credentials": {"token": "reddit-token"},
        "sequence": [
            ("GET", "/api/v1/me", 200, {"name": "haitham"}),
            ("GET", "/user/haitham/saved", 200, {"data": {"children": [{"data": {
                "name": "t3_abc", "title": "DXB", "selftext": "metro", "created_utc": 1730000000,
            }}]}}),
        ],
        "source_id": "t3_abc",
        "timestamp": "1730000000",
        "text": "metro",
    },
    "x": {
        "credentials": {"token": "x-token"},
        "sequence": [
            ("GET", "/2/users/me", 200, {"data": {"id": "42", "username": "h"}}),
            ("GET", "/2/users/42/tweets", 200, {"data": [{"id": "99", "text": "hello dubai", "created_at": "2026-11-01T00:00:00.000Z"}]}),
        ],
        "source_id": "99",
        "timestamp": "2026-11-01T00:00:00.000Z",
        "text": "hello dubai",
    },
    "spotify": {
        "credentials": {"token": "spotify-token"},
        "sequence": [("GET", "/v1/me/tracks", 200, {"items": [{
            "added_at": "2026-11-01T00:00:00Z", "track": {"id": "tr1", "name": "Song", "artists": [{"name": "A"}]},
        }]})],
        "source_id": "tr1",
        "timestamp": "2026-11-01T00:00:00Z",
        "text": "Song",
    },
    "dropbox": {
        "credentials": {"token": "dropbox-token"},
        "sequence": [("POST", "/files/list_folder", 200, {
            "entries": [{".tag": "file", "id": "id:1", "name": "contract.pdf", "server_modified": "2026-11-01T00:00:00Z", "size": 12}],
            "cursor": "cur1", "has_more": False,
        })],
        "source_id": "id:1",
        "timestamp": "2026-11-01T00:00:00Z",
        "text": "contract.pdf",
    },
}


@pytest.mark.parametrize("connector_id", sorted(CASES))
def test_live_connector_happy_path(tmp_path, connector_id):
    case = CASES[connector_id]
    sequence = list(case["sequence"])
    service, store, _db = _service(tmp_path, transport=_scripted(sequence))
    _seed(store, "owner-a", connector_id, case["credentials"])
    result = service.sync("owner-a", connector_id)
    assert sequence == []
    assert result["imported"] == (2 if connector_id == "telegram" else 1)
    assert result["health"] == "healthy"
    assert result["status"] == "ok"
    rows = store.records("owner-a", connector_id)
    match = next(row for row in rows if row["source_id"] == case["source_id"])
    assert match["source_timestamp"] == case["timestamp"]
    assert case["text"] in match["text"]
    assert match["provenance"] == "provider_confirmed"
    assert match["as_of"] == NOW
    assert store.records("owner-b", connector_id) == []


@pytest.mark.parametrize("connector_id", sorted(CASES))
def test_live_connector_auth_failure_keeps_cursor(tmp_path, connector_id):
    case = CASES[connector_id]
    service, store, _db = _service(tmp_path, transport=httpx.MockTransport(lambda _request: httpx.Response(401, json={})))
    _seed(store, "owner-a", connector_id, case["credentials"])
    store.upsert_connection(owner="owner-a", connector_id=connector_id, cursor={"since": "keep-me"}, updated_at=NOW)
    with pytest.raises(AuthFailed):
        service.sync("owner-a", connector_id)
    conn = store.connection("owner-a", connector_id)
    assert conn["health"] == "auth_required"
    assert conn["cursor"] == {"since": "keep-me"}
    assert store.records("owner-a", connector_id) == []
    assert store.credentials("owner-a", connector_id)


def test_retry_backoff_and_stop(tmp_path):
    calls = {"n": 0}

    def handler(_request):
        calls["n"] += 1
        return httpx.Response(503, json={})

    clock = {"now": NOW}

    def now():
        return clock["now"]

    service, store, _db = _service(tmp_path, transport=httpx.MockTransport(handler), clock=now)
    _seed(store, "owner-a", "github", {"token": "gh-token"})
    first = service.sync("owner-a", "github")
    assert first["status"] == "retry" and first["health"] == "error" and first["next_retry_at"]
    assert service.sync("owner-a", "github")["status"] == "retry_wait"
    assert calls["n"] == 1
    for _ in range(4):
        clock["now"] = (datetime.fromisoformat(clock["now"]) + timedelta(hours=1)).isoformat(timespec="seconds")
        service.sync("owner-a", "github")
    assert calls["n"] == 5
    clock["now"] = (datetime.fromisoformat(clock["now"]) + timedelta(hours=1)).isoformat(timespec="seconds")
    with pytest.raises(PermanentFailure):
        service.sync("owner-a", "github")
    assert calls["n"] == 5
    service.sync("owner-a", "github", force=True)
    assert calls["n"] == 6


def test_rate_limit_uses_retry_after(tmp_path):
    calls = {"n": 0}

    def handler(_request):
        calls["n"] += 1
        return httpx.Response(429, headers={"Retry-After": "3"}, json={})

    service, store, _db = _service(tmp_path, transport=httpx.MockTransport(handler))
    _seed(store, "owner-a", "spotify", {"token": "spotify-token"})
    result = service.sync("owner-a", "spotify")
    assert result["health"] == "rate_limited"
    assert result["next_retry_at"] == (datetime.fromisoformat(NOW) + timedelta(seconds=3)).isoformat(timespec="seconds")
    assert service.sync("owner-a", "spotify")["status"] == "retry_wait"
    assert calls["n"] == 1
    assert store.records("owner-a", "spotify") == []


def test_gmail_incremental_history_and_attachment_name(tmp_path):
    sequence = list(CASES["gmail"]["sequence"]) + [
        ("GET", "/history", 200, {"historyId": "11", "history": [{"messagesAdded": [{"message": {"id": "m2"}}]}]}),
        ("GET", "/messages/m2", 200, {
            "id": "m2", "snippet": "second", "internalDate": "1730000001000",
            "payload": {"headers": [{"name": "Date", "value": "Sat, 15 Nov 2026 09:00:00 +0400"}, {"name": "Subject", "value": "Next"}]},
        }),
    ]
    service, store, _db = _service(tmp_path, transport=_scripted(sequence))
    _seed(store, "owner-a", "gmail", CASES["gmail"]["credentials"])
    service.sync("owner-a", "gmail")
    second = service.sync("owner-a", "gmail")
    assert second["imported"] == 1
    rows = {row["source_id"]: row for row in store.records("owner-a", "gmail")}
    assert rows["m1"]["metadata"]["attachments"] == [{"file_name": "cv.pdf", "mime_type": "application/pdf"}]
    assert rows["m2"]["source_timestamp"] == "Sat, 15 Nov 2026 09:00:00 +0400"
    assert sequence == []


def test_credentials_are_encrypted_and_owner_scoped(tmp_path):
    service, store, db = _service(tmp_path)
    token = "super-secret-token-xyz"
    _seed(store, "owner-a", "github", {"token": token})
    blob = db.execute("SELECT ciphertext FROM connector_credentials").fetchone()[0]
    assert token.encode() not in bytes(blob)
    assert store.credentials("owner-a", "github")["token"] == token
    assert store.credentials("owner-b", "github") is None


def test_import_preserves_timestamp_and_rejects_fake_provenance(tmp_path):
    service, store, _db = _service(tmp_path)
    content = json.dumps([{
        "id": "r1",
        "text": "shirt",
        "timestamp": "Fri, 14 Nov 2026 09:00:00 +0400",
        "amount": "40",
        "currency": "AED",
        "provenance": "official",
    }])
    first = service.import_file("owner-a", "noon", "noon.json", content)
    assert first["imported"] == 1 and first["provenance"] == "user_supplied"
    row = store.records("owner-a", "noon")[0]
    assert row["source_timestamp"] == "Fri, 14 Nov 2026 09:00:00 +0400"
    assert row["provenance"] == "user_supplied"
    assert row["metadata"]["amount"] == {"value": "40", "currency": "AED", "provenance": "user_supplied", "as_of": "Fri, 14 Nov 2026 09:00:00 +0400"}
    second = service.import_file("owner-a", "noon", "noon.json", content)
    assert second["duplicate"] == 1 and second["imported"] == 0
    with pytest.raises(PermanentFailure):
        service.sync("owner-a", "amazon")
    with pytest.raises(PermanentFailure):
        service.import_file("owner-a", "gmail", "x.json", content)


def test_unavailable_sources_do_not_sync(tmp_path):
    service, _store, _db = _service(tmp_path)
    for spec in catalog():
        if spec.mode != "unavailable":
            continue
        described = service.describe(spec.id, "owner-a")
        assert described["available"] is False and described["read_records"] is False and described["outbound"] is False
        with pytest.raises(UnavailableConnector):
            service.sync("owner-a", spec.id)


def test_registry_matches_declarations_and_schema_is_generic():
    specs = catalog()
    impls = build_implementations()
    assert [spec.id for spec in specs if spec.integration == "unofficial"] == ["whatsapp"]
    whatsapp = next(spec for spec in specs if spec.id == "whatsapp")
    assert whatsapp.feature_flag == "WHATSAPP_EVOLUTION_ENABLED" and whatsapp.available is False and whatsapp.account_risk
    signal = next(spec for spec in specs if spec.id == "signal")
    assert "no official" in signal.limitations.lower() or "does not offer an official" in signal.limitations.lower()
    instagram = next(spec for spec in specs if spec.id == "instagram")
    assert instagram.mode == "export" and "direct messages" in instagram.limitations.lower()
    for spec in specs:
        if spec.mode in {"live", "export"}:
            assert spec.id in impls
        else:
            assert spec.id not in impls
    schema = "\n".join(DDL).lower()
    for spec in specs:
        assert re.search(rf"\b{re.escape(spec.id)}\b", schema) is None
    for path in (ROOT / "app" / "connectors" / "plugins").glob("*.py"):
        assert "CREATE TABLE" not in path.read_text()


def test_public_hosts_reject_private_targets():
    assert public_https_origin("https://acme.atlassian.net") == "https://acme.atlassian.net"
    for bad in ("http://acme.atlassian.net", "https://127.0.0.1", "https://10.1.1.1", "https://localhost", "https://user:pass@acme.atlassian.net"):
        with pytest.raises(PermanentFailure):
            public_https_origin(bad)


def test_filesystem_is_scoped(tmp_path):
    service, store, _db = _service(tmp_path)
    folder = tmp_path / "notes"
    folder.mkdir()
    outside = tmp_path / "outside-secret.txt"
    outside.write_text("outside")
    (folder / "note.txt").write_text("marina rent")
    (folder / ".env").write_text("SUPER_SECRET=1")
    (folder / "link.txt").symlink_to(outside)
    _seed(store, "owner-a", "filesystem", {"root": str(folder)})
    result = service.sync("owner-a", "filesystem")
    assert result["imported"] == 1
    rows = store.records("owner-a", "filesystem")
    assert rows[0]["source_id"] == "note.txt"
    assert "marina rent" in rows[0]["text"]
    assert rows[0]["source_timestamp"].isdigit()
    dumped = json.dumps(rows)
    assert "SUPER_SECRET" not in dumped and "outside" not in dumped
    again = service.sync("owner-a", "filesystem")
    assert again["imported"] == 0
    note = folder / "note.txt"
    note.write_text("marina rent updated")
    stamp = note.stat().st_mtime_ns + 1_000_000
    os.utime(note, ns=(stamp, stamp))
    updated = service.sync("owner-a", "filesystem")
    assert updated["updated"] == 1
    with pytest.raises(PermanentFailure):
        service.connect("owner-a", "filesystem", {"root": "/"})
    counts = service.delete_user_data("owner-a", "filesystem")
    assert counts["deleted"]["connector_records"] == 1
    assert (folder / "note.txt").read_text() == "marina rent updated"


def test_imap_parses_fixture_and_login_failure(tmp_path):
    header = b"Subject: Visa slot\r\nFrom: RTA <no-reply@example.com>\r\nDate: Fri, 14 Nov 2026 09:00:00 +0400\r\n\r\n"
    fetched = [
        (b'10 (UID 10 INTERNALDATE "14-Nov-2026 05:00:00 +0000" BODY[HEADER.FIELDS (SUBJECT FROM DATE)] {80}', header),
        (b" BODY[TEXT]<0> {5}", b"hello"),
        b")",
    ]
    item = parse_imap_fetch(b"10", fetched)
    assert item.source_timestamp == "Fri, 14 Nov 2026 09:00:00 +0400"
    assert item.metadata["internaldate"] == "14-Nov-2026 05:00:00 +0000"
    assert "hello" in item.text

    class FakeIMAP:
        def login(self, user, password):
            if password == "bad":
                raise RuntimeError("login failed for bad")
        def select(self, mailbox, readonly=True):
            return "OK", [b"1"]
        def uid(self, command, *args):
            if command == "search":
                return "OK", [b"10"]
            return "OK", fetched
        def logout(self):
            return "BYE", [None]

    class Module:
        def IMAP4_SSL(self, host, port):
            assert host == "imap.example.com" and port == 993
            return FakeIMAP()

    service, store, _db = _service(tmp_path)

    from contextlib import contextmanager

    @contextmanager
    def opener(_impl):
        yield Module()

    service.open_client = opener
    with pytest.raises(AuthFailed):
        service.connect("owner-a", "imap", {"host": "imap.example.com", "username": "a", "password": "bad"})
    assert store.credentials("owner-a", "imap") is None
    connected = service.connect("owner-a", "imap", {"host": "imap.example.com", "username": "a@b.c", "password": "app-pass"})
    assert connected["account_label"] == "a@b.c"
    assert "app-pass" not in json.dumps(connected)
    result = service.sync("owner-a", "imap")
    assert result["imported"] == 1
    assert store.records("owner-a", "imap")[0]["source_timestamp"] == "Fri, 14 Nov 2026 09:00:00 +0400"


def test_outbound_gate_default_deny(tmp_path):
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if request.url.path.endswith("/getMe"):
            return httpx.Response(200, json={"ok": True, "result": {"username": "dubai_bot"}})
        if request.url.path.endswith("/sendMessage"):
            return httpx.Response(200, json={"ok": True, "result": {"message_id": 5}})
        raise AssertionError(request.url.path)

    clock = {"now": NOW}
    service, store, _db = _service(tmp_path, transport=httpx.MockTransport(handler), clock=lambda: clock["now"])
    connected = service.connect("owner-a", "telegram", {"bot_token": "12345:AAAbbb"})
    assert "12345:AAAbbb" not in json.dumps({k: v for k, v in connected.items() if k != "webhook_secret"})
    payload = {"chat_id": "9", "text": "hello"}
    proposed = service.propose_outbound("owner-a", "telegram", "send_message", payload)
    assert proposed["sent"] is False and proposed["status"] == "pending" and proposed["shares"] == ["chat_id", "text"]
    with pytest.raises(PermissionDenied):
        service.execute_outbound("owner-a", "telegram", proposed["grant_id"], payload)
    with pytest.raises(PermissionDenied):
        service.decide_outbound("owner-b", proposed["grant_id"], True)
    assert store.grant("owner-a", proposed["grant_id"])["status"] == "pending"
    denied = service.propose_outbound("owner-a", "telegram", "send_message", payload)
    service.decide_outbound("owner-a", denied["grant_id"], False)
    with pytest.raises(PermissionDenied):
        service.execute_outbound("owner-a", "telegram", denied["grant_id"], payload)
    service.decide_outbound("owner-a", proposed["grant_id"], True)
    with pytest.raises(PermissionDenied):
        service.execute_outbound("owner-a", "telegram", proposed["grant_id"], {"chat_id": "9", "text": "changed"})
    assert store.grant("owner-a", proposed["grant_id"])["status"] == "approved"
    sent = service.execute_outbound("owner-a", "telegram", proposed["grant_id"], payload)
    assert sent["provider_accepted"] is True and sent["provenance"] == "provider_confirmed"
    assert "delivery receipt" in sent["notice"]
    with pytest.raises(PermissionDenied):
        service.execute_outbound("owner-a", "telegram", proposed["grant_id"], payload)
    assert calls["n"] == 2
    expired = service.propose_outbound("owner-a", "telegram", "send_message", payload)
    clock["now"] = (datetime.fromisoformat(NOW) + timedelta(seconds=601)).replace(tzinfo=timezone.utc).isoformat(timespec="seconds")
    with pytest.raises(PermissionDenied):
        service.decide_outbound("owner-a", expired["grant_id"], True)
    with pytest.raises(PermissionDenied):
        service.propose_outbound("owner-a", "github", "send_message", payload)


def test_revoke_keeps_records_delete_removes_them(tmp_path):
    calls = []

    def handler(request):
        calls.append(request.url.path)
        return httpx.Response(200, json={})

    service, store, _db = _service(tmp_path, transport=httpx.MockTransport(handler))
    _seed(store, "owner-a", "gmail", {"access_token": "gmail-token"})
    from app.connectors.types import RawItem
    store.upsert_records("owner-a", "gmail", [RawItem("m1", "Fri, 14 Nov 2026 09:00:00 +0400", "hello", "email")], now=NOW, provenance="provider_confirmed")
    revoked = service.revoke("owner-a", "gmail")
    assert revoked["records_kept"] is True and revoked["remote"] == "revoked"
    assert calls == ["/revoke"]
    assert store.credentials("owner-a", "gmail") is None
    assert store.records("owner-a", "gmail")
    service.delete_user_data("owner-a", "gmail")
    assert store.records("owner-a", "gmail") == []
    assert store.connection("owner-a", "gmail") is None


def test_sync_does_not_write_profile_memory(tmp_path):
    sequence = list(CASES["github"]["sequence"])
    service, store, db = _service(tmp_path, transport=_scripted(sequence))
    _seed(store, "owner-a", "github", CASES["github"]["credentials"])
    service.sync("owner-a", "github")
    names = [row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    assert "mem_events" not in names and "profile_facts" not in names


def test_docs_match_the_registry():
    root = Path(__file__).resolve().parents[3] / "docs" / "connectors"
    matrix = (root / "capability-matrix.md").read_text()
    priority = (root / "prioritization.md").read_text()
    architecture = (root / "architecture.md").read_text()
    whatsapp = (root / "whatsapp-evolution.md").read_text()
    for spec in catalog():
        assert f"`{spec.id}`" in matrix
        row = next(line for line in priority.splitlines() if line.startswith(f"| {spec.id} |"))
        cells = [cell.strip() for cell in row.strip().strip("|").split("|")]
        assert cells[0] == spec.id and cells[1] == spec.mode
        assert int(cells[-1]) == spec.priority
    assert "mem_events" in architecture
    assert "Baileys" in whatsapp and "ban" in whatsapp.lower()


def test_discord_without_a_channel_does_not_read_personal_dms(tmp_path):
    def handler(_request):
        raise AssertionError("Discord was called without a channel id")

    service, store, _db = _service(tmp_path, transport=httpx.MockTransport(handler))
    _seed(store, "owner-a", "discord", {"token": "discord-token"})
    result = service.sync("owner-a", "discord")
    assert result["imported"] == 0
    assert "Personal DMs" in (result["notice"] or "")


def test_schema_is_idempotent_and_migration_matches(tmp_path):
    db = connect(tmp_path / "schema.db")
    ensure_connector_schema(db)
    ensure_connector_schema(db)
    migration = Path(__file__).resolve().parents[3].joinpath("supabase/migrations/20261114000100_connectors.sql").read_text()
    for name in ("connector_credentials", "connector_connections", "connector_records", "connector_sync_log", "connector_outbound_grants"):
        assert name in migration
        assert db.execute("SELECT name FROM sqlite_master WHERE name=?", (name,)).fetchone()
    assert "ENABLE ROW LEVEL SECURITY" in migration and "REVOKE ALL" in migration


def test_webhook_secret_and_dedupe(tmp_path):
    def handler(request):
        if request.url.path.endswith("/getMe"):
            return httpx.Response(200, json={"ok": True, "result": {"username": "dubai_bot"}})
        raise AssertionError(request.url.path)

    service, store, _db = _service(tmp_path, transport=httpx.MockTransport(handler))
    connected = service.connect("owner-a", "telegram", {"bot_token": "12345:AAAbbb"})
    hook_id = connected["webhook_path"].rstrip("/").split("/")[-1]
    payload = {"update_id": 1, "message": {"message_id": 3, "date": 1730000000, "chat": {"id": 9, "type": "private"}, "text": "ping"}}
    with pytest.raises(AuthFailed):
        service.ingest_webhook("telegram", hook_id, "wrong", payload)
    first = service.ingest_webhook("telegram", hook_id, connected["webhook_secret"], payload)
    assert first["imported"] == 1
    second = service.ingest_webhook("telegram", hook_id, connected["webhook_secret"], payload)
    assert second["duplicate"] == 1
    assert store.records("owner-b", "telegram") == []


def test_whatsapp_message_normalizer_keeps_media_metadata():
    item = normalize_evolution_message({
        "key": {"remoteJid": "971500000000-111@g.us", "fromMe": False, "id": "ABC"},
        "messageTimestamp": 1730000000,
        "pushName": "Noura",
        "message": {"imageMessage": {"mimetype": "image/jpeg", "fileLength": "1200", "caption": "pic"}},
    })
    assert item is not None
    assert item.kind == "group_message"
    assert item.source_id == "ABC"
    assert item.source_timestamp == "1730000000"
    assert item.metadata["media"] == [{"kind": "image", "mimetype": "image/jpeg", "file_length": "1200", "file_name": "", "caption": "pic"}]
    assert "base64" not in json.dumps(item.metadata)


def test_whatsapp_disabled_does_not_call_network(tmp_path, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "whatsapp_evolution_enabled", False)

    def handler(_request):
        raise AssertionError("network")

    service, _store, _db = _service(tmp_path, transport=httpx.MockTransport(handler))
    described = service.describe("whatsapp", "owner-a")
    assert described["available"] is False and described["integration"] == "unofficial" and described["outbound_enabled"] is False
    with pytest.raises(DisabledConnector):
        service.connect("owner-a", "whatsapp", {})
    with pytest.raises(PermissionDenied):
        service.propose_outbound("owner-a", "whatsapp", "send_message", {"to": "971500000000", "text": "hi"})


def test_whatsapp_link_sync_and_gated_send(tmp_path, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "whatsapp_evolution_enabled", True)
    monkeypatch.setattr(settings, "evolution_api_base_url", "https://evolution.example.com")
    monkeypatch.setattr(settings, "evolution_api_key", "server-key")
    calls = []
    states = {"n": 0}

    def handler(request: httpx.Request):
        body = json.loads(request.content or b"{}") if request.content else {}
        calls.append((request.method, request.url.path, body.get("instanceName")))
        path = request.url.path
        if path.endswith("/instance/create"):
            return httpx.Response(201, json={})
        if "/instance/connect/" in path:
            return httpx.Response(200, json={"base64": "cXItYm90ZQ==", "code": "PAIR"})
        if "/instance/connectionState/" in path:
            states["n"] += 1
            state = "close" if states["n"] <= 2 else "open"
            return httpx.Response(200, json={"instance": {"state": state}})
        if "/chat/findMessages/" in path:
            return httpx.Response(200, json={"messages": {"records": [
                {"key": {"remoteJid": "971500000000@s.whatsapp.net", "fromMe": False, "id": "M1"}, "messageTimestamp": 1730000000, "pushName": "Noura", "message": {"conversation": "hello"}},
                {"key": {"remoteJid": "971500000000-111@g.us", "fromMe": False, "id": "G1"}, "messageTimestamp": 1730000001, "pushName": "Building", "message": {"conversation": "group"}},
            ]}})
        if "/group/fetchAllGroups/" in path:
            return httpx.Response(200, json=[{"id": "971500000000-111@g.us", "subject": "Building"}])
        if "/message/sendText/" in path:
            return httpx.Response(200, json={"key": {"id": "sent1"}})
        if "/instance/logout/" in path or "/instance/delete/" in path:
            return httpx.Response(200, json={})
        raise AssertionError(path)

    service, store, _db = _service(tmp_path, transport=httpx.MockTransport(handler))
    linked = service.connect("owner-a", "whatsapp", {"instance_name": "attacker"})
    assert linked["status"] == "pending" and linked["unofficial"] is True and linked["qr_base64"]
    assert any("ban" in risk.lower() for risk in linked["risks"])
    stored = store.credentials("owner-a", "whatsapp")["instance_name"]
    assert stored == instance_name("owner-a") and stored != "attacker" and "owner-a" not in stored
    other = service.connect("owner-b", "whatsapp", {})
    assert store.credentials("owner-b", "whatsapp")["instance_name"] != stored
    assert other["qr_base64"]
    # The QR response saw connectionState close-or-open; force the stored row to connected for sync.
    store.upsert_connection("owner-a", "whatsapp", status="connected", updated_at=NOW)
    result = service.sync("owner-a", "whatsapp")
    assert result["health"] == "degraded" and result["partial"] is True and "Unofficial" in result["notice"]
    rows = {row["kind"]: row for row in store.records("owner-a", "whatsapp")}
    assert rows["message"]["text"] == "hello" and rows["message"]["source_timestamp"] == "1730000000"
    assert rows["group_message"]["metadata"]["group"].endswith("@g.us")
    assert rows["group"]["title"] == "Building"
    again = service.sync("owner-a", "whatsapp")
    assert again["duplicate"] >= 1 and again["imported"] == 0
    paths = [path for _method, path, _name in calls if "findMessages" in path or "sendText" in path]
    assert all(stored in path for path in paths)
    assert not any(store.credentials("owner-b", "whatsapp")["instance_name"] in path for path in paths)
    payload = {"to": "971500000000", "text": "on my way"}
    proposed = service.propose_outbound("owner-a", "whatsapp", "send_message", payload)
    assert proposed["sent"] is False
    before = len(calls)
    with pytest.raises(PermissionDenied):
        service.execute_outbound("owner-a", "whatsapp", proposed["grant_id"], payload)
    assert len(calls) == before
    service.decide_outbound("owner-a", proposed["grant_id"], True)
    sent = service.execute_outbound("owner-a", "whatsapp", proposed["grant_id"], payload)
    assert sent["provider_accepted"] is True and "not a delivery receipt" in sent["notice"]
    assert any("/message/sendText/" in path for _m, path, _n in calls)
    revoked = service.revoke("owner-a", "whatsapp")
    assert revoked["remote"] == "logout_requested"
    assert any("/instance/logout/" in path for _m, path, _n in calls)
    assert store.credentials("owner-a", "whatsapp") is None
    assert store.records("owner-a", "whatsapp")


def test_whatsapp_closed_session_does_not_invent_messages(tmp_path, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "whatsapp_evolution_enabled", True)
    monkeypatch.setattr(settings, "evolution_api_base_url", "http://127.0.0.1:8080")
    monkeypatch.setattr(settings, "evolution_api_key", "server-key")
    calls = []

    def handler(request):
        calls.append(request.url.path)
        if "/instance/connectionState/" in request.url.path:
            return httpx.Response(200, json={"state": "close"})
        if "/instance/connect/" in request.url.path:
            return httpx.Response(200, json={"qrcode": {"base64": "aaa", "code": "PAIR"}})
        raise AssertionError(request.url.path)

    service, store, _db = _service(tmp_path, transport=httpx.MockTransport(handler))
    _seed(store, "owner-a", "whatsapp", {"instance_name": instance_name("owner-a")})
    store.upsert_connection("owner-a", "whatsapp", status="connected", updated_at=NOW)
    with pytest.raises(AuthFailed):
        service.sync("owner-a", "whatsapp")
    assert store.records("owner-a", "whatsapp") == []
    assert not any("findMessages" in path for path in calls)
    outcome = service.reconnect("owner-a", "whatsapp")
    assert outcome["state"] == "close" and outcome["qr_base64"] == "aaa" and outcome["unofficial"] is True
