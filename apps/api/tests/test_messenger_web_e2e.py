"""MG-B7b Messenger web E2E tests: conversation list + WS hub broadcast and live 2-browser Playwright verification.

Covers:
1. Offline deterministic HTTP + WebSocket hub test (list conversations, live WS broadcast on send/edit/delete,
   and strict isolation for a non-member user).
2. Live two-browser (+ third denied browser) Playwright E2E against real local Supabase GoTrue, FastAPI
   messenger server, and Vite dev server (skipped automatically when local Supabase env vars are unset).
"""
from __future__ import annotations

import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
import httpx
import pytest
from starlette.testclient import WebSocketDenialResponse

from app.identity import (
    IdentityConfig,
    IdentityService,
    IdentityStore,
    JWTVerifier,
    create_identity_router,
)
from app.messenger.hub import ChatHub
from app.messenger.routes_chat import router as chat_router
from app.messenger.store import ChatStore
from tests.fixtures.contest_shared.identity_fixtures import (
    TEST_AUDIENCE,
    TEST_HS256_SECRET,
    TEST_ISSUER,
    default_claims,
    sign_hs256_jwt,
)

ORIGIN = "http://testserver"

SUPABASE_URL = os.getenv("SUPABASE_LOCAL_URL", "").strip().rstrip("/")
SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "").strip()
JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "").strip()


def _build_offline_app(
    identity_db_path: Path,
    chat_db_path: Path,
) -> tuple[FastAPI, IdentityStore, ChatStore, TestClient]:
    verifier = JWTVerifier(issuer=TEST_ISSUER, audience=TEST_AUDIENCE, hs256_secret=TEST_HS256_SECRET)
    config = IdentityConfig(jwt_issuer=TEST_ISSUER, jwt_audience=TEST_AUDIENCE, jwt_hs256_secret=TEST_HS256_SECRET)
    ident_store = IdentityStore(identity_db_path)
    chat_store = ChatStore(chat_db_path)
    identity_service = IdentityService(ident_store, verifier, config=config)

    app = FastAPI(title="Messenger Web E2E Offline")
    app.state.identity_service = identity_service
    app.state.chat_store = chat_store
    app.state.chat_hub = ChatHub()
    app.include_router(create_identity_router())
    app.include_router(chat_router)
    return app, ident_store, chat_store, TestClient(app)


def _open_adult_messenger_session(client: TestClient, sub: str) -> tuple[str, str]:
    token = sign_hs256_jwt(default_claims(sub=sub))
    opened = client.post(
        "/api/identity/sessions",
        headers={"Authorization": f"Bearer {token}"},
        json={"app_id": "messenger"},
    )
    assert opened.status_code == 200, opened.text
    body = opened.json()
    session_token = body["session_token"]
    user_id = body["user_id"]

    aged = client.post(
        "/api/identity/age-band",
        headers={"X-App-Session": session_token},
        json={"age_band": "adult_18_plus"},
    )
    assert aged.status_code == 200, aged.text
    assert aged.json()["is_minor_protected"] is False
    return session_token, user_id


