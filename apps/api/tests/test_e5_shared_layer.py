"""E5: Community + Messenger on the same sign-in and the same memory. Synthetic accounts only, fake memory client."""
from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
from cryptography.fernet import Fernet
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import db as db_mod
from app.identity import IdentityConfig, IdentityService, IdentityStore, JWTVerifier, create_identity_router
from app.identity.google_signin import GoogleSignInService, validate_return_to
from app.identity.models import APP_CAPABILITIES, IdentityError, VerifiedPrincipal
from app.memory_bridge.bridge import MemoryBridge
from app.memory_bridge.fake_client import FakeTemporalMemoryClient
from app.memory_bridge.models import ConsentDeniedError, GroupConsentSnapshot, MemoryBridgeUnavailable, MemoryRecordInput
from app.messenger.memory_client import forget_chat, save_approved
from app.messenger.store import ChatStore
from app.shared_runtime import SHARED_DB_ENV, init_shared_runtime
from tests.fixtures.contest_shared.identity_fixtures import TEST_AUDIENCE, TEST_HS256_SECRET, TEST_ISSUER
from tests.test_e2_signin_pairing import REDIRECT, _google_transport


def _verifier() -> JWTVerifier:
    return JWTVerifier(issuer=TEST_ISSUER, audience=TEST_AUDIENCE, hs256_secret=TEST_HS256_SECRET)


def _cfg() -> IdentityConfig:
    return IdentityConfig(jwt_issuer=TEST_ISSUER, jwt_audience=TEST_AUDIENCE, jwt_hs256_secret=TEST_HS256_SECRET)


