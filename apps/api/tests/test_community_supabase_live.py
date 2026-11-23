"""Live GoTrue check for a community session. Skips when local Supabase is not configured."""

import os

import pytest

pytestmark = pytest.mark.skipif(
    not os.getenv("SUPABASE_LOCAL_URL", "").strip(),
    reason="SUPABASE_LOCAL_URL is unset; local Supabase GoTrue is not running",
)


def test_community_live_gotrue_session_skipped_without_url():
    """Reached only when SUPABASE_LOCAL_URL is set. The skip above is the clean path."""
    import httpx
    from fastapi.testclient import TestClient

    from app.community.server import app

    url = os.environ["SUPABASE_LOCAL_URL"].rstrip("/")
    anon = os.environ["SUPABASE_ANON_KEY"]
    service_key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    email = "community-live@dubai.test"
    password = "SynthPass!ChangeMe"
    headers = {"apikey": service_key, "Authorization": f"Bearer {service_key}", "Content-Type": "application/json"}
    with httpx.Client(timeout=20) as http:
        created = http.post(f"{url}/auth/v1/admin/users", headers=headers, json={"email": email, "password": password, "email_confirm": True})
        try:
            assert created.status_code in (200, 201, 422), created.text
            signed = http.post(
                f"{url}/auth/v1/token?grant_type=password",
                headers={"apikey": anon, "Content-Type": "application/json"},
                json={"email": email, "password": password},
            )
            assert signed.status_code == 200, signed.text
            jwt_token = signed.json()["access_token"]
            client = TestClient(app)
            opened = client.post("/api/identity/sessions", headers={"Authorization": f"Bearer {jwt_token}"}, json={"app_id": "community"})
            assert opened.status_code == 200, opened.text
        finally:
            user_id = (created.json() or {}).get("id") if created.content else None
            if user_id:
                http.delete(f"{url}/auth/v1/admin/users/{user_id}", headers=headers)
