"""Postgres integration & 20k-fact latency tests for U1c SQL retrieval and privacy invalidation."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import random
import statistics
import time
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from temporal_memory.api.app import create_app
from temporal_memory.core.graph_store import PostgresGraphStore
from temporal_memory.db.db import Database, drop_test_schema, fold_text, migrate
from temporal_memory.live import context as live_ctx
from temporal_memory.models import Candidate, Fact, FactEntity, GraphStoreFull, Owner, Record, Subject


@pytest.fixture()
def pg_db():
    from temporal_memory.config import settings

    schema = f"tm_test_u1c_{uuid4().hex[:12]}"
    db = Database(settings.test_database_url, schema=schema)
    migrate(db)
    try:
        yield db
    finally:
        drop_test_schema(db, schema)


def test_postgres_implements_graph_store_full_channels_and_cursors(pg_db: Database):
    store = PostgresGraphStore(pg_db)
    full: GraphStoreFull = store
    store.create_owner(Owner(id="karim", label="Karim", kind="simulated", display_name="Karim Haddad", self_aliases=["Karim", "Kimo"]))

    with pg_db.transaction() as conn:
        conn.execute(
            "INSERT INTO subjects (id, owner, parent_id, path, label, kind, status, provenance) VALUES "
            "('th_career', 'karim', NULL, 'career', 'Career', 'theme', 'active', 'user_supplied'), "
            "('s_atlas', 'karim', 'th_career', 'career/atlas', 'Atlas Project', 'topic', 'active', 'user_supplied'), "
            "('th_health', 'karim', NULL, 'health', 'Health', 'theme', 'active', 'inferred'), "
            "('s_sleep', 'karim', 'th_health', 'health/sleep', 'Sleep', 'topic', 'active', 'inferred')"
        )
        with pg_db.connection() as _:
            pass
        # Upsert records via store helper outside or inside? Just SQL here
        for rid, src, at, txt in [
            ("r1", "messenger:c1", "2026-11-20T09:00:00Z", "Sherif works at NexaPay on payments"),
            ("r2", "messenger:c2", "2026-11-21T09:00:00Z", "NexaPay team hired a backend lead in Dubai"),
            ("r3", "notes:a", "2026-11-04T08:00:00Z", "LLM Agents cohort starts Nov 16"),
            ("r4", "notes:b", "2026-11-22T09:00:00Z", "Sleep tracker shows 6h average"),
        ]:
            conn.execute(
                "INSERT INTO records (id, owner, source, at, author, text, content_hash) VALUES (%s,'karim',%s,%s,'Karim',%s,%s)",
                (rid, src, at, txt, hashlib.sha256(txt.encode()).hexdigest()),
            )
        conn.execute(
            "INSERT INTO entities (id, owner, kind, name, status, provenance) VALUES "
            "('e_sherif', 'karim', 'person', 'Sherif', 'active', 'user_supplied'), "
            "('e_nexapay', 'karim', 'org', 'NexaPay', 'active', 'user_supplied')"
        )
        conn.execute(
            "INSERT INTO entity_aliases (owner, entity_id, alias, alias_folded, source) VALUES "
            "('karim', 'e_sherif', 'Sherif', 'sherif', 'user'), "
            "('karim', 'e_nexapay', 'NexaPay', 'nexapay', 'user')"
        )
        for fid, txt, orig, sid, vf, prov in [
            ("f1", "Sherif works at NexaPay on payments.", None, "s_atlas", "2026-11-20", "user_supplied"),
            ("f2", "NexaPay team hired a backend lead in Dubai.", None, "s_atlas", "2026-11-21", "user_supplied"),
            ("f3", "LLM agents cohort starts Nov 16.", "كورس الوكلاء الذكية يبدأ ١٦ نوفمبر", "s_atlas", "2026-11-04", "user_supplied"),
            ("f_sens", "Karim averages 6 hours of sleep.", None, "s_sleep", "2026-11-22", "inferred"),
        ]:
            conn.execute(
                "INSERT INTO facts (id, owner, text, text_orig, text_folded, subject_id, valid_from, status, provenance, content_hash) "
                "VALUES (%s,'karim',%s,%s,%s,%s,%s,'active',%s,%s)",
                (fid, txt, orig, fold_text(f"{txt} {orig or ''}"), sid, vf, prov, hashlib.sha256(fid.encode()).hexdigest()),
            )
        conn.execute("INSERT INTO fact_evidence (owner, fact_id, record_id) VALUES ('karim','f1','r1'),('karim','f2','r2'),('karim','f3','r3'),('karim','f_sens','r4')")
        conn.execute("INSERT INTO fact_entities (owner, fact_id, entity_id) VALUES ('karim','f1','e_sherif'),('karim','f1','e_nexapay'),('karim','f2','e_nexapay')")
        conn.execute("INSERT INTO links (id, owner, src, rel, dst, valid_from, evidence_fact_id) VALUES ('l1','karim','e_sherif','WORKS_AT','e_nexapay','2026-11-20','f1')")

    # 1. Exact get_facts order + dedupe
    got = full.get_facts("karim", ["f3", "missing", "f1", "f3"])
    assert [f.id for f in got] == ["f3", "f1"]

    # 2. Arabic text_orig search + FTS
    ar_cands = full.search_candidates("karim", "متى يبدأ كورس الوكلاء الذكية؟", limit=10)
    assert any(c.fact_id == "f3" for c in ar_cands)

    # 3. 1-hop entity link expansion: querying "Sherif" surfaces f2 via NexaPay link!
    hop_cands = full.search_candidates("karim", "Who did Sherif's company hire?", limit=10)
    assert [c.fact_id for c in hop_cands[:2]] and "f2" in [c.fact_id for c in hop_cands]

    # 4. source_prefix strict filter before limit
    c1_only = full.search_candidates("karim", "NexaPay", source_prefix="messenger:c1", limit=10)
    assert [c.fact_id for c in c1_only] == ["f1"]

    # 5. Sensitive inferred sleep fact excluded from search_candidates
    sens_cands = full.search_candidates("karim", "sleep tracker", limit=10)
    assert all(c.fact_id != "f_sens" for c in sens_cands)

    # 6. iter_visible_facts keyset pagination + date bounds + bump_privacy_revision
    paged = list(full.iter_visible_facts("karim", date_from="2026-11-20", date_to="2026-11-21", page_size=1))
    assert [f.id for f in paged] == ["f2", "f1"]
    assert full.fact_counts_by_subject("karim")["s_atlas"] == 3
    assert full.bump_privacy_revision("karim") == 1


def test_20k_facts_needle_and_p95_under_150ms_inproc_and_http(pg_db: Database):
    store = PostgresGraphStore(pg_db)
    store.create_owner(Owner(id="k20", label="K20", kind="demo", display_name="Karim Haddad", self_aliases=["Karim"]))

    rng = random.Random(11)
    names = ["Omar", "Layla", "Karim", "Sara", "Yousef", "Huda", "Rami", "Noor"] + [f"Person{i}" for i in range(92)]
    places = ["Business Bay", "JLT", "Marina", "Deira", "DIFC"]
    orgs = ["Emirates NBD", "Careem", "Noon", "DEWA", "Etisalat"]
    verbs = ["works at", "met with", "visited", "joined", "reviewed"]
    roots = ["career/atlas", "learning/ai", "projects/raseef", "events/dining", "home-money/rent", "travel/trips"]

    n = 20_000
    with pg_db.transaction() as conn:
        cur = conn.cursor()
        with cur.copy("COPY entities (id, owner, kind, name, status, provenance) FROM STDIN") as cp:
            cp.write_row(("e_self", "k20", "person", "Karim Haddad", "active", "user_supplied"))
            for i, nm in enumerate(names):
                cp.write_row((f"e{i}", "k20", "person", nm, "active", "user_supplied"))
        with cur.copy("COPY entity_aliases (owner, entity_id, alias, alias_folded) FROM STDIN") as cp:
            for i, nm in enumerate(names):
                cp.write_row(("k20", f"e{i}", nm, fold_text(nm)))
        with cur.copy("COPY subjects (id, owner, path, label, kind, status, provenance) FROM STDIN") as cp:
            for j, p in enumerate(roots):
                cp.write_row((f"s{j}", "k20", p, p.split("/")[1].title(), "topic", "active", "user_supplied"))
        with cur.copy("COPY records (id, owner, source, at, author, text, content_hash) FROM STDIN") as cp:
            for k in range(n):
                day = f"20{20 + (k * 6 // n):02d}-{1 + k % 12:02d}-{1 + k % 28:02d}"
                txt = f"{names[k % len(names)]} {verbs[k % len(verbs)]} {orgs[k % len(orgs)]} in {places[k % len(places)]} note {k}"
                cp.write_row((f"r{k}", "k20", "whatsapp", day, names[k % len(names)], txt, f"h_{k}"))
            cp.write_row(("r_needle", "k20", "gmail", "2015-01-01", "clinic", "zanzibarite dentist recall", "h_needle"))
        with cur.copy("COPY facts (id, owner, text, text_folded, subject_id, valid_from, status, provenance, content_hash) FROM STDIN") as cp:
            for k in range(n):
                day = f"20{20 + (k * 6 // n):02d}-{1 + k % 12:02d}-{1 + k % 28:02d}"
                txt = f"{names[k % len(names)]} {verbs[k % len(verbs)]} {orgs[k % len(orgs)]} in {places[k % len(places)]} note {k}"
                cp.write_row((f"f{k}", "k20", txt, fold_text(txt), f"s{rng.randrange(len(roots))}", day, "active", "user_supplied", f"fh_{k}"))
            cp.write_row(("f_needle", "k20", "Karim had a zanzibarite dentist recall", "karim had a zanzibarite dentist recall", "s3", "2015-01-01", "active", "user_supplied", "fh_needle"))
        with cur.copy("COPY fact_entities (owner, fact_id, entity_id) FROM STDIN") as cp:
            for k in range(n):
                cp.write_row(("k20", f"f{k}", f"e{k % len(names)}"))
            cp.write_row(("k20", "f_needle", "e_self"))
        with cur.copy("COPY fact_evidence (owner, fact_id, record_id) FROM STDIN") as cp:
            for k in range(n):
                cp.write_row(("k20", f"f{k}", f"r{k}"))
            cp.write_row(("k20", "f_needle", "r_needle"))
        conn.execute("UPDATE owners SET facts_version = 1, alias_version = 1 WHERE id = 'k20'")
    with pg_db.connection() as conn:
        conn.execute("ANALYZE")

    live_ctx.invalidate_alias_cache()

    # In-process cold + warm (cache bypass on different queries + repeated) + 2015 needle
    needle_inproc = store.search_candidates("k20", "zanzibarite dentist", limit=10)
    assert any(c.fact_id == "f_needle" for c in needle_inproc)

    inproc_ctx_lat: list[float] = []
    queries = [f"Omar Careem DIFC query {i}" for i in range(100)]
    for q in queries:
        t0 = time.perf_counter()
        out = live_ctx.context_pack("k20", q, max_tokens=1500, store=store)
        inproc_ctx_lat.append((time.perf_counter() - t0) * 1000.0)
        assert out["facts"]
    inproc_p95 = statistics.quantiles(inproc_ctx_lat, n=20)[18]
    assert inproc_p95 < 150.0, f"In-process 20k context_pack cold-query p95={inproc_p95:.2f}ms >= 150ms"

    # HTTP route checks (context, search, graph subjects, graph people, 2015 needle)
    app = create_app(pg_db, admin_token="adm")
    client = TestClient(app)
    tok = client.post("/v1/tokens", headers={"Authorization": "Bearer adm"}, json={"role": "owner-device", "owner": "k20", "label": "bench"}).json()["token"]
    hdrs = {"Authorization": f"Bearer {tok}"}

    srch_needle = client.get("/v1/owners/k20/search", headers=hdrs, params={"q": "zanzibarite", "limit": 10})
    ctx_needle = client.post("/v1/owners/k20/context", headers=hdrs, json={"text": "zanzibarite dentist"})
    assert srch_needle.status_code == 200 and any(f["id"] == "f_needle" for f in srch_needle.json()["facts"])
    assert ctx_needle.status_code == 200 and any(f["id"] == "f_needle" for f in ctx_needle.json()["facts"])

    http_ctx, http_srch, http_gs, http_gp = [], [], [], []
    base_queries = ["Where does Omar work?", "What did Layla say about Careem?", "Who visited DIFC?", "Tell me about Sara at Etisalat", "Rami Noon Marina"]
    for i in range(100):
        q = base_queries[i % len(base_queries)]
        t0 = time.perf_counter()
        assert client.post("/v1/owners/k20/context", headers=hdrs, json={"text": q}).status_code == 200
        http_ctx.append((time.perf_counter() - t0) * 1000.0)

        t0 = time.perf_counter()
        assert client.get("/v1/owners/k20/search", headers=hdrs, params={"q": "Careem", "limit": 20}).status_code == 200
        http_srch.append((time.perf_counter() - t0) * 1000.0)

        t0 = time.perf_counter()
        assert client.get("/v1/owners/k20/vault/graph", headers=hdrs, params={"view": "subjects"}).status_code == 200
        http_gs.append((time.perf_counter() - t0) * 1000.0)

        t0 = time.perf_counter()
        assert client.get("/v1/owners/k20/vault/graph", headers=hdrs, params={"view": "people"}).status_code == 200
        http_gp.append((time.perf_counter() - t0) * 1000.0)

    for label, samples in [("context", http_ctx), ("search", http_srch), ("graph_subjects", http_gs), ("graph_people", http_gp)]:
        p95 = statistics.quantiles(samples, n=20)[18]
        assert p95 < 150.0, f"HTTP 20k {label} p95={p95:.2f}ms exceeded 150ms"

    # Privacy revision bump alone invalidates cached context_pack across processes
    warm1 = client.post("/v1/owners/k20/context", headers=hdrs, json={"text": "zanzibarite dentist"}).json()
    assert any(f["id"] == "f_needle" for f in warm1["facts"])
    with pg_db.transaction() as conn:
        conn.execute("UPDATE facts SET erased_at = now() WHERE owner = 'k20' AND id = 'f_needle'")
        conn.execute("UPDATE owners SET privacy_revision = privacy_revision + 1 WHERE id = 'k20'")
    warm2 = client.post("/v1/owners/k20/context", headers=hdrs, json={"text": "zanzibarite dentist"}).json()
    assert all(f["id"] != "f_needle" for f in warm2["facts"])