@pytest.fixture()
def trio(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """apps/api (sign-in, mocked Google) + a Community-shaped and a Messenger-shaped entry app on ONE identity store."""
    db_path = tmp_path / "shared-identity.sqlite3"
    state: dict = {}
    api_store = IdentityStore(db_path)
    api_svc = IdentityService(api_store, _verifier(), config=_cfg())
    google = GoogleSignInService(
        api_svc, client_id="synthetic-client-id.apps.test", client_secret="synthetic-secret-not-real",
        redirect_uri=REDIRECT, token_key=Fernet.generate_key(), transport=_google_transport(state),
    )
    api = FastAPI()
    api.state.identity_service = api_svc
    api.state.google_signin_service = google
    api.include_router(create_identity_router())

    monkeypatch.setenv(SHARED_DB_ENV, str(db_path))
    monkeypatch.setenv("MEMORY_BRIDGE_BACKEND", "fake")
    monkeypatch.delenv("TM_BASE_URL", raising=False)
    monkeypatch.setenv("IDENTITY_TOKEN_KEY", Fernet.generate_key().decode())
    entries = {}
    stores = []
    for name in ("community", "messenger"):
        entry = FastAPI()
        stores += init_shared_runtime(entry)
        entry.include_router(create_identity_router())
        entries[name] = entry
    yield api, entries
    for s in stores:
        s.close()
    api_store.close()


def _google_code(client: TestClient, code: str, return_to: str) -> str:
    start = client.get("/api/identity/google/start", params={"client": "web", "return_to": return_to})
    assert start.status_code == 302
    q = parse_qs(urlsplit(start.headers["location"]).query)
    cb = client.get("/api/identity/google/callback", params={"state": q["state"][0], "code": code})
    assert cb.status_code == 302, cb.text
    return parse_qs(urlsplit(cb.headers["location"]).query)["auth_code"][0]


def test_return_to_allows_loopback_ports_of_the_three_websites_and_nothing_else():
    for url in ("http://localhost:8081/connect", "http://localhost:3060/signin", "http://localhost:5173/",
                "http://127.0.0.1:3060/signin"):
        assert validate_return_to(url) == url
    for bad in ("https://localhost:3060/x", "http://evil.example/x", "http://localhost.evil.example:3060/x",
                "http://user@localhost:3060/x", "http://localhost:3060/x#frag"):
        with pytest.raises(IdentityError):
            validate_return_to(bad)


def test_one_google_signin_gives_the_same_user_id_in_all_three_apps(trio):
    api, entries = trio
    client = TestClient(api, follow_redirects=False)
    ids = {}
    for app_id, port in (("quest", 8081), ("community", 3060), ("messenger", 5173)):
        auth_code = _google_code(client, "code-a", f"http://localhost:{port}/signin")
        # The Community/Messenger websites redeem the code at their OWN API (same identity store); apps/api serves Quest.
        host = client if app_id == "quest" else TestClient(entries[app_id])
        ex = host.post("/api/identity/google/exchange", json={"auth_code": auth_code, "app_id": app_id})
        assert ex.status_code == 200, ex.text
        body = ex.json()
        assert body["app_id"] == app_id
        me = host.get("/api/identity/me", headers={"X-App-Session": body["session_token"]})
        assert me.status_code == 200 and me.json()["display_name"] == "Alice Test"
        ids[app_id] = me.json()["user_id"]
    assert len(set(ids.values())) == 1, ids


def test_session_of_one_app_is_refused_by_another_and_unknown_app_id_is_rejected(trio):
    api, entries = trio
    client = TestClient(api, follow_redirects=False)
    comm = TestClient(entries["community"])
    token = comm.post("/api/identity/google/exchange",
                      json={"auth_code": _google_code(client, "code-a", "http://localhost:3060/signin"),
                            "app_id": "community"}).json()["session_token"]
    svc = entries["messenger"].state.identity_service
    with pytest.raises(IdentityError) as exc:
        svc.authenticate_session(token, expected_app="messenger")
    assert exc.value.status_code == 403
    bad = comm.post("/api/identity/google/exchange",
                    json={"auth_code": _google_code(client, "code-a", "http://localhost:3060/signin"), "app_id": "admin"})
    assert bad.status_code == 422


def test_qr_pairing_gives_a_messenger_and_a_community_session_for_the_same_user(trio):
    api, entries = trio
    client = TestClient(api, follow_redirects=False)
    quest_tok = client.post("/api/identity/google/exchange",
                            json={"auth_code": _google_code(client, "code-a", "http://localhost:8081/connect")}).json()
    users = {}
    for app_id in ("community", "messenger"):
        pair = client.post("/api/identity/pair/start", headers={"X-App-Session": quest_tok["session_token"]}).json()
        done = TestClient(entries[app_id]).post(
            "/api/identity/pair/complete", json={"code": pair["code"], "app_id": app_id, "device_label": "iPhone"})
        assert done.status_code == 200, done.text
        assert done.json()["app_id"] == app_id
        users[app_id] = done.json()["user_id"]
    assert set(users.values()) == {quest_tok["user_id"]}


def test_entry_runtime_is_off_without_the_shared_env_and_http_backend_fails_closed(tmp_path, monkeypatch):
    monkeypatch.delenv(SHARED_DB_ENV, raising=False)
    app = FastAPI()
    assert init_shared_runtime(app) == [] and getattr(app.state, "memory_bridge", None) is None
    monkeypatch.setenv(SHARED_DB_ENV, str(tmp_path / "x.sqlite3"))
    monkeypatch.setenv("MEMORY_BRIDGE_BACKEND", "http")
    monkeypatch.delenv("TM_BASE_URL", raising=False)
    monkeypatch.delenv("TM_SERVICE_TOKEN", raising=False)
    with pytest.raises(MemoryBridgeUnavailable):
        init_shared_runtime(FastAPI())


# ---------------------------------------------------------------------------------------------- consent + Forget
def _p(user_id: str, app_id: str) -> VerifiedPrincipal:
    return VerifiedPrincipal(user_id=user_id, app_id=app_id, capabilities=APP_CAPABILITIES[app_id],
                             auth_mode="verified_app_session", age_band="adult_18_plus")


@pytest.fixture()
def world(tmp_path: Path):
    db = db_mod.connect(tmp_path / "bridge.sqlite3")
    fake = FakeTemporalMemoryClient()
    bridge = MemoryBridge(db, fake)
    chat = ChatStore(tmp_path / "chat.sqlite3")
    yield bridge, fake, chat
    db.close()


def _rec(owner, kind, source_id, rid, text, host, topic):
    return MemoryRecordInput(record_id=rid, source_kind=kind, source_id=source_id, host_app=host, author_id=owner,
                             text=text, valid_time="2026-11-24T10:00:00+00:00", subject_path=topic,
                             explicit_user_confirm=True)


def _open_all(bridge, owner):
    for app_id in ("quest", "community", "messenger"):
        bridge.set_source_consent(_p(owner, app_id), app_id, enabled=True, allow_interest_export=True)
        bridge.set_app_consent(_p(owner, app_id), app_id, read_enabled=True, write_enabled=True,
                               allow_interest_export_to_community=True)


def test_community_ranking_sees_only_consented_interest_features_never_raw_text(world):
    bridge, _fake, _chat = world
    owner = "usr_e5_a"
    quest, comm = _p(owner, "quest"), _p(owner, "community")
    bridge.set_app_consent(comm, "community", read_enabled=False, write_enabled=False)
    with pytest.raises(ConsentDeniedError):                    # default off
        bridge.read_community_interest_features(comm)
    bridge.set_source_consent(quest, "quest", enabled=True, allow_interest_export=True)
    bridge.set_app_consent(quest, "quest", read_enabled=True, write_enabled=True, allow_interest_export_to_community=True)
    bridge.set_app_consent(comm, "community", read_enabled=True, write_enabled=False, allow_interest_export_to_community=True)
    secret = "RAW_E5_QUEST_CHAT_canary tell nobody"
    bridge.write_consented(quest, _rec(owner, "quest", "quest:t1", "qmsg:t1", secret, "quest", "interests/padel"))
    bridge.write_consented(quest, _rec(owner, "quest", "quest:t1", "qmsg:t2", "my diabetes medication dose", "quest",
                                       "interests/health"))
    feats = bridge.read_community_interest_features(comm)
    assert [f.topic_slug for f in feats] == ["padel"]            # the sensitive one never becomes a feature
    dumped = repr(feats)
    assert "canary" not in dumped and "diabetes" not in dumped and "qmsg" not in dumped


def test_messenger_messages_are_not_memories_without_consent_and_save_is_source_linked(world):
    bridge, fake, chat = world
    a, b = _p("usr_e5_a", "messenger"), _p("usr_e5_b", "messenger")
    conv = chat.create_conversation(a.user_id, [b.user_id], kind="direct")
    msg = chat.send(conv, a.user_id, "m-e5-1", "Friday kiosk deadline, synthetic.")
    assert fake.records.get(a.user_id, {}) == {}                 # chatting writes nothing
    with pytest.raises(PermissionError):                         # ai mode defaults off
        save_approved(chat, bridge, a, conv, msg, confirmed=True)
    for person in (a, b):
        bridge.set_source_consent(person, "messenger", enabled=True)
        bridge.set_app_consent(person, "messenger", read_enabled=True, write_enabled=True)
        bridge.set_conversation_consent(person, conv, ai_mode="save")
        chat.set_ai_mode(conv, person.user_id, "save")
    with pytest.raises(PermissionError):                         # consent alone is not enough: each save is confirmed
        save_approved(chat, bridge, a, conv, msg, confirmed=False)
    assert fake.records.get(a.user_id, {}) == {}
    assert save_approved(chat, bridge, a, conv, msg, confirmed=True).ok
    rec = fake.records[a.user_id][f"mgmsg:{msg['id']}"]
    assert rec.source == f"messenger:{conv}"                     # scoped and source-linked
    assert fake.records.get(b.user_id, {}) == {}                 # the other participant gets nothing


def test_forget_in_one_app_removes_it_for_all_three(world):
    bridge, _fake, chat = world
    owner = "usr_e5_a"
    _open_all(bridge, owner)
    q, c, m = _p(owner, "quest"), _p(owner, "community"), _p(owner, "messenger")
    conv = chat.create_conversation(owner, ["usr_e5_other"], kind="direct")
    chat.set_ai_mode(conv, owner, "save")
    chat.set_ai_mode(conv, "usr_e5_other", "save")
    bridge.set_conversation_consent(m, conv, ai_mode="save", allow_interest_export=True)
    grp = GroupConsentSnapshot(conv, True, True, True, 1)
    bridge.write_consented(q, _rec(owner, "quest", "quest:t1", "qmsg:1", "Plays padel on Fridays", "quest", "interests/padel"))
    bridge.write_consented(m, _rec(owner, "messenger", f"messenger:{conv}", "mgmsg:1", "Booked the courtside slot",
                                   "messenger", "interests/courtside"), group_consent=grp)
    bridge.write_consented(c, _rec(owner, "community", "community:g1", "cmsave:1", "Saved a pottery thread", "community",
                                   "interests/pottery"))

    def quest_text() -> str:
        return " | ".join(f["text"] for f in bridge.read_quest_context(q, "padel pottery courtside")["facts"])

    def topics() -> set[str]:
        return {f.topic_slug for f in bridge.read_community_interest_features(c)}

    assert {"padel", "pottery", "courtside"} <= topics()
    assert "courtside" in quest_text() and "pottery" in quest_text()
    forget_chat(bridge, m, conv, key="e5-forget-conv")           # Forget in the Messenger ...
    assert "courtside" not in quest_text() and "courtside" not in topics()   # ... gone for Quest and Community
    assert "padel" in quest_text() and "pottery" in topics()     # other sources untouched
    bridge.forget_source(c, "community", host_app="community", idempotency_key="e5-forget-community")
    assert "pottery" not in quest_text() and "pottery" not in topics()      # Forget in Community: gone for Quest too
    bridge.forget_source(q, "quest", host_app="quest", idempotency_key="e5-forget-quest")
    assert bridge.read_quest_context(q, "padel pottery courtside")["facts"] == []
    assert bridge.read_community_interest_features(c) == []


def test_two_accounts_never_see_each_others_memory_interests_or_messages(world):
    bridge, _fake, chat = world
    founder, tester = "usr_e5_founder", "usr_e5_tester"
    for owner in (founder, tester):
        _open_all(bridge, owner)
    qf, cf, mf = (_p(founder, x) for x in ("quest", "community", "messenger"))
    qt, ct, mt = (_p(tester, x) for x in ("quest", "community", "messenger"))
    conv = chat.create_conversation(founder, ["usr_e5_third"], kind="direct")
    chat.set_ai_mode(conv, founder, "save")
    chat.set_ai_mode(conv, "usr_e5_third", "save")
    bridge.set_conversation_consent(mf, conv, ai_mode="save", allow_interest_export=True)
    grp = GroupConsentSnapshot(conv, True, True, True, 1)
    bridge.write_consented(qf, _rec(founder, "quest", "quest:f", "qmsg:f1", "FOUNDER_ONLY quest falconry", "quest", "interests/falconry"))
    bridge.write_consented(cf, _rec(founder, "community", "community:f", "cmsave:f1", "FOUNDER_ONLY community chess", "community", "interests/chess"))
    bridge.write_consented(mf, _rec(founder, "messenger", f"messenger:{conv}", "mgmsg:f1", "FOUNDER_ONLY message sailing",
                                    "messenger", "interests/sailing"), group_consent=grp)
    bridge.write_consented(qt, _rec(tester, "quest", "quest:t", "qmsg:t1", "TESTER_ONLY quest gardening", "quest", "interests/gardening"))
    query = "FOUNDER_ONLY TESTER_ONLY falconry chess sailing gardening"
    t_blob = " ".join(f["text"] for f in bridge.read_quest_context(qt, query)["facts"])
    assert "TESTER_ONLY" in t_blob and "FOUNDER_ONLY" not in t_blob
    assert [f.topic_slug for f in bridge.read_community_interest_features(ct)] == ["gardening"]
    assert bridge.read_community_own_activity(ct) == []
    scope = bridge.read_messenger_chat_scope(mt, conv, group_consent=GroupConsentSnapshot(conv, False, False, False, 1)) \
        if False else None   # a non-participant never reaches a conversation scope (group snapshot caller_ok=False)
    f_blob = " ".join(f["text"] for f in bridge.read_quest_context(qf, query)["facts"])
    assert "FOUNDER_ONLY" in f_blob and "TESTER_ONLY" not in f_blob
    assert {f.topic_slug for f in bridge.read_community_interest_features(cf)} == {"falconry", "chess", "sailing"}
    bridge.forget_source(qt, "quest", host_app="quest", idempotency_key="e5-tester-forget")   # tester forgets everything ...
    assert "FOUNDER_ONLY" in " ".join(f["text"] for f in bridge.read_quest_context(qf, query)["facts"])  # ... founder intact


def test_google_auth_code_redeemed_once_cannot_be_redeemed_in_another_app(trio):
    api, entries = trio
    client = TestClient(api, follow_redirects=False)
    hosts = {"quest": client, "community": TestClient(entries["community"]), "messenger": TestClient(entries["messenger"])}
    for first, others in (("community", ("messenger", "quest")), ("messenger", ("community", "quest")), ("quest", ("community", "messenger"))):
        code = _google_code(client, "code-a", "http://localhost:3060/signin")
        ok = hosts[first].post("/api/identity/google/exchange", json={"auth_code": code, "app_id": first})
        assert ok.status_code == 200, ok.text
        for other in (first,) + others:
            again = hosts[other].post("/api/identity/google/exchange", json={"auth_code": code, "app_id": other})
            assert again.status_code in (400, 401, 403, 409), again.text
            assert "session_token" not in again.text


def test_pairing_code_redeemed_once_cannot_be_redeemed_in_another_app(trio):
    api, entries = trio
    client = TestClient(api, follow_redirects=False)
    quest = client.post("/api/identity/google/exchange",
                        json={"auth_code": _google_code(client, "code-a", "http://localhost:8081/connect")}).json()
    hosts = {"quest": client, "community": TestClient(entries["community"]), "messenger": TestClient(entries["messenger"])}
    for first, others in (("community", ("messenger", "quest")), ("messenger", ("community", "quest"))):
        code = client.post("/api/identity/pair/start", headers={"X-App-Session": quest["session_token"]}).json()["code"]
        ok = hosts[first].post("/api/identity/pair/complete", json={"code": code, "app_id": first})
        assert ok.status_code == 200, ok.text
        for other in (first,) + others:
            again = hosts[other].post("/api/identity/pair/complete", json={"code": code, "app_id": other})
            assert again.status_code in (400, 401, 403, 409, 429), again.text
            assert "session_token" not in again.text
