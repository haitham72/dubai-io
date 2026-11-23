"""ID-09 tests for CS-B5 MemoryTokenService, Fernet at-rest encryption, HTTP routes, and isolation."""
from __future__ import annotations

from pathlib import Path

from cryptography.fernet import Fernet
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.identity import (
    IdentityConfig,
    IdentityError,
    IdentityService,
    IdentityStore,
    JWTVerifier,
    MemoryTokenService,
    create_identity_router,
)
from app.identity.deps import LEGACY_ANON_COOKIE
from app.memory_bridge.fake_client import FakeTemporalMemoryClient
from app.memory_bridge.models import ConsentDeniedError
from tests.fixtures.contest_shared.identity_fixtures import (
    TEST_AUDIENCE,
    TEST_HS256_SECRET,
    TEST_ISSUER,
    default_claims,
    sign_hs256_jwt,
)


def _setup(tmp_path: Path, *, token_key: str | None = None):
    verifier = JWTVerifier(
        issuer=TEST_ISSUER,
        audience=TEST_AUDIENCE,
        hs256_secret=TEST_HS256_SECRET,
    )
    store = IdentityStore(tmp_path / "identity.sqlite3")
    svc = IdentityService(
        store,
        verifier,
        config=IdentityConfig(
            jwt_issuer=TEST_ISSUER,
            jwt_audience=TEST_AUDIENCE,
            jwt_hs256_secret=TEST_HS256_SECRET,
        ),
    )
    fake_tm = FakeTemporalMemoryClient()
    key_path = tmp_path / "identity_token.key"
    token_svc = MemoryTokenService(store, fake_tm, token_key=token_key, key_path=key_path)

    app = FastAPI()
    app.state.identity_service = svc
    app.state.memory_token_handler = token_svc
    app.include_router(create_identity_router())
    return svc, store, fake_tm, token_svc, TestClient(app), key_path


