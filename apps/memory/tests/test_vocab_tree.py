"""Unit and Postgres integration tests for E10 data-driven topic tree + learned vocab."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest

from temporal_memory.api.app import create_app
from temporal_memory.core.applier import apply
from temporal_memory.core.bridge_store import resolve_fact
from temporal_memory.core.extract import OUTPUT_SCHEMA, _parse_extraction_output, build_system_prompt
from temporal_memory.core.graph_store import PostgresGraphStore
from temporal_memory.core.retrieval import compute_subject_salience_sql, invalidate_learned_cache, search_candidates
from temporal_memory.core.subject_aliases import aliases_for_text
from temporal_memory.db import db as db_module
from temporal_memory.db.db import create_test_schema, drop_test_schema, fold_text
from temporal_memory.models import Attempt, Job, NewTerm, OutFact, Owner
from temporal_memory.models import ExtractionOutput
from temporal_memory.vocab import (
    DEFAULT_TREE_PATH,
    WEIGHT_FLOOR,
    VocabValidationError,
    get_vocab,
    load_vocab,
)
from temporal_memory.vocab.proposals import (
    apply_new_terms,
    get_proposal_stats,
    list_owner_learned_terms,
    load_owner_learned_index,
    reset_proposal_stats,
)


@pytest.fixture()
def pg():
    schema_db, schema = create_test_schema()
    prev = db_module._DEFAULT_DB
    db_module._DEFAULT_DB = schema_db
    invalidate_learned_cache()
    try:
        yield schema_db
    finally:
        invalidate_learned_cache()
        db_module._DEFAULT_DB = prev
        drop_test_schema(schema_db, schema)


def _seed_owner(conn, owner: str) -> None:
    conn.execute(
        "INSERT INTO owners (id, label, kind) VALUES (%s, %s, 'simulated') ON CONFLICT DO NOTHING",
        (owner, owner),
    )


def _seed_record(conn, owner: str, rid: str, text: str, *, source: str = "messenger:c1", at: str = "2026-11-20T09:00:00Z") -> None:
    conn.execute(
        "INSERT INTO records (id, owner, source, at, author, text, content_hash) VALUES (%s,%s,%s,%s,%s,%s,%s)",
        (rid, owner, source, at, owner, text, hashlib.sha256(f"{owner}:{rid}:{text}".encode()).hexdigest()),
    )


def _seed_fact(
    conn,
    owner: str,
    fid: str,
    text: str,
    rid: str,
    *,
    text_orig: str | None = None,
    subject_id: str | None = None,
    valid_from: str = "2026-11-20",
    provenance: str = "user_supplied",
) -> None:
    folded = fold_text(f"{text} {text_orig or ''}")
    conn.execute(
        "INSERT INTO facts (id, owner, text, text_orig, text_folded, subject_id, valid_from, status, provenance, content_hash) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,'active',%s,%s)",
        (fid, owner, text, text_orig, folded, subject_id, valid_from, provenance, hashlib.sha256(fid.encode()).hexdigest()),
    )
    conn.execute(
        "INSERT INTO fact_evidence (owner, fact_id, record_id) VALUES (%s,%s,%s)",
        (owner, fid, rid),
    )


def _make_job(owner: str, rids: list[str], *, jid: str = "j1") -> Job:
    return Job(
        id=jid,
        owner=owner,
        kind="extract.day",
        priority=1,
        pool="internal",
        input_ref=rids,
        input_version=0,
        context_hash="ctx1",
        prompt_version="extract@4",
        day="2026-11-20",
        state="submitted",
        attempt_no=1,
        fence_token="fence-1",
    )


def _make_attempt(output: ExtractionOutput, *, jid: str = "j1") -> Attempt:
    return Attempt(
        job_id=jid,
        attempt_no=1,
        fence_token="fence-1",
        worker_id="w1",
        worker_kind="internal-cloud",
        model="claude-haiku-4-5-20251001",
        prompt_version="extract@4",
        output=output,
    )


# ------------------------------------------------------------------ unit validation


def test_default_vocab_loads_cleanly_and_contains_no_fixture_names():
    raw_text = DEFAULT_TREE_PATH.read_text(encoding="utf-8")
    low = fold_text(raw_text)
    forbidden = (
        "fitzone",
        "peakform",
        "autohub",
        "camry",
        "testflight",
        "samsung",
        "macbook",
        "ipad",
        "nadia",
        "tariq",
        "omar",
        "karim",
        "haitham",
        "الوكلاء",
    )
    for word in forbidden:
        assert word not in low, f"forbidden fixture word leaked into curated tree.json: {word}"

    tree = get_vocab()
    assert tree.by_path["health"].sensitive is True
    assert tree.by_path["health"].blocks_proposals is True
    # Sensitivity / proposal-blocking inherited by descendants:
    health_children = tree.children_by_parent.get("health", ())
    assert health_children
    for child_path in health_children:
        assert tree.by_path[child_path].sensitive is True
        assert tree.by_path[child_path].blocks_proposals is True


@pytest.mark.parametrize(
    "bad_payload",
    [
        {"nodes": [], "lexicon": []},
        {"nodes": [{"path": "career", "cluster": "invalid_cluster", "label": "X"}], "lexicon": []},
        {"nodes": [{"path": "career/a", "cluster": "career", "parent": "missing_parent", "label": "A"}], "lexicon": []},
        {
            "nodes": [
                {"path": "career", "cluster": "career", "label": "C"},
                {"path": "career", "cluster": "career", "label": "Dup"},
            ],
            "lexicon": [],
        },
        {
            "nodes": [
                {"path": "a", "cluster": "career", "parent": "b", "label": "A"},
                {"path": "b", "cluster": "career", "parent": "a", "label": "B"},
            ],
            "lexicon": [],
        },
    ],
)
def test_invalid_vocab_raises_validation_error(tmp_path: Path, bad_payload: dict):
    p = tmp_path / "bad_tree.json"
    p.write_text(json.dumps(bad_payload), encoding="utf-8")
    with pytest.raises(VocabValidationError):
        load_vocab(p)


def test_tree_expansion_descendants_lexicon_and_no_sibling_leak():
    tree = get_vocab()
    # Parent -> child/grandchild expansion: "sport" & Arabic "رياضة" include surfing without sibling pollution.
    _, sport_exp = tree.expand_terms(["sport"], max_terms=60)
    assert "surfing" in sport_exp or "surf" in sport_exp
    _, ar_sport_exp = tree.expand_terms(["رياضة"], max_terms=60)
    assert "surfing" in ar_sport_exp or "sport" in ar_sport_exp

    # Sibling non-expansion: querying "surfing" must NOT expand sibling "padel" or parent "sports".
    _, surf_exp = tree.expand_terms(["surfing"], max_terms=40)
    assert "padel" not in surf_exp
    assert "sports" not in surf_exp

    # Bidirectional lexicon: Arabizi/Arabic "بكام" -> price/cost/budget.
    _, bk_exp = tree.expand_terms(["بكام"], max_terms=40)
    assert "price" in bk_exp or "cost" in bk_exp

    # subject_aliases delegates cleanly without fixture brands
    aliases = aliases_for_text("household/tenancy", "monthly rent payment")
    assert "ايجار" in aliases or "rent" in aliases

    # Extract schema and prompt expose new_terms while keeping prompt compact (no full tree dump)
    assert "new_terms" in OUTPUT_SCHEMA["properties"]
    sys_prompt = build_system_prompt(None)
    assert "new_terms" in sys_prompt
    # Compact prompt rule only; never dump curated tree branches/subtopics into the system prompt.
    assert len(sys_prompt) < 5500
    assert "surf school" not in sys_prompt and "padel" not in sys_prompt
    parsed = _parse_extraction_output(
        {
            "entities": [],
            "facts": [],
            "links": [],
            "new_terms": [{"term": "FitZone", "is_a": "fitness", "evidence": ["r1"]}],
        }
    )
    assert parsed.new_terms == [NewTerm(term="FitZone", is_a="fitness", evidence=["r1"])]


# ------------------------------------------------------------------ Postgres integration


def test_retrieval_tree_lexicon_and_learned_owner_isolation(pg, monkeypatch):
    monkeypatch.setenv("TM_SEMANTIC", "0")
    with pg.transaction() as conn:
        _seed_owner(conn, "owner_a")
        _seed_owner(conn, "owner_b")
        _seed_record(conn, "owner_a", "ra1", "Joined a coastal surf school near the beach.")
        _seed_record(conn, "owner_a", "ra2", "The apartment rent price is 1200 USD per month.")
        _seed_record(conn, "owner_a", "ra3", "Book a Friday padel court with friends.")
        _seed_record(conn, "owner_a", "ra4", "FitZone renewal paid for 6 months.")
        _seed_record(conn, "owner_b", "rb1", "Bought a FitZone bottle online.")
        conn.execute(
            "INSERT INTO subjects (id, owner, parent_id, path, label, kind, status, provenance) VALUES "
            "('s_surf', 'owner_a', NULL, 'events/coastal', 'Coastal', 'topic', 'active', 'user_supplied'), "
            "('s_price', 'owner_a', NULL, 'home-money/monthly', 'Monthly', 'topic', 'active', 'user_supplied'), "
            "('s_padel', 'owner_a', NULL, 'events/friday', 'Friday', 'topic', 'active', 'user_supplied'), "
            "('s_fit', 'owner_a', NULL, 'events/clubs', 'Clubs', 'topic', 'active', 'user_supplied'), "
            "('s_b', 'owner_b', NULL, 'home-money/bottles', 'Bottles', 'topic', 'active', 'user_supplied')"
        )
        _seed_fact(conn, "owner_a", "fa_surf", "Owner joined a coastal surf school.", "ra1", subject_id="s_surf")
        _seed_fact(conn, "owner_a", "fa_price", "Monthly rent price is $1200.", "ra2", subject_id="s_price")
        _seed_fact(conn, "owner_a", "fa_padel", "Booked a Friday padel match.", "ra3", subject_id="s_padel")
        _seed_fact(conn, "owner_a", "fa_fitzone", "FitZone renewal active through May.", "ra4", subject_id="s_fit")
        _seed_fact(conn, "owner_b", "fb_fitzone", "FitZone bottle purchase.", "rb1", subject_id="s_b")

    # 1. Descendant expansion without exact keyword: "sport" -> surf, "رياضة" -> surf
    hits_sport = [c.fact_id for c in search_candidates(pg, "owner_a", "sport")]
    assert "fa_surf" in hits_sport
    hits_ar_sport = [c.fact_id for c in search_candidates(pg, "owner_a", "رياضة")]
    assert "fa_surf" in hits_ar_sport

    # 2. Sibling non-expansion: querying "surfing" must NOT match sibling padel
    hits_surf = [c.fact_id for c in search_candidates(pg, "owner_a", "surfing")]
    assert "fa_surf" in hits_surf
    assert "fa_padel" not in hits_surf

    # 3. Lexicon expansion: "بكام" matches price fact
    hits_price = [c.fact_id for c in search_candidates(pg, "owner_a", "بكام")]
    assert "fa_price" in hits_price

    # 4. Before learning, querying "sport" or "gym" does NOT know about "FitZone"
    assert "fa_fitzone" not in hits_sport
    assert "fa_fitzone" not in [c.fact_id for c in search_candidates(pg, "owner_a", "gym")]

    # 5. Apply extraction with learned term ONLY on owner_a
    out = ExtractionOutput(
        entities=[],
        facts=[
            OutFact(
                text="FitZone 6-month membership paid.",
                text_orig=None,
                subject_path="events/clubs",
                entities=[],
                op="new",
                target=None,
                valid_from="2026-11-20",
                evidence=["ra4"],
                sensitive=None,
            )
        ],
        links=[],
        new_terms=[NewTerm(term="FitZone", is_a="gym", evidence=["ra4"])],
    )
    verdict = apply("owner_a", _make_job("owner_a", ["ra4"], jid="j_learn_a"), _make_attempt(out, jid="j_learn_a"), db=pg)
    assert verdict.ok

    # Owner A sees fa_fitzone when querying "gym", "sport", or "رياضة"
    assert "fa_fitzone" in [c.fact_id for c in search_candidates(pg, "owner_a", "gym")]
    assert "fa_fitzone" in [c.fact_id for c in search_candidates(pg, "owner_a", "sport")]
    assert "fa_fitzone" in [c.fact_id for c in search_candidates(pg, "owner_a", "رياضة")]

    # Owner B remains isolated (never gets FitZone expanded from owner A's learned_terms)
    assert "fb_fitzone" not in [c.fact_id for c in search_candidates(pg, "owner_b", "gym")]
    assert "fb_fitzone" not in [c.fact_id for c in search_candidates(pg, "owner_b", "sport")]


def test_proposal_validation_drops_chaining_duplicates_and_api_endpoint(pg):
    reset_proposal_stats()
    with pg.transaction() as conn:
        _seed_owner(conn, "o1")
        _seed_owner(conn, "o2")
        _seed_record(conn, "o1", "r1", "Signed up at FitZone and started FlowCore.")
        _seed_record(conn, "o1", "r2", "Renewed FitZone membership again.")
        _seed_record(conn, "o2", "r_other", "Belongs to another owner.")

    # Custom ambiguous tree to verify ambiguous rejection alongside real tree checks
    amb_tree = load_vocab(DEFAULT_TREE_PATH)

    with pg.transaction() as conn:
        # Chained attachment: FitZone -> gym, FlowCore -> FitZone
        res1 = apply_new_terms(
            conn,
            "o1",
            [
                NewTerm(term="FitZone", is_a="gym", evidence=["r1"]),
                NewTerm(term="FlowCore", is_a="FitZone", evidence=["r1"]),
                # Rejection cases:
                NewTerm(term="FooBar", is_a="nonexistent_branch_xyz", evidence=["r1"]),  # no_branch
                NewTerm(term="BazQux", is_a="gym", evidence=["r_other"]),              # no_source (wrong owner)
                NewTerm(term="Ghost", is_a="gym", evidence=[]),                         # no_source (empty)
                NewTerm(term="ClinicX", is_a="health", evidence=["r1"]),                # rule9 (blocked root)
                NewTerm(term="family secret", is_a="family", evidence=["r1"]),          # rule9 (family)
                NewTerm(term="otp token", is_a="software", evidence=["r1"]),            # rule9 (sensitive word)
                NewTerm(term="padel", is_a="sport", evidence=["r1"]),                   # curated_clash
                NewTerm(term="price", is_a="budget", evidence=["r1"]),                  # curated_clash (lexicon)
            ],
            {"r1", "r2", "r_other"},
            vocab=amb_tree,
        )
        assert res1["kept"] == 2
        assert res1["no_branch"] == 1
        assert res1["no_source"] == 2
        assert res1["rule9"] == 3
        assert res1["curated_clash"] == 2

        # Second sighting adds r2 source without duplicating learned_terms row
        res2 = apply_new_terms(
            conn,
            "o1",
            [NewTerm(term="FitZone", is_a="gym", evidence=["r2"])],
            {"r2"},
            vocab=amb_tree,
        )
        assert res2["kept"] == 1
        items = list_owner_learned_terms(conn, "o1")
        fit = [it for it in items if it["term_folded"] == "fitzone"][0]
        assert fit["source_record_ids"] == ["r1", "r2"]
        flow = [it for it in items if it["term_folded"] == "flowcore"][0]
        assert flow["parent_path"] == "lifestyle/sports/gym/fitzone"

    # Separate ambiguous tree test
    amb_json = {
        "nodes": [
            {"path": "career", "cluster": "career", "label": "Work", "aliases": ["track"]},
            {"path": "lifestyle", "cluster": "events", "label": "Sport", "aliases": ["track"]},
        ],
        "lexicon": [],
    }
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        tp = Path(td) / "amb.json"
        tp.write_text(json.dumps(amb_json), encoding="utf-8")
        custom_tree = load_vocab(tp)
        with pg.transaction() as conn:
            res_amb = apply_new_terms(
                conn,
                "o1",
                [NewTerm(term="SprintClub", is_a="track", evidence=["r1"])],
                {"r1"},
                vocab=custom_tree,
            )
            assert res_amb["ambiguous"] == 1
            assert res_amb["kept"] == 0

    tot = get_proposal_stats()
    assert tot["kept"] == 3
    assert tot["ambiguous"] == 1

    # HTTP GET /v1/owners/{owner}/vocab/learned authorization & response
    app = create_app(pg, admin_token="adm")
    client = TestClient(app)
    tok_o1 = client.post("/v1/tokens", headers={"Authorization": "Bearer adm"}, json={"role": "owner-device", "owner": "o1"}).json()["token"]
    tok_o2 = client.post("/v1/tokens", headers={"Authorization": "Bearer adm"}, json={"role": "owner-device", "owner": "o2"}).json()["token"]
    tok_wk = client.post("/v1/tokens", headers={"Authorization": "Bearer adm"}, json={"role": "worker", "label": "w"}).json()["token"]

    r_ok = client.get("/v1/owners/o1/vocab/learned", headers={"Authorization": f"Bearer {tok_o1}"})
    assert r_ok.status_code == 200, r_ok.text
    body = r_ok.json()
    assert body["count"] == 2
    assert {it["term_folded"] for it in body["items"]} == {"fitzone", "flowcore"}

    assert client.get("/v1/owners/o1/vocab/learned", headers={"Authorization": f"Bearer {tok_o2}"}).status_code == 403
    assert client.get("/v1/owners/o1/vocab/learned", headers={"Authorization": f"Bearer {tok_wk}"}).status_code == 403


def test_d18_weight_lowering_floor_ordering_and_no_deletion(pg):
    today = "2026-11-25"
    with pg.transaction() as conn:
        _seed_owner(conn, "o_d18")
        _seed_record(conn, "o_d18", "r_spin", "Tried SpinZone studio.")
        _seed_record(conn, "o_d18", "r_fit_a", "FitZone day pass bought.")
        _seed_record(conn, "o_d18", "r_fit_b", "Renewed FitZone annual pass.")
        _seed_record(conn, "o_d18", "r_low", "Checked LowClub schedule.")
        conn.execute(
            "INSERT INTO subjects (id, owner, parent_id, path, label, kind, status, provenance, user_confirmed_at) VALUES "
            "('s_inf', 'o_d18', NULL, 'lifestyle/inferred_hobby', 'Inferred Hobby', 'topic', 'candidate', 'inferred', NULL), "
            "('s_conf', 'o_d18', NULL, 'lifestyle/confirmed_hobby', 'Confirmed Hobby', 'topic', 'candidate', 'inferred', now()), "
            "('s_user', 'o_d18', NULL, 'lifestyle/user_hobby', 'User Hobby', 'topic', 'active', 'user_supplied', NULL)"
        )
        conn.execute(
            "INSERT INTO subject_aliases (owner, subject_id, alias, alias_folded) VALUES "
            "('o_d18', 's_inf', 'Inferred Hobby', 'inferred hobby')"
        )
        _seed_fact(conn, "o_d18", "f_spin", "Visited SpinZone studio.", "r_spin", subject_id="s_inf", valid_from=today, provenance="inferred")
        _seed_fact(conn, "o_d18", "f_low", "Checked LowClub gym hours.", "r_low", subject_id="s_inf", valid_from=today, provenance="inferred")
        _seed_fact(conn, "o_d18", "f_fit_a", "Bought FitZone day pass.", "r_fit_a", subject_id="s_conf", valid_from=today, provenance="inferred")
        _seed_fact(conn, "o_d18", "f_fit_b", "Renewed FitZone annual pass.", "r_fit_b", subject_id="s_user", valid_from=today, provenance="user_supplied")

        apply_new_terms(
            conn,
            "o_d18",
            [
                NewTerm(term="SpinZone", is_a="gym", evidence=["r_spin"]),
                NewTerm(term="LowClub", is_a="gym", evidence=["r_low"]),
                NewTerm(term="FitZone", is_a="gym", evidence=["r_fit_a", "r_fit_b"]),
            ],
            {"r_spin", "r_fit_a", "r_fit_b", "r_low"},
        )
        # Snapshot initial row counts (D18: nothing may be deleted).
        init_lt = conn.execute("SELECT count(*)::int AS c FROM learned_terms WHERE owner = 'o_d18'").fetchone()["c"]
        init_subj = conn.execute("SELECT count(*)::int AS c FROM subjects WHERE owner = 'o_d18'").fetchone()["c"]
        init_alias = conn.execute("SELECT count(*)::int AS c FROM subject_aliases WHERE owner = 'o_d18'").fetchone()["c"]
        assert (init_lt, init_subj, init_alias) == (3, 3, 1)

    store = PostgresGraphStore(pg)
    # 1) "Not true" on the only source fact drops SpinZone to WEIGHT_FLOOR (row kept!)
    resolve_fact(store, "o_d18", "f_spin", SimpleNamespace(action="reject"))
    # 2) Lowering confidence to floor on f_low drops LowClub AND leaves s_inf with no >floor facts
    # 3) Lowering ONLY one of FitZone's two sources keeps FitZone at the higher weight (1.0)
    with pg.transaction() as conn:
        conn.execute("UPDATE facts SET confidence = 0.05 WHERE owner = 'o_d18' AND id IN ('f_low', 'f_fit_a')")
        conn.execute("UPDATE owners SET facts_version = facts_version + 1 WHERE id = 'o_d18'")

    with pg.connection() as conn:
        items = {it["term_folded"]: it for it in list_owner_learned_terms(conn, "o_d18")}
        idx = load_owner_learned_index(conn, "o_d18")
        sal = compute_subject_salience_sql(conn, "o_d18")
        after_lt = conn.execute("SELECT count(*)::int AS c FROM learned_terms WHERE owner = 'o_d18'").fetchone()["c"]
        after_subj = conn.execute("SELECT count(*)::int AS c FROM subjects WHERE owner = 'o_d18'").fetchone()["c"]
        after_alias = conn.execute("SELECT count(*)::int AS c FROM subject_aliases WHERE owner = 'o_d18'").fetchone()["c"]

    # Nothing deleted across learned_terms, subjects, or subject_aliases
    assert (after_lt, after_subj, after_alias) == (init_lt, init_subj, init_alias)
    assert items["spinzone"]["weight"] == pytest.approx(WEIGHT_FLOOR)
    assert items["lowclub"]["weight"] == pytest.approx(WEIGHT_FLOOR)
    assert items["fitzone"]["weight"] == pytest.approx(1.0)
    assert sorted(items["spinzone"]["source_record_ids"]) == ["r_spin"]

    # Expansion puts curated node's own aliases, then high-weight FitZone, and floor-weight terms LAST.
    _, exp = get_vocab().expand_terms(["gym"], learned=idx, max_terms=40)
    assert "fitzone" in exp
    assert "lowclub" in exp and "spinzone" in exp
    assert exp.index("fitness") < exp.index("fitzone") < exp.index("lowclub")
    assert exp.index("fitzone") < exp.index("spinzone")
    assert set(exp[-2:]) == {"lowclub", "spinzone"}

    # §E #18 D18: inferred unconfirmed subject sits at salience floor 0.05; confirmed & user-supplied stay higher.
    assert sal["s_inf"] == pytest.approx(WEIGHT_FLOOR)
    assert sal["s_conf"] > WEIGHT_FLOOR
    assert sal["s_user"] > WEIGHT_FLOOR
