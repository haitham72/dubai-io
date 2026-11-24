"""Tests for `/vault/graph?view=subjects|people` and `POST /vault/people/{id}/tier` (U1c + Rule 9)."""
from __future__ import annotations

import hashlib
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from temporal_memory.api.app import create_app
from temporal_memory.core import applier
from temporal_memory.core.graph_store import PostgresGraphStore
from temporal_memory.db.db import Database, drop_test_schema, fold_text, migrate
from temporal_memory.models import Attempt, ExtractionOutput, FactEntity, Job, OutEntity, OutFact, OutLink, Owner


@pytest.fixture()
def graph_api():
    from temporal_memory.config import settings

    schema = f"tm_test_graph_{uuid4().hex[:12]}"
    db = Database(settings.test_database_url, schema=schema)
    migrate(db)
    store = PostgresGraphStore(db)
    store.create_owner(Owner(id="karim", label="Karim", kind="simulated", display_name="Karim Haddad", self_aliases=["Karim"]))
    store.create_owner(Owner(id="layla", label="Layla", kind="simulated", display_name="Layla"))

    app = create_app(db, admin_token="adm")
    client = TestClient(app)
    adm_hdr = {"Authorization": "Bearer adm"}
    tok_karim = client.post("/v1/tokens", headers=adm_hdr, json={"role": "owner-device", "owner": "karim", "label": "phone"}).json()["token"]
    tok_layla = client.post("/v1/tokens", headers=adm_hdr, json={"role": "owner-device", "owner": "layla", "label": "phone"}).json()["token"]
    tok_worker = client.post("/v1/tokens", headers=adm_hdr, json={"role": "worker", "label": "cli"}).json()["token"]
    try:
        yield {
            "db": db,
            "store": store,
            "client": client,
            "karim_hdr": {"Authorization": f"Bearer {tok_karim}"},
            "layla_hdr": {"Authorization": f"Bearer {tok_layla}"},
            "worker_hdr": {"Authorization": f"Bearer {tok_worker}"},
            "admin_hdr": adm_hdr,
        }
    finally:
        drop_test_schema(db, schema)


