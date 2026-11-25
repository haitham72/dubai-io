"""E12 two-user Playwright e2e: Community website <-> real local community API.

Runs only when `playwright` is importable (installed ad-hoc in the api venv:
`uv pip install --python apps/api/.venv/Scripts/python.exe playwright` then
`python -m playwright install chromium`). Synthetic users only.

The API is a real uvicorn server built in-process from apps/api routers, with
the same test session path as apps/api/tests/fixtures/community/bind.py
(minted community app sessions injected as X-App-Session by the website).
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

import pytest

pytest.importorskip("playwright.sync_api", reason="playwright not installed")

COMMUNITY_DIR = Path(__file__).resolve().parents[2]
API_DIR = COMMUNITY_DIR.parent / "api"
SCREENS = Path(__file__).resolve().parent / "screens"
SESSION_KEY = "dubaiio_community_session"


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _wait_http(url: str, timeout: float = 60.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                if r.status < 500:
                    return
        except Exception:
            pass
        time.sleep(0.5)
    raise RuntimeError(f"{url} did not come up")


@pytest.fixture(scope="module")
def stack(tmp_path_factory):
    """Real community API (uvicorn) + Next dev server + two minted users."""
    tmp = tmp_path_factory.mktemp("e12")
    sys.path.insert(0, str(API_DIR))
    try:
        import uvicorn
        from fastapi import FastAPI
        from app import actions
        from app.actions import ActionEngine, ActionStore
        from app.community.routes import router as community_router
        from app.identity import IdentityConfig, IdentityService, IdentityStore, JWTVerifier
        from tests.fixtures.contest_shared.identity_fixtures import (
            TEST_AUDIENCE, TEST_HS256_SECRET, TEST_ISSUER,
            default_claims, sign_hs256_jwt,
        )
    except Exception as exc:  # pragma: no cover - env guard
        pytest.skip(f"api imports unavailable: {exc}")

    store = ActionStore(tmp / "community.sqlite3")
    old_engine = actions._engine
    actions._engine = ActionEngine(store)

    verifier = JWTVerifier(issuer=TEST_ISSUER, audience=TEST_AUDIENCE, hs256_secret=TEST_HS256_SECRET)
    service = IdentityService(
        IdentityStore(tmp / "identity.sqlite3"), verifier,
        config=IdentityConfig(jwt_issuer=TEST_ISSUER, jwt_audience=TEST_AUDIENCE, jwt_hs256_secret=TEST_HS256_SECRET),
        legacy_session_resolver=store.owner,
    )

    tokens: dict[str, str] = {}
    for name in ("alice", "bob"):
        jwt = sign_hs256_jwt(default_claims(sub=f"e12-{name}", display_name=f"E12 {name.title()}"))
        principal = service.authenticate_jwt(jwt)
        principal = service.set_age_band(principal, age_band="adult_18_plus")
        tokens[name] = service.create_app_session(principal, app_id="community").session_token

    web_port = _free_port()
    base_web = f"http://127.0.0.1:{web_port}"

    app = FastAPI()
    app.state.identity_service = service
    from fastapi.middleware.cors import CORSMiddleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[base_web, "http://localhost:" + str(web_port)],
        allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
    )

    @app.get("/api/health")
    def health():
        return {"ok": True}

    app.include_router(community_router)

    api_port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=api_port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    node = shutil.which("node")
    next_bin = COMMUNITY_DIR / "node_modules" / "next" / "dist" / "bin" / "next"
    if not node or not next_bin.exists():
        server.should_exit = True
        pytest.skip("node or next binary not available")
    env = dict(os.environ)
    env["NEXT_PUBLIC_CM_API"] = f"http://127.0.0.1:{api_port}"
    env["NEXT_PUBLIC_DUBAI_API"] = f"http://127.0.0.1:{api_port}"
    web = subprocess.Popen(
        [node, str(next_bin), "dev", "-p", str(web_port), "-H", "127.0.0.1"],
        cwd=str(COMMUNITY_DIR), env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

    base_api = f"http://127.0.0.1:{api_port}"
    base_web = f"http://127.0.0.1:{web_port}"
    try:
        _wait_http(f"{base_api}/api/health", timeout=30)
        _wait_http(base_web + "/", timeout=180)
        yield {"api": base_api, "web": base_web, "tokens": tokens}
    finally:
        web.terminate()
        try:
            web.wait(timeout=10)
        except Exception:
            web.kill()
        server.should_exit = True
        thread.join(timeout=10)
        actions._engine = old_engine
        store.db.close()


def api_call(stack, user: str, method: str, path: str, body=None):
    import urllib.request
    req = urllib.request.Request(
        stack["api"] + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"content-type": "application/json", "X-App-Session": stack["tokens"][user]},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def _profile(stack, user: str, handle: str):
    status, body = api_call(stack, user, "PUT", "/api/community/profiles/me", {
        "handle": handle, "display_name": handle.replace("_", " ").title(),
        "bio": f"Synthetic e2e profile for {handle}", "area": "Dubai",
        "interests": ["walking", "books"], "age_band": "18+", "privacy": "public",
    })
    assert status == 200, body


def _context(browser, stack, user: str):
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    ctx.add_init_script(
        f"try{{window.localStorage.setItem('{SESSION_KEY}', {json.dumps(stack['tokens'][user])})}}catch(e){{}}"
    )
    return ctx


def _shot(page, name: str):
    SCREENS.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(SCREENS / name), full_page=False)


def test_two_user_flow(stack):
    from playwright.sync_api import sync_playwright

    _profile(stack, "alice", "e12_alice")
    _profile(stack, "bob", "e12_bob")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        alice = _context(browser, stack, "alice")
        bob = _context(browser, stack, "bob")
        pa, pb = alice.new_page(), bob.new_page()

        # -- A creates a profile-backed post via the real UI --
        pa.goto(f"{stack['web']}/create", wait_until="load", timeout=120_000)
        pa.fill("#post-text", "E2E: marina walk at sunrise — who is in for Saturday?")
        pa.click("button.primary")
        try:
            pa.wait_for_selector("article.v2-card:visible", timeout=60_000)
        except Exception:
            SCREENS.mkdir(parents=True, exist_ok=True)
            pa.screenshot(path=str(SCREENS / "debug-after-post.png"))
            print("URL:", pa.url)
            raise
        post_card = pa.locator("article.v2-card:visible", has_text="marina walk").first
        assert post_card.count() == 1
        post_id = post_card.get_attribute("data-post-id")
        _shot(pa, "01-feed-alice-post.png")

        # -- B sees it in Following only after following A --
        # (the feed renders a phone + a desktop layout; only one is visible)
        pb.goto(f"{stack['web']}/", wait_until="load", timeout=120_000)
        pb.locator("[role=tab]:visible", has_text="Following").click()
        pb.wait_for_timeout(1500)
        assert pb.locator("article.v2-card:visible", has_text="marina walk").count() == 0

        pb.goto(f"{stack['web']}/u/e12_alice", wait_until="load", timeout=120_000)
        pb.get_by_role("button", name="Follow", exact=True).click()
        pb.wait_for_selector("button[aria-pressed='true']", timeout=15_000)

        pb.goto(f"{stack['web']}/", wait_until="load", timeout=120_000)
        pb.locator("[role=tab]:visible", has_text="Following").click()
        card = pb.locator("article.v2-card:visible", has_text="marina walk").first
        card.wait_for(state="visible", timeout=30_000)

        # -- B likes and replies (threaded reply covered by unit tests) --
        like_btn = card.get_by_role("button", name="Like")
        like_btn.click()
        deadline = time.time() + 20
        while like_btn.get_attribute("aria-pressed") != "true" and time.time() < deadline:
            pb.wait_for_timeout(250)
        assert like_btn.get_attribute("aria-pressed") == "true"
        assert card.locator(".v2-count").first.text_content() == "1"
        card.get_by_role("button", name="Comments").click()
        card.locator(".v2-replybox input").fill("Count me in — see you Saturday!")
        card.locator(".v2-replybox button", has_text="Send").click()
        card.locator("text=Count me in").wait_for(state="visible", timeout=15_000)
        _shot(pb, "02-thread-bob-reply.png")

        # -- A sees the like count and the reply notification --
        pa.goto(f"{stack['web']}/", wait_until="load", timeout=120_000)
        a_card = pa.locator("article.v2-card:visible", has_text="marina walk").first
        a_card.wait_for(state="visible", timeout=30_000)
        assert a_card.locator(".v2-count").first.text_content() == "1"
        pa.goto(f"{stack['web']}/inbox", wait_until="load", timeout=120_000)
        pa.wait_for_selector("text=Count me in", timeout=30_000)
        _shot(pa, "03-inbox-alice-notification.png")

        # -- Profile, search and For-you screenshots --
        pa.goto(f"{stack['web']}/u/e12_bob", wait_until="load", timeout=120_000)
        _shot(pa, "04-profile-bob.png")
        pa.goto(f"{stack['web']}/search?q=marina", wait_until="load", timeout=120_000)
        pa.wait_for_selector("article.v2-card:visible", timeout=30_000)
        _shot(pa, "05-search.png")
        pa.goto(f"{stack['web']}/", wait_until="load", timeout=120_000)
        pa.locator("[role=tab]:visible", has_text="For you").click()
        pa.wait_for_timeout(2000)
        _shot(pa, "06-for-you.png")

        # -- communities page screenshot --
        pa.goto(f"{stack['web']}/communities", wait_until="load", timeout=120_000)
        pa.wait_for_timeout(1500)
        _shot(pa, "07-communities.png")

        alice.close(); bob.close(); browser.close()

        # API-level assertions on the same real server
        status, inbox = api_call(stack, "alice", "GET", "/api/community/inbox")
        assert status == 200
        kinds = [n.get("kind") or n.get("type") for n in inbox.get("notifications", [])]
        assert any(k in ("reply", "comment") for k in kinds), inbox

        status, post = api_call(stack, "alice", "GET", f"/api/community/posts/{post_id}")
        assert status == 200 and post["post"]["reaction_count"] >= 1


def test_private_group_fenced(stack):
    """A post in a private group is invisible to a non-member (API + UI)."""
    from playwright.sync_api import sync_playwright

    status, group = api_call(stack, "alice", "POST", "/api/community/groups",
                             {"name": "E12 Secret Circle", "handle": "e12_secret",
                              "description": "private e2e group", "visibility": "private"})
    assert status in (200, 201), group
    gid = group["group"]["id"]
    status, post = api_call(stack, "alice", "POST", f"/api/community/groups/{gid}/posts",
                            {"text": "secret plan inside private group"})
    assert status in (200, 201), post

    status, detail = api_call(stack, "bob", "GET", f"/api/community/groups/{gid}")
    assert status in (403, 404), (status, detail)
    status, posts = api_call(stack, "bob", "GET", f"/api/community/groups/{gid}/posts")
    assert status in (403, 404), (status, posts)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = _context(browser, stack, "bob")
        page = ctx.new_page()
        page.goto(f"{stack['web']}/communities/{gid}", wait_until="load", timeout=120_000)
        page.wait_for_selector(".error, .v2-error, [role=alert]", timeout=60_000)
        body = page.inner_text("body")
        assert "secret plan inside private group" not in body
        assert "not visible" in body.lower() or "not found" in body.lower() or "private" in body.lower()
        ctx.close(); browser.close()


def test_reply_to_deleted_post_shows_api_error(stack):
    status, post = api_call(stack, "alice", "POST", "/api/community/posts",
                            {"text": "e2e post that will be deleted"})
    assert status in (200, 201), post
    pid = post["post"]["id"]
    status, _ = api_call(stack, "alice", "DELETE", f"/api/community/posts/{pid}")
    assert status in (200, 204), _
    status, err = api_call(stack, "bob", "POST", f"/api/community/posts/{pid}/comments",
                           {"text": "reply after delete"})
    assert status in (400, 404, 410, 422), (status, err)
    assert err.get("detail"), err


def test_api_down_shows_honest_demo_state(stack):
    """With the API unreachable the feed falls back to demo data WITH the pill — never a fake success."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        ctx.add_init_script(f"try{{window.localStorage.setItem('{SESSION_KEY}', {json.dumps(stack['tokens']['alice'])})}}catch(e){{}}")
        page = ctx.new_page()
        page.route("**/api/community/**", lambda route: route.abort())
        page.goto(f"{stack['web']}/", wait_until="load", timeout=120_000)
        try:
            page.locator(".demo-pill:visible, .v2-demo:visible").first.wait_for(state="visible", timeout=60_000)
        except Exception:
            page.screenshot(path=str(SCREENS / "debug-offline.png"))
            print("URL:", page.url)
            print("BODY:", page.inner_text("body")[:2000].encode("ascii", "replace").decode())
            raise
        body = page.inner_text("body")
        assert "unavailable" in body.lower() or "demo" in body.lower()
        # no fake 'Posted' confirmation anywhere
        assert "Posted" not in body
        page.screenshot(path=str(SCREENS / "08-offline-demo-feed.png"))
        ctx.close(); browser.close()
