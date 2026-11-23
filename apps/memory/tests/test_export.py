"""Tests for Quest-style Markdown export & zip endpoint (WP-B)."""
from __future__ import annotations

import io
import zipfile

from fastapi import FastAPI
from fastapi.testclient import TestClient

from temporal_memory.api import export_md, vault
from temporal_memory.api.vault import AuthContext
from tests.fixtures.fake_store import FakeGraphStore


def test_render_full_quest_tree_and_forget_and_held_back():
    st = FakeGraphStore.from_karim_slice()
    tree = export_md.render("karim", store=st)

    # Core top-level files
    for req in ("USER.md", "MEMORIES.md", "noticed.md", "held-back.md"):
        assert req in tree

    # Subject theme + topic files + superseded "was ... until <date>" + original text
    assert "subjects/money/_subject.md" in tree
    assert "subjects/money/al-barsha-rent.md" in tree
    assert "was true until 2026-11-01" in tree["subjects/money/al-barsha-rent.md"]
    assert "فرح عمر اتنقل لقاعة زعبيل" in tree["subjects/lifestyle/omar-wedding.md"]

    # People files contain relationship, closeness, aliases, subject roles, evidence limits
    farouk_md = tree["people/omar-farouk.md"]
    assert "relationship: friend" in farouk_md
    assert "closeness: T1" in farouk_md
    assert "3omar" in farouk_md
    assert "groom" in farouk_md
    assert "Evidence limits:" in farouk_md

    # Quests, places, orgs, timeline present
    assert "quests/raseef-side-project-app.md" in tree
    assert "places/zabeel-hall.md" in tree
    assert "orgs/qamartech.md" in tree
    assert "timeline/2026-11.md" in tree

    # held-back.md has counts only, never secret text
    assert "family_health" in tree["held-back.md"]
    assert "credential" in tree["held-back.md"]
    assert "BarshaL0bby" not in tree["held-back.md"]

    # Forget removes fact from EVERY md file
    st.forget_source("karim", ["g081"])
    tree_after = export_md.render("karim", store=st)
    for path, content in tree_after.items():
        assert "AED 5,400" not in content, f"Forgotten fact leaked into {path}"


def test_export_zip_endpoint_and_owner_403():
    st = FakeGraphStore.from_karim_slice()
    tokens = {"karim-tok": AuthContext(role="owner-device", owner="karim"), "other-tok": AuthContext(role="owner-device", owner="other")}
    vault.configure(store=st, auth_verifier=lambda tok: tokens.get(tok or ""))

    app = FastAPI()
    app.include_router(export_md.router)
    client = TestClient(app)

    assert client.get("/v1/owners/karim/export/md.zip", headers={"Authorization": "Bearer other-tok"}).status_code == 403

    res = client.get("/v1/owners/karim/export/md.zip", headers={"Authorization": "Bearer karim-tok"})
    assert res.status_code == 200
    with zipfile.ZipFile(io.BytesIO(res.content)) as zf:
        names = set(zf.namelist())
        assert "memory/MEMORIES.md" in names
        assert "memory/people/omar-farouk.md" in names