def test_vault_graph_both_views_rule9_and_tier_auth(graph_api):
    db: Database = graph_api["db"]
    client: TestClient = graph_api["client"]
    k_hdr = graph_api["karim_hdr"]
    l_hdr = graph_api["layla_hdr"]
    w_hdr = graph_api["worker_hdr"]
    a_hdr = graph_api["admin_hdr"]

    with db.transaction() as conn:
        conn.execute(
            "INSERT INTO entities (id, owner, kind, name, status, relation_to_user, provenance, closeness_suggested, closeness_suggested_evidence) VALUES "
            "('e_self', 'karim', 'person', 'Karim Haddad', 'active', 'self', 'user_supplied', NULL, NULL), "
            "('p_omar', 'karim', 'person', 'Omar Farouk', 'active', 'friend', 'user_supplied', 'T1', '[\"f_omar\"]'::jsonb), "
            "('p_fam_inf', 'karim', 'person', 'Uncle Sam Inferred', 'candidate', 'family', 'inferred', 'T1', '[\"f_fam_inf\"]'::jsonb), "
            "('p_proj', 'karim', 'project', 'Dubai-io Core', 'active', NULL, 'user_supplied', NULL, NULL), "
            "('p_orphan', 'karim', 'person', 'Zeta Sensitive', 'candidate', 'family', 'inferred', NULL, NULL)"
        )
        conn.execute(
            "INSERT INTO subjects (id, owner, parent_id, path, label, kind, status, provenance, sensitive_cat) VALUES "
            "('s_career', 'karim', NULL, 'career/atlas', 'Atlas Engineering', 'topic', 'active', 'user_supplied', NULL), "
            "('s_proj', 'karim', NULL, 'projects/dubai-io', 'Dubai-io', 'goal', 'active', 'user_supplied', NULL), "
            "('s_health', 'karim', NULL, 'health/sleep', 'Sleep', 'topic', 'active', 'user_supplied', 'health'), "
            "('s_faith', 'karim', NULL, 'faith/prayer', 'Prayer', 'topic', 'active', 'inferred', 'religion'), "
            "('s_fam', 'karim', NULL, 'people-family/cousin', 'Cousin Visit', 'topic', 'candidate', 'inferred', NULL)"
        )
        for rid, at, txt in [
            ("r1", "2026-11-01", "Omar Farouk reviewed Dubai-io Core"),
            ("r2", "2026-11-02", "Karim sleeps 7 hours"),
            ("r3", "2026-11-03", "Karim prayed Fajr"),
            ("r4", "2026-11-04", "Uncle Sam works in Sharjah"),
        ]:
            conn.execute(
                "INSERT INTO records (id, owner, source, at, author, text, content_hash) VALUES (%s,'karim','notes',%s,'Karim',%s,%s)",
                (rid, at, txt, hashlib.sha256(txt.encode()).hexdigest()),
            )
        for fid, txt, sid, prov in [
            ("f_omar", "Omar Farouk reviewed Dubai-io Core.", "s_proj", "user_supplied"),
            ("f_career", "Karim leads Atlas Engineering.", "s_career", "user_supplied"),
            ("f_health", "Karim sleeps 7 hours.", "s_health", "user_supplied"),
            ("f_faith", "Karim prays Fajr.", "s_faith", "inferred"),
            ("f_fam_inf", "Uncle Sam works in Sharjah.", "s_fam", "inferred"),
        ]:
            conn.execute(
                "INSERT INTO facts (id, owner, text, text_folded, subject_id, valid_from, status, provenance, content_hash) "
                "VALUES (%s,'karim',%s,%s,%s,'2026-11-01','active',%s,%s)",
                (fid, txt, fold_text(txt), sid, prov, hashlib.sha256(fid.encode()).hexdigest()),
            )
        conn.execute(
            "INSERT INTO fact_evidence (owner, fact_id, record_id) VALUES "
            "('karim','f_omar','r1'),('karim','f_career','r1'),('karim','f_health','r2'),('karim','f_faith','r3'),('karim','f_fam_inf','r4')"
        )
        conn.execute(
            "INSERT INTO fact_entities (owner, fact_id, entity_id) VALUES "
            "('karim','f_omar','p_omar'),('karim','f_omar','p_proj'),('karim','f_fam_inf','p_fam_inf')"
        )
        conn.execute(
            "INSERT INTO links (id, owner, src, rel, dst, valid_from, evidence_fact_id) VALUES "
            "('lnk_proj', 'karim', 'p_omar', 'WORKS_ON', 'p_proj', '2026-11-01', 'f_omar'), "
            "('lnk_orphan', 'karim', 'e_self', 'FAMILY_OF', 'p_orphan', '2026-11-01', NULL), "
            "('lnk_fam_inf', 'karim', 'e_self', 'FAMILY_OF', 'p_fam_inf', '2026-11-04', 'f_fam_inf')"
        )

    # Auto-promote Alserkal Cafe over 2 distinct days from a non-owner message -> must remain provenance='inferred'
    for idx, (rid, day, txt) in enumerate([
        ("r_c1", "2026-11-05", "Karim met Omar at Alserkal Cafe."),
        ("r_c2", "2026-11-08", "Karim worked at Alserkal Cafe."),
    ], 1):
        with db.transaction() as conn:
            conn.execute(
                "INSERT INTO records (id, owner, source, at, author, text, content_hash) VALUES (%s,'karim','whatsapp:work',%s,'Omar',%s,%s)",
                (rid, day, txt, hashlib.sha256(txt.encode()).hexdigest()),
            )
        j = Job(id=f"jg_{idx}", owner="karim", kind="extract.day", priority=1, pool="internal", input_ref=[rid], input_version=0, context_hash=f"cg{idx}", prompt_version="extract@3", day=day, state="leased")
        a = Attempt(
            job_id=j.id, attempt_no=1, fence_token=f"fg{idx}", worker_id="w1", worker_kind="internal-cloud", model="haiku", prompt_version="extract@3",
            output=ExtractionOutput(
                entities=[OutEntity(ref="new:Alserkal Cafe", kind="place", aliases=[], relation_to_user=None)],
                facts=[OutFact(text=txt, text_orig=None, subject_path="projects/dubai-io", entities=[FactEntity("new:Alserkal Cafe")], op="new", target=None, valid_from=day, evidence=[rid], sensitive=None)],
                links=[],
            ),
        )
        applier.apply("karim", j, a, db=db)

    # 1. Cross-owner & worker graph -> 403
    assert client.get("/v1/owners/karim/vault/graph", headers=l_hdr).status_code == 403
    assert client.get("/v1/owners/karim/vault/graph", headers=w_hdr).status_code == 403

    # 2. Subjects view: no health/faith/inferred people-family cluster, true counts
    gs = client.get("/v1/owners/karim/vault/graph", headers=k_hdr, params={"view": "subjects"}).json()
    assert gs["view"] == "subjects"
    assert gs["center_id"] == "e_self"
    cluster_groups = {n["group"] for n in gs["nodes"] if n["kind"] == "cluster"}
    assert "career" in cluster_groups and "projects" in cluster_groups
    assert "health" not in cluster_groups and "faith" not in cluster_groups and "people-family" not in cluster_groups
    assert all("Sleep" not in n["label"] and "Prayer" not in n["label"] and "Cousin" not in n["label"] for n in gs["nodes"])

    # 3. People view: includes projects, drops orphans/inferred family, tier stays None until confirmed
    gp = client.get("/v1/owners/karim/vault/graph", headers=k_hdr, params={"view": "people", "max_per_group": 1}).json()
    node_ids = {n["id"] for n in gp["nodes"]}
    labels = {n["label"] for n in gp["nodes"]}
    assert "Omar Farouk" in labels and "Dubai-io Core" in labels and "Alserkal Cafe" in labels
    assert "Zeta Sensitive" not in labels and "Uncle Sam Inferred" not in labels
    assert gp["counts"]["people"] == 1 and gp["counts"]["places"] == 1 and gp["counts"]["projects"] == 1
    assert gp["counts"]["relations"] == 1  # only lnk_proj; orphan & inferred family links excluded!
    assert all(e["src"] in node_ids and e["dst"] in node_ids for e in gp["edges"])

    omar_node = next(n for n in gp["nodes"] if n["id"] == "p_omar")
    assert omar_node["tier"] is None
    assert omar_node["closeness_suggested"] == "T1"
    alserkal_node = next(n for n in gp["nodes"] if n["label"] == "Alserkal Cafe")
    assert alserkal_node["provenance"] == "inferred"
    assert alserkal_node["review_state"] == "pending_review"

    # 4. POST /tier strict owner-auth only (admin/worker/cross-owner -> 403)
    assert client.post("/v1/owners/karim/vault/people/p_omar/tier", headers=a_hdr, json={"tier": "T1"}).status_code == 403
    assert client.post("/v1/owners/karim/vault/people/p_omar/tier", headers=w_hdr, json={"tier": "T1"}).status_code == 403
    assert client.post("/v1/owners/karim/vault/people/p_omar/tier", headers=l_hdr, json={"tier": "T1"}).status_code == 403

    res_t1 = client.post("/v1/owners/karim/vault/people/p_omar/tier", headers=k_hdr, json={"tier": "T1"})
    assert res_t1.status_code == 200
    assert res_t1.json()["closeness_tier"] == "T1"
    assert res_t1.json()["tier_confirmed_at"]

    gp2 = client.get("/v1/owners/karim/vault/graph", headers=k_hdr, params={"view": "people"}).json()
    omar_after = next(n for n in gp2["nodes"] if n["id"] == "p_omar")
    assert omar_after["tier"] == "T1"
