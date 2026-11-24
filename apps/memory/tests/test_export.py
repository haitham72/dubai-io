"""§9 markdown export: gold-slice file list, supersession, forget, held-back counts."""
from __future__ import annotations

import io
import zipfile

from fastapi import FastAPI
from fastapi.testclient import TestClient

from temporal_memory.api import export_md, vault
from temporal_memory.api.vault import AuthContext
from tests.fixtures.fake_store import FakeGraphStore

_ROOTS = (
    "USER.md",
    "NOW.md",
    "MEMORIES.md",
    "SOURCES.md",
    "MECHANICAL_INDEX.md",
    "_staging/hypotheses-to-confirm.md",
    "_staging/proposed-tree-splits.md",
)


def test_render_section9_tree_supersession_forget_and_held_back():
    st = FakeGraphStore.from_karim_slice()
    tree = export_md.render("karim", store=st)

    for req in _ROOTS:
        assert req in tree
    assert "05-home-and-money/al-barsha-rent.md" in tree
    assert "was Karim rents a 1BR flat in Al Barsha for AED 5,000 per month. until 2026-11-01" in tree[
        "05-home-and-money/al-barsha-rent.md"
    ]
    wedding = tree["06-events-and-occasions/omar-wedding.md"]
    assert "فرح عمر اتنقل لقاعة زعبيل" in wedding
    assert "You told me" in wedding

    farouk = tree["01-people/inner-circle/omar-farouk.md"]
    assert "Relation:** friend" in farouk
    assert "Tier:** T1" in farouk
    assert "3omar" in farouk
    assert "groom" in farouk
    assert "Evidence limits:" in farouk

    career = tree["02-career-and-craft/atlas-work.md"]
    assert "Omar El-Sayed joined the Atlas squad" in career
    assert "inferred" in career
    joined = next(line for line in career.splitlines() if "joined the Atlas squad" in line)
    assert "You told me" not in joined

    assert "03-projects/raseef-app.md" in tree
    assert "04-learning-and-ideas/llm-agents-course.md" in tree
    assert "07-travel-and-places/zabeel-hall.md" in tree
    assert not any(path.startswith("people/") or path.startswith("subjects/") or path.startswith("health") for path in tree)
    assert "Identity" in tree["USER.md"] and "Drive" in tree["USER.md"]
    assert "family_health" in tree["SOURCES.md"]
    assert "credential" in tree["SOURCES.md"]
    assert "BarshaL0bby" not in "\n".join(tree.values())
    assert "Nothing here is applied" in tree["_staging/proposed-tree-splits.md"]
    assert "12 or more" in tree["_staging/proposed-tree-splits.md"]
    assert "g081" in tree["MECHANICAL_INDEX.md"]

    st.forget_source("karim", ["g081"])
    tree_after = export_md.render("karim", store=st)
    for path, content in tree_after.items():
        assert "AED 5,400" not in content, f"Forgotten fact leaked into {path}"


def test_export_zip_endpoint_and_owner_403():
    st = FakeGraphStore.from_karim_slice()
    tokens = {
        "karim-tok": AuthContext(role="owner-device", owner="karim"),
        "other-tok": AuthContext(role="owner-device", owner="other"),
    }
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
    assert "memory/01-people/inner-circle/omar-farouk.md" in names
    assert "memory/USER.md" in names
    assert "memory/people/omar-farouk.md" not in names