def _mint_ws_ticket(client: TestClient, session_token: str, *, origin: str = ORIGIN) -> str:
    resp = client.post(
        "/api/identity/ws-ticket",
        headers={"X-App-Session": session_token, "Origin": origin},
        json={"app_id": "messenger"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["ticket"]


def _conversation_ids(payload: dict | list) -> list[str]:
    rows = payload["conversations"] if isinstance(payload, dict) else payload
    return [row["id"] if isinstance(row, dict) else row for row in rows]


def test_messenger_list_conversations_and_ws_broadcast(tmp_path: Path):
    """Offline hub + routes test: conversation listing, live WS broadcast on send/edit/delete, and non-member isolation."""
    _app, ident_store, chat_store, client = _build_offline_app(
        tmp_path / "web_offline_identity.sqlite3",
        tmp_path / "web_offline_chat.sqlite3",
    )
    try:
        sess_a, user_a = _open_adult_messenger_session(client, "mg-web-offline-a")
        sess_b, user_b = _open_adult_messenger_session(client, "mg-web-offline-b")
        sess_c, user_c = _open_adult_messenger_session(client, "mg-web-offline-c")
        assert len({user_a, user_b, user_c}) == 3

        created = client.post(
            "/api/messenger/conversations",
            headers={"X-App-Session": sess_a},
            json={"kind": "direct", "member_ids": [user_b], "title": "Alpha Beta"},
        )
        assert created.status_code == 200, created.text
        conv_ab = created.json()["id"]

        list_a = client.get("/api/messenger/conversations", headers={"X-App-Session": sess_a})
        list_b = client.get("/api/messenger/conversations", headers={"X-App-Session": sess_b})
        list_c = client.get("/api/messenger/conversations", headers={"X-App-Session": sess_c})
        assert list_a.status_code == 200, list_a.text
        assert list_b.status_code == 200, list_b.text
        assert list_c.status_code == 200, list_c.text
        assert _conversation_ids(list_a.json()) == [conv_ab]
        assert _conversation_ids(list_b.json()) == [conv_ab]
        assert _conversation_ids(list_c.json()) == []

        t_a = _mint_ws_ticket(client, sess_a)
        t_b = _mint_ws_ticket(client, sess_b)
        t_c = _mint_ws_ticket(client, sess_c)

        with (
            client.websocket_connect(f"/api/messenger/ws?ticket={t_a}", headers={"origin": ORIGIN}) as ws_a,
            client.websocket_connect(f"/api/messenger/ws?ticket={t_b}", headers={"origin": ORIGIN}) as ws_b,
            client.websocket_connect(f"/api/messenger/ws?ticket={t_c}", headers={"origin": ORIGIN}) as ws_c,
        ):
            assert ws_a.receive_json() == {"op": "ready", "user_id": user_a}
            assert ws_b.receive_json() == {"op": "ready", "user_id": user_b}
            assert ws_c.receive_json() == {"op": "ready", "user_id": user_c}

            ws_a.send_json(
                {
                    "op": "send",
                    "conversation_id": conv_ab,
                    "client_msg_id": "hub-1",
                    "text": "Live broadcast hello",
                }
            )
            ack_a = ws_a.receive_json()
            assert ack_a["op"] == "ack"
            msg = ack_a["message"]
            assert msg["body"] == "Live broadcast hello"
            assert msg["sender_id"] == user_a

            pushed_b = ws_b.receive_json()
            assert pushed_b["op"] == "message"
            assert pushed_b["message"]["id"] == msg["id"]
            assert pushed_b["message"]["body"] == "Live broadcast hello"

            edited = client.post(
                f"/api/messenger/conversations/{conv_ab}/messages/{msg['id']}/edit",
                headers={"X-App-Session": sess_a},
                json={"text": "Live broadcast edited"},
            )
            assert edited.status_code == 200, edited.text

            edit_b = ws_b.receive_json()
            assert edit_b["op"] == "edit"
            assert edit_b["message"]["id"] == msg["id"]
            assert edit_b["message"]["body"] == "Live broadcast edited"

            deleted = client.post(
                f"/api/messenger/conversations/{conv_ab}/messages/{msg['id']}/delete",
                headers={"X-App-Session": sess_a},
            )
            assert deleted.status_code == 200, deleted.text

            delete_b = ws_b.receive_json()
            assert delete_b["op"] == "delete"
            assert delete_b["message"]["id"] == msg["id"]
            assert delete_b["message"]["deleted"] is True

            # Verify User C received zero pushed frames across send, edit, and delete
            # by sending a synchronous probe frame and asserting the immediate reply.
            ws_c.send_json({"op": "__probe__"})
            assert ws_c.receive_json() == {"op": "error", "code": "unknown_op"}
    finally:
        chat_store.close()
        ident_store.close()


def test_messenger_ws_allowed_origins_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """D13 WS origin allowlist test: MESSENGER_ALLOWED_ORIGINS permits tunnel Origin and rejects unlisted Origin (403)."""
    allowed_origin = "https://messenger-tunnel.example.test"
    monkeypatch.setenv("MESSENGER_ALLOWED_ORIGINS", allowed_origin)

    _app, ident_store, chat_store, client = _build_offline_app(
        tmp_path / "origins_identity.sqlite3",
        tmp_path / "origins_chat.sqlite3",
    )
    try:
        sess_a, user_a = _open_adult_messenger_session(client, "mg-web-origins-a")

        allowed_ticket = _mint_ws_ticket(client, sess_a, origin=allowed_origin)
        with client.websocket_connect(
            f"/api/messenger/ws?ticket={allowed_ticket}",
            headers={"origin": allowed_origin},
        ) as ws_allowed:
            assert ws_allowed.receive_json() == {"op": "ready", "user_id": user_a}

        unlisted_ticket = _mint_ws_ticket(client, sess_a, origin=ORIGIN)
        with pytest.raises(WebSocketDenialResponse) as denied_exc:
            with client.websocket_connect(
                f"/api/messenger/ws?ticket={unlisted_ticket}",
                headers={"origin": ORIGIN},
            ):
                pass
        assert denied_exc.value.status_code == 403
    finally:
        chat_store.close()
        ident_store.close()


def _two_free_tcp_ports() -> tuple[int, int]:
    with (
        socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s1,
        socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s2,
    ):
        s1.bind(("127.0.0.1", 0))
        s2.bind(("127.0.0.1", 0))
        return int(s1.getsockname()[1]), int(s2.getsockname()[1])


def _wait_http_200(url: str, proc: subprocess.Popen[str], log_path: Path, *, timeout_s: float = 30.0) -> None:
    deadline = time.monotonic() + timeout_s
    last_err = ""
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            output = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else ""
            raise RuntimeError(f"Process exited early ({proc.returncode}) before {url} became ready:\n{output}")
        try:
            resp = httpx.get(url, timeout=1.5)
            if resp.status_code == 200:
                return
            last_err = f"HTTP {resp.status_code}"
        except Exception as exc:
            last_err = str(exc)
        time.sleep(0.25)
    output = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else ""
    raise TimeoutError(f"Timed out waiting for {url} ({last_err}):\n{output}")


def _terminate_process(proc: subprocess.Popen[str] | None) -> None:
    if proc is None or proc.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
            check=False,
            capture_output=True,
        )
        try:
            proc.wait(timeout=5)
            return
        except subprocess.TimeoutExpired:
            pass
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


@pytest.mark.skipif(
    not (SUPABASE_URL and SERVICE_ROLE_KEY and ANON_KEY),
    reason="SUPABASE_LOCAL_URL / local Supabase Auth env vars not set",
)
def test_messenger_two_browser_e2e_live_supabase(tmp_path: Path):
    """Live Playwright two-browser (+ denied 3rd browser) E2E against real GoTrue, uvicorn, and Vite."""
    from playwright.sync_api import sync_playwright

    run_id = uuid4().hex[:10]
    password = f"MgWeb!{run_id}"
    users = [
        (f"mg_web_a_{run_id}@dubai.test", "Messenger Web Alpha"),
        (f"mg_web_b_{run_id}@dubai.test", "Messenger Web Beta"),
        (f"mg_web_c_{run_id}@dubai.test", "Messenger Web Gamma"),
    ]
    created_ids: list[str] = []
    admin_headers = {
        "apikey": SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
    }

    api_port, web_port = _two_free_tcp_ports()
    api_url = f"http://127.0.0.1:{api_port}"
    web_url = f"http://127.0.0.1:{web_port}"

    api_dir = Path(__file__).resolve().parents[1]
    web_dir = Path(__file__).resolve().parents[2] / "messenger"
    api_log = tmp_path / "api.log"
    web_log = tmp_path / "vite.log"

    api_proc: subprocess.Popen[str] | None = None
    web_proc: subprocess.Popen[str] | None = None

    with httpx.Client(base_url=SUPABASE_URL, timeout=15.0) as supa:
        try:
            for email, display_name in users:
                created = supa.post(
                    "/auth/v1/admin/users",
                    headers=admin_headers,
                    json={
                        "email": email,
                        "password": password,
                        "email_confirm": True,
                        "user_metadata": {"display_name": display_name},
                    },
                )
                assert created.status_code in (200, 201), created.text
                created_ids.append(created.json()["id"])

            issuer = f"{SUPABASE_URL}/auth/v1"
            api_env = os.environ.copy()
            api_env.update(
                {
                    "SUPABASE_LOCAL_URL": SUPABASE_URL,
                    "SUPABASE_JWT_SECRET": JWT_SECRET,
                    "IDENTITY_JWT_ISSUER": issuer,
                    "IDENTITY_JWT_JWKS_URL": f"{issuer}/.well-known/jwks.json",
                    "IDENTITY_JWT_HS256_SECRET": JWT_SECRET,
                    "IDENTITY_JWT_AUDIENCE": "authenticated",
                    "MESSENGER_IDENTITY_DB": str(tmp_path / "web_identity.sqlite3"),
                    "MESSENGER_CHAT_DB": str(tmp_path / "web_chat.sqlite3"),
                }
            )
            with api_log.open("w", encoding="utf-8") as api_fh, web_log.open("w", encoding="utf-8") as web_fh:
                api_proc = subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "uvicorn",
                        "app.messenger.server:app",
                        "--host",
                        "127.0.0.1",
                        "--port",
                        str(api_port),
                    ],
                    cwd=str(api_dir),
                    env=api_env,
                    stdout=api_fh,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
                _wait_http_200(f"{api_url}/api/messenger/health", api_proc, api_log)

                npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
                web_env = os.environ.copy()
                web_env["MESSENGER_API_URL"] = api_url
                web_proc = subprocess.Popen(
                    [
                        npm_cmd,
                        "run",
                        "dev",
                        "--",
                        "--host",
                        "127.0.0.1",
                        "--port",
                        str(web_port),
                        "--strictPort",
                    ],
                    cwd=str(web_dir),
                    env=web_env,
                    stdout=web_fh,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
                _wait_http_200(f"{web_url}/", web_proc, web_log)

                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    ctx_a = browser.new_context()
                    ctx_b = browser.new_context()
                    ctx_c = browser.new_context()
                    try:
                        page_a = ctx_a.new_page()
                        page_b = ctx_b.new_page()
                        page_c = ctx_c.new_page()

                        # (a) Initial real-mode boot has zero seeded chats/messages
                        for page in (page_a, page_b, page_c):
                            page.goto(f"{web_url}/", wait_until="domcontentloaded")
                            page.wait_for_function("() => Boolean(window.__messenger)", timeout=15000)
                            body_text = page.locator("body").inner_text()
                            assert "Arif Khan" not in body_text
                            assert "Kite Beach" not in body_text

                        # (b) Sign A, B, C into real Supabase GoTrue
                        auth_states = []
                        for page, (email, display_name) in zip((page_a, page_b, page_c), users):
                            auth = page.evaluate(
                                """async (creds) => {
                                    await window.__messenger.actions.signInWithPassword(creds);
                                    return window.__messenger.getState().auth;
                                }""",
                                {
                                    "supabaseUrl": SUPABASE_URL,
                                    "anonKey": ANON_KEY,
                                    "email": email,
                                    "password": password,
                                    "displayName": display_name,
                                },
                            )
                            assert auth["status"] == "signed_in", auth
                            auth_states.append(auth)

                        user_a_id, user_b_id, user_c_id = (a["userId"] for a in auth_states)
                        assert len({user_a_id, user_b_id, user_c_id}) == 3

                        # (c) Browser A creates a real direct conversation with B and sends a message
                        conv_result = page_a.evaluate(
                            """async (memberId) => {
                                return await window.__messenger.actions.createConversation({
                                    memberIds: [memberId],
                                    kind: "direct",
                                    title: "Alpha Beta",
                                });
                            }""",
                            user_b_id,
                        )
                        conv_id = conv_result["id"] if isinstance(conv_result, dict) else conv_result
                        assert isinstance(conv_id, str) and conv_id

                        composer_a = page_a.locator('input[aria-label="Message"]')
                        composer_a.fill("Real browser message from A")
                        composer_a.press("Enter")
                        page_a.locator("main").get_by_text("Real browser message from A").first.wait_for(state="visible", timeout=10000)

                        # (d) Browser B refreshes conversations, opens conv_id, sees A's message, and replies
                        page_b.evaluate(
                            """async (cid) => {
                                await window.__messenger.actions.refreshConversations();
                                await window.__messenger.actions.openChat(cid);
                            }""",
                            conv_id,
                        )
                        page_b.locator("main").get_by_text("Real browser message from A").first.wait_for(state="visible", timeout=10000)
                        composer_b = page_b.locator('input[aria-label="Message"]')
                        composer_b.fill("Live reply from Browser B")
                        composer_b.press("Enter")
                        page_b.locator("main").get_by_text("Live reply from Browser B").first.wait_for(state="visible", timeout=10000)

                        # (e) Browser A receives B's reply live over WS, then reloads and verifies persistence
                        page_a.locator("main").get_by_text("Live reply from Browser B").first.wait_for(state="visible", timeout=10000)
                        page_a.reload(wait_until="domcontentloaded")
                        page_a.wait_for_function(
                            "() => Boolean(window.__messenger) && window.__messenger.getState().auth?.status === 'signed_in'",
                            timeout=15000,
                        )
                        page_a.evaluate(
                            """async (cid) => {
                                const state = window.__messenger.getState();
                                if (!state.conversations || state.conversations.length === 0) {
                                    await window.__messenger.actions.refreshConversations();
                                }
                                if (window.__messenger.getState().activeChatId !== cid) {
                                    await window.__messenger.actions.openChat(cid);
                                }
                            }""",
                            conv_id,
                        )
                        page_a.locator("main").get_by_text("Real browser message from A").first.wait_for(state="visible", timeout=10000)
                        page_a.locator("main").get_by_text("Live reply from Browser B").first.wait_for(state="visible", timeout=10000)

                        # (f) Browser C sees 0 conversations, gets lastError === "not_found" on openChat, and sees neither message
                        c_check = page_c.evaluate(
                            """async (cid) => {
                                await window.__messenger.actions.refreshConversations();
                                const convCount = (window.__messenger.getState().conversations || []).length;
                                try {
                                    await window.__messenger.actions.openChat(cid);
                                } catch (_err) {
                                    // Expected if openChat rejects after recording lastError.
                                }
                                return {
                                    convCount,
                                    lastError: window.__messenger.getState().lastError,
                                };
                            }""",
                            conv_id,
                        )
                        assert c_check["convCount"] == 0
                        assert c_check["lastError"] == "not_found"
                        body_c = page_c.locator("body").inner_text()
                        assert "Real browser message from A" not in body_c
                        assert "Live reply from Browser B" not in body_c
                    finally:
                        ctx_c.close()
                        ctx_b.close()
                        ctx_a.close()
                        browser.close()
        finally:
            _terminate_process(web_proc)
            _terminate_process(api_proc)
            for uid in created_ids:
                try:
                    supa.delete(f"/auth/v1/admin/users/{uid}", headers=admin_headers)
                except Exception:
                    pass