def _mint_app_session(client: TestClient, sub: str, app_id: str, *, caps: list[str] | None = None) -> tuple[str, str]:
    jwt_tok = sign_hs256_jwt(default_claims(sub=sub))
    body: dict[str, object] = {"app_id": app_id}
    if caps is not None:
        body["requested_capabilities"] = caps
    resp = client.post(
        "/api/identity/sessions",
        headers={"Authorization": f"Bearer {jwt_tok}"},
        json=body,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    return str(data["user_id"]), str(data["session_token"])


def test_ensure_bridge_token_encrypts_at_rest_and_resolves_per_owner(tmp_path: Path, monkeypatch) -> None:
    """ID-09: bridge_service token is Fernet-encrypted in cs_memory_tokens and resolves per owner."""
    key = Fernet.generate_key().decode("ascii")
    monkeypatch.setenv("IDENTITY_TOKEN_KEY", key)
    _svc, store, fake_tm, token_svc, client, _key_path = _setup(tmp_path)

    uid_a, _ = _mint_app_session(client, "550e8400-e29b-41d4-a716-446655440101", "quest")
    uid_b, _ = _mint_app_session(client, "550e8400-e29b-41d4-a716-446655440102", "quest")

    tok_a1 = token_svc.ensure_bridge_token(uid_a)
    tok_a2 = token_svc.owner_token_resolver(uid_a)
    tok_b = token_svc.ensure_bridge_token(uid_b)
    assert tok_a1 == tok_a2
    assert tok_a1 != tok_b
    assert uid_a in fake_tm.owners and uid_b in fake_tm.owners

    row = store.get_active_memory_token(uid_a, kind="bridge_service")
    assert row is not None
    assert row["encrypted_token"] is not None
    assert tok_a1.encode("utf-8") not in row["encrypted_token"]
    assert Fernet(key.encode("ascii")).decrypt(row["encrypted_token"]).decode("utf-8") == tok_a1

    # Scoped temporal_memory client works for owner A and rejects owner B.
    scoped_a = fake_tm.as_scoped(tok_a1)
    scoped_a.upsert_record_and_enqueue(
        uid_a,
        record_id="qmsg:bridge-1",
        source="quest:t1",
        at="2026-11-23T10:00:00Z",
        author=uid_a,
        text="Owner A bridge token write",
        enqueue="none",
        direct_fact={
            "text": "Owner A bridge token write",
            "subject_path": "work/notes",
            "evidence": ["qmsg:bridge-1"],
        },
    )
    assert len(scoped_a.search_facts(uid_a, "bridge")) == 1
    with pytest.raises(ConsentDeniedError):
        scoped_a.search_facts(uid_b, "")

    # Wrong key fails closed on decryption.
    wrong_key = Fernet.generate_key().decode("ascii")
    bad_svc = MemoryTokenService(store, fake_tm, token_key=wrong_key)
    with pytest.raises(IdentityError) as exc_info:
        bad_svc.ensure_bridge_token(uid_a)
    assert exc_info.value.status_code == 500


def test_local_key_file_fallback_and_isolated_path(tmp_path: Path, monkeypatch) -> None:
    """When IDENTITY_TOKEN_KEY is unset, local_key generates an isolated key file (never hardcoded)."""
    monkeypatch.delenv("IDENTITY_TOKEN_KEY", raising=False)
    _svc, store, fake_tm, token_svc, client, key_path = _setup(tmp_path)
    assert key_path.exists()

    uid, _ = _mint_app_session(client, "550e8400-e29b-41d4-a716-446655440103", "quest")
    tok1 = token_svc.ensure_bridge_token(uid)
    # Re-instantiate reading from the same isolated key file.
    token_svc_reloaded = MemoryTokenService(store, fake_tm, key_path=key_path)
    assert token_svc_reloaded.ensure_bridge_token(uid) == tok1


def test_http_mint_list_revoke_and_cross_user_isolation(tmp_path: Path) -> None:
    """ID-09: HTTP device token mint/list/revoke enforces owner binding, revocation, and User A vs User B isolation."""
    _svc, store, fake_tm, _token_svc, client, _key_path = _setup(tmp_path)

    uid_a, sess_a_q = _mint_app_session(client, "550e8400-e29b-41d4-a716-446655440111", "quest")
    uid_b, sess_b_q = _mint_app_session(client, "550e8400-e29b-41d4-a716-446655440112", "quest")

    # Spoofed owner or server-owned fields in body rejected.
    spoof_resp = client.post(
        "/api/identity/memory-device-token",
        headers={"X-App-Session": sess_a_q},
        json={"owner": uid_b, "label": "steal"},
    )
    assert spoof_resp.status_code == 403

    spoof_role = client.post(
        "/api/identity/memory-device-token",
        headers={"X-App-Session": sess_a_q},
        json={"role": "admin", "label": "escalate"},
    )
    assert spoof_role.status_code == 422

    # Happy path: mint owner_device token via HTTP route.
    mint_resp = client.post(
        "/api/identity/memory-device-token",
        headers={"X-App-Session": sess_a_q},
        json={"label": "laptop-cli"},
    )
    assert mint_resp.status_code == 200, mint_resp.text
    minted = mint_resp.json()
    assert minted["owner_id"] == uid_a
    assert minted["label"] == "laptop-cli"
    assert minted["token"]
    tm_token_id = minted["tm_token_id"]

    # Stored as metadata-only (encrypted_token=None).
    row = store.get_memory_token_by_tm_id(tm_token_id)
    assert row is not None
    assert row["kind"] == "owner_device"
    assert row["encrypted_token"] is None
    assert row["user_id"] == uid_a

    # List returns metadata only (no raw token!).
    list_resp = client.get("/api/identity/memory-device-token", headers={"X-App-Session": sess_a_q})
    assert list_resp.status_code == 200
    tokens = list_resp.json()["tokens"]
    assert len(tokens) == 1
    assert tokens[0]["tm_token_id"] == tm_token_id
    assert "token" not in tokens[0]
    assert "encrypted_token" not in tokens[0]

    # Audit log recorded without raw token.
    audits = store.list_audit_events(uid_a)
    assert any(ev["event_kind"] == "memory_device_token_minted" for ev in audits)
    assert minted["token"] not in str(audits)

    # User A's device token works for User A, fails 403 on User B's vault/records.
    scoped_a = fake_tm.as_scoped(minted["token"])
    scoped_a.upsert_record_and_enqueue(
        uid_a,
        record_id="qmsg:dev-1",
        source="quest:cli",
        at="2026-11-23T11:00:00Z",
        author=uid_a,
        text="Device token note",
        enqueue="none",
        direct_fact={"text": "Device token note", "subject_path": "notes", "evidence": ["qmsg:dev-1"]},
    )
    assert len(scoped_a.search_facts(uid_a, "Device")) == 1

    fake_tm.ensure_owner(uid_b, label=uid_b)
    with pytest.raises(ConsentDeniedError) as exc_vault:
        scoped_a.get_vault_subjects(uid_b)
    assert exc_vault.value.status_code == 403
    with pytest.raises(ConsentDeniedError) as exc_search:
        scoped_a.search_facts(uid_b, "")
    assert exc_search.value.status_code == 403
    with pytest.raises(ConsentDeniedError) as exc_write:
        scoped_a.upsert_record_and_enqueue(
            uid_b,
            record_id="qmsg:hack",
            source="quest:cli",
            at="2026-11-23T11:05:00Z",
            author=uid_b,
            text="cross-owner write",
            enqueue="none",
        )
    assert exc_write.value.status_code == 403

    # User B cannot list or revoke User A's tm_token_id.
    assert client.get("/api/identity/memory-device-token", headers={"X-App-Session": sess_b_q}).json()["tokens"] == []
    cross_del = client.delete(
        f"/api/identity/memory-device-token/{tm_token_id}",
        headers={"X-App-Session": sess_b_q},
    )
    assert cross_del.status_code == 403
    assert store.get_memory_token_by_tm_id(tm_token_id)["revoked_at"] is None  # type: ignore[index]

    # User A revokes own token -> calls revoke_token & blocks subsequent temporal_memory calls.
    del_resp = client.delete(
        f"/api/identity/memory-device-token/{tm_token_id}",
        headers={"X-App-Session": sess_a_q},
    )
    assert del_resp.status_code == 200
    assert del_resp.json()["revoked"] is True
    assert store.get_memory_token_by_tm_id(tm_token_id)["revoked_at"] is not None  # type: ignore[index]
    assert fake_tm.tokens[tm_token_id]["revoked_at"] is not None

    with pytest.raises(ConsentDeniedError) as exc_revoked:
        scoped_a.search_facts(uid_a, "Device")
    assert exc_revoked.value.status_code == 401

    # Unknown token -> 404.
    assert (
        client.delete(
            "/api/identity/memory-device-token/tok_nonexistent",
            headers={"X-App-Session": sess_a_q},
        ).status_code
        == 404
    )


def test_device_token_capability_and_app_enforcement(tmp_path: Path) -> None:
    """Non-quest app, missing memory:device_token capability, raw JWT, and anon cookie are rejected."""
    _svc, _store, _fake_tm, _token_svc, client, _key_path = _setup(tmp_path)
    sub = "550e8400-e29b-41d4-a716-446655440120"
    jwt_tok = sign_hs256_jwt(default_claims(sub=sub))
    _, sess_comm = _mint_app_session(client, sub, "community")
    _, sess_msg = _mint_app_session(client, sub, "messenger")
    _, sess_quest_no_cap = _mint_app_session(client, sub, "quest", caps=["quest:chat", "memory:read:owner"])

    for hdr in (
        {"X-App-Session": sess_comm},
        {"X-App-Session": sess_msg},
        {"X-App-Session": sess_quest_no_cap},
        {"Authorization": f"Bearer {jwt_tok}"},
    ):
        assert client.post("/api/identity/memory-device-token", headers=hdr, json={}).status_code == 403
        assert client.get("/api/identity/memory-device-token", headers=hdr).status_code == 403
        assert client.delete("/api/identity/memory-device-token/tok_1", headers=hdr).status_code == 403

    # Anonymous legacy cookie rejected 401.
    assert (
        client.post(
            "/api/identity/memory-device-token",
            headers={"Cookie": f"{LEGACY_ANON_COOKIE}=anon-owner-1"},
            json={},
        ).status_code
        == 401
    )

    # Spoofed identity headers rejected 400.
    assert (
        client.post(
            "/api/identity/memory-device-token",
            headers={"X-User-Id": "usr_spoof", "X-App-Session": sess_comm},
            json={},
        ).status_code
        == 400
    )
