"""E6 harness helper: mint two SYNTHETIC accounts + app sessions in the shared identity store.

Uses the identity test path (IdentityStore + IdentityService.issue_user_session), never a product backdoor and never
the founder's real account / Google sign-in. Run with the apps/api venv from the apps/api directory of the checkout the
stack runs from:  python <this file> <out.json>
Output JSON holds raw session tokens: it lives under acceptance/results/ (gitignored). Never print the tokens.
"""
from __future__ import annotations

import json
import secrets
import sys

from app.config import settings
from app.identity import IdentityConfig, IdentityService, IdentityStore, JWTVerifier

ACCOUNTS = {
    "A": {"subject": "e6-synthetic-account-a", "name": "E6 Synthetic Alpha", "email": "e6-a@synthetic.invalid"},
    "B": {"subject": "e6-synthetic-account-b", "name": "E6 Synthetic Bravo", "email": "e6-b@synthetic.invalid"},
}


def main(out_path: str) -> None:
    target = str(settings.database_url or (settings.data_dir / "identity.sqlite3"))
    cfg = IdentityConfig.from_env()
    verifier = JWTVerifier(issuer="local-unconfigured", audience=cfg.jwt_audience or "authenticated",
                           hs256_secret=secrets.token_urlsafe(32))
    store = IdentityStore(target)
    svc = IdentityService(store, verifier, config=cfg)
    out: dict = {}
    for key, acc in ACCOUNTS.items():
        user, _created = store.get_or_create_user_for_identity(
            issuer="e6-synthetic", subject=acc["subject"], display_name=acc["name"], email=acc["email"], email_verified=True)
        # Community is adults-only: declare an adult band through the normal identity store call.
        from app.identity.store import iso_utc
        store.update_age_band(user["user_id"], age_band="adult_18_plus", declared_at=iso_utc())
        sessions = {}
        session_ids = {}
        for app_id in ("quest", "community", "messenger"):
            s = svc.issue_user_session(user["user_id"], app_id=app_id, device_label=f"e6-{key}-{app_id}")
            sessions[app_id] = s.session_token
            session_ids[app_id] = s.session_id
        out[key] = {"user_id": user["user_id"], "display_name": acc["name"], "sessions": sessions, "session_ids": session_ids}
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(out, fh)
    print("minted", {k: v["user_id"] for k, v in out.items()}, "identity_target_kind", "postgres" if "://" in target else "sqlite")


if __name__ == "__main__":
    main(sys.argv[1])
