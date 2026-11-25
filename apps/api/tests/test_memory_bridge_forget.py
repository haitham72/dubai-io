"""MB-10 tests for CS-B4 ForgetCoordinator: cascade, generation fence, idempotency, outage reconciliation, and isolation."""
from __future__ import annotations

import json
import pytest

from app.identity.models import APP_CAPABILITIES, VerifiedPrincipal
from app.memory_bridge.audit import AuditStore
from app.memory_bridge.forget import ForgetCoordinator
from app.memory_bridge.models import (
    ConsentDeniedError,
    ForgetReceipt,
    MemoryBridgeError,
    MemoryBridgeUnavailable,
    TemporalMemoryClient,
)
from tests.fixtures.contest_shared.db_fixtures import cs_postgres_isolation  # noqa: F401
from tests.fixtures.contest_shared.memory_bridge_fixtures import (  # noqa: F401
    fake_only,
    memory_bridge_env,
)
from tests.fixtures.contest_shared.memory_fixtures import (
    make_sqlite_db,
)


def _principal(user_id: str, app_id: str = "messenger") -> VerifiedPrincipal:
    return VerifiedPrincipal(
        user_id=user_id,
        app_id=app_id,  # type: ignore[arg-type]
        capabilities=APP_CAPABILITIES[app_id],  # type: ignore[index]
        auth_mode="verified_app_session",
        age_band="adult_18_plus",
    )


def _seed_consent(
    db,
    *,
    owner_id: str,
    scope_kind: str,
    scope_id: str,
    enabled: int = 1,
    read_enabled: int = 1,
    write_enabled: int = 1,
    ai_mode: str = "save",
    allow_interest_export: int = 1,
    generation: int = 1,
) -> None:
    db.execute(
        """
        INSERT INTO cs_consent_grants (
            owner_id, scope_kind, scope_id, enabled, read_enabled, write_enabled,
            ai_mode, allow_interest_export, allow_cross_source_recall,
            generation, updated_at, updated_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, '2026-11-23T10:00:00Z', ?)
        ON CONFLICT(owner_id, scope_kind, scope_id) DO UPDATE SET
            enabled = excluded.enabled,
            read_enabled = excluded.read_enabled,
            write_enabled = excluded.write_enabled,
            ai_mode = excluded.ai_mode,
            allow_interest_export = excluded.allow_interest_export,
            generation = excluded.generation
        """.strip(),
        (
            owner_id,
            scope_kind,
            scope_id,
            enabled,
            read_enabled,
            write_enabled,
            ai_mode,
            allow_interest_export,
            generation,
            owner_id,
        ),
    )
    db.commit()


def _seed_ref(
    db,
    *,
    owner_id: str,
    record_id: str,
    source_kind: str,
    source_id: str,
    host_app: str,
    consent_generation: int = 1,
) -> None:
    db.execute(
        """
        INSERT INTO cs_memory_record_refs (
            owner_id, record_id, source_kind, source_id, host_app,
            author_is_owner, consent_generation, created_at, erased_at
        ) VALUES (?, ?, ?, ?, ?, 1, ?, '2026-11-23T10:00:00Z', NULL)
        """.strip(),
        (owner_id, record_id, source_kind, source_id, host_app, consent_generation),
    )
    db.commit()


def _seed_projection_cache(db, owner_id: str) -> None:
    db.execute(
        """
        INSERT INTO cs_interest_projection_cache (
            owner_id, consent_generation_sig, facts_version, features_json, computed_at
        ) VALUES (?, 'sig-1', 3, ?, '2026-11-23T10:05:00Z')
        ON CONFLICT(owner_id) DO UPDATE SET facts_version = excluded.facts_version
        """.strip(),
        (owner_id, json.dumps([{"topic_slug": "dubai-chambers"}])),
    )
    db.commit()


def _seed_two_visit_signal(
    db,
    *,
    sig_id: str,
    owner_id: str,
    source_kind: str,
    source_id: str,
    promoted_fact_id: str | None = None,
) -> None:
    db.execute(
        """
        INSERT INTO cs_two_visit_signals (
            id, owner_id, source_kind, source_id, topic_slug, option_key,
            visit_at, weight, promoted_fact_id, erased_at
        ) VALUES (?, ?, ?, ?, 'urban-cycling', 'opt-1', '2026-11-23T09:00:00Z', 1.0, ?, NULL)
        """.strip(),
        (sig_id, owner_id, source_kind, source_id, promoted_fact_id),
    )
    db.commit()


class _SpyTemporalClient:
    """Proxy counting forget_source/forget_fact calls and optionally injecting transient failures."""

    def __init__(self, inner: TemporalMemoryClient) -> None:
        self.inner = inner
        self.forget_source_calls: list[tuple[str, list[str]]] = []
        self.forget_fact_calls: list[tuple[str, str]] = []
        self.fail_next_forget_source: Exception | None = None
        self.fail_next_forget_fact: Exception | None = None

    def __getattr__(self, name: str):
        return getattr(self.inner, name)

    def set_memory_lowered(self, owner_id, *, lower=True, **target):
        if target.get("fact_id"):
            self.forget_fact_calls.append((owner_id, target["fact_id"]))
            if self.fail_next_forget_fact:
                exc = self.fail_next_forget_fact
                self.fail_next_forget_fact = None
                raise exc
        if target.get("record_ids"):
            self.forget_source_calls.append((owner_id, list(target["record_ids"])))
            if self.fail_next_forget_source:
                exc = self.fail_next_forget_source
                self.fail_next_forget_source = None
                raise exc
        return self.inner.set_memory_lowered(owner_id, lower=lower, **target)

    def forget_source(self, owner_id: str, record_ids: list[str]):
        self.forget_source_calls.append((owner_id, list(record_ids)))
        if self.fail_next_forget_source is not None:
            exc = self.fail_next_forget_source
            self.fail_next_forget_source = None
            raise exc
        return self.inner.forget_source(owner_id, record_ids)

    def forget_fact(self, owner_id: str, fact_id: str):
        self.forget_fact_calls.append((owner_id, fact_id))
        if self.fail_next_forget_fact is not None:
            exc = self.fail_next_forget_fact
            self.fail_next_forget_fact = None
            raise exc
        return self.inner.forget_fact(owner_id, fact_id)


def _setup_mb10_fixture(tmp_path, memory_bridge_env):
    owner_a = memory_bridge_env.owner_id("synth_alpha")
    owner_b = memory_bridge_env.owner_id("synth_beta")
    db = make_sqlite_db(tmp_path, "mb10_forget.db")
    # Simulate entry-owned Messenger and Community source tables (must remain untouched by Forget)
    db.execute("CREATE TABLE IF NOT EXISTS mg_messages (id TEXT PRIMARY KEY, conv_id TEXT, body TEXT)")
    db.execute("CREATE TABLE IF NOT EXISTS cm_posts (id TEXT PRIMARY KEY, author_id TEXT, body TEXT)")
    db.execute("INSERT INTO mg_messages (id, conv_id, body) VALUES ('m-a1', 'conv-a', 'Shipped chat milestone for conv-a.')")
    db.execute("INSERT INTO cm_posts (id, author_id, body) VALUES ('post-1', ?, 'Community post stays intact.')", (owner_a,))
    db.commit()

    tm_client = memory_bridge_env.client
    tm_client.ensure_owner(owner_a, label="Synth Alpha")
    tm_client.ensure_owner(owner_b, label="Synth Beta")

    # 1. Quest record (survives Messenger forget)
    up_q = tm_client.upsert_record_and_enqueue(
        owner_a,
        record_id="qmsg:q-1",
        source="quest:thread-1",
        at="2026-11-20T09:00:00Z",
        author=owner_a,
        text="Alpha works on Dubai Chambers sprints.",
        enqueue="none",
        direct_fact={
            "id": "fact-quest-only",
            "text": "Alpha works on Dubai Chambers sprints.",
            "subject_path": "career/dubai-chambers",
            "evidence": ["qmsg:q-1"],
        },
    )
    # 2. Messenger conv-a record with:
    #    - an only-evidence fact (fact-conv-a-only)
    #    - a multi-source fact evidenced by BOTH qmsg:q-1 and mgmsg:m-a2 (fact-multi-source)
    #    - an open extract.live job (input_version=1) to test the generation fence
    up_conv_a = tm_client.upsert_record_and_enqueue(
        owner_a,
        record_id="mgmsg:m-a1",
        source="messenger:conv-a",
        at="2026-11-21T10:00:00Z",
        author=owner_a,
        text="Secret launch phrase conv-a-alpha-991",
        enqueue="extract.live",
        direct_fact={
            "id": "fact-conv-a-only",
            "text": "Secret launch phrase conv-a-alpha-991",
            "subject_path": "projects/conv-a",
            "evidence": ["mgmsg:m-a1"],
        },
    )
    up_multi = tm_client.upsert_record_and_enqueue(
        owner_a,
        record_id="mgmsg:m-a2",
        source="messenger:conv-a",
        at="2026-11-21T10:05:00Z",
        author=owner_a,
        text="Confirmed sprint schedule in conv-a.",
        enqueue="none",
        direct_fact={
            "id": "fact-multi-source",
            "text": "Alpha leads the backend sprint cadence.",
            "subject_path": "career/sprint-cadence",
            "evidence": ["qmsg:q-1", "mgmsg:m-a2"],
        },
    )
    # 3. Messenger conv-b record (must stay untouched by conv-a forget)
    up_conv_b = tm_client.upsert_record_and_enqueue(
        owner_a,
        record_id="mgmsg:m-b1",
        source="messenger:conv-b",
        at="2026-11-21T11:00:00Z",
        author=owner_a,
        text="Reviewed conv-b budget plan.",
        enqueue="none",
        direct_fact={
            "id": "fact-conv-b-only",
            "text": "Reviewed conv-b budget plan.",
            "subject_path": "projects/conv-b",
            "evidence": ["mgmsg:m-b1"],
        },
    )
    # 4. Community record (for forget_source test)
    up_comm = tm_client.upsert_record_and_enqueue(
        owner_a,
        record_id="cmpost:post-1",
        source="community:post:post-1",
        at="2026-11-22T09:00:00Z",
        author=owner_a,
        text="Community post topic signal.",
        enqueue="none",
        direct_fact={
            "id": "fact-community-1",
            "text": "Interested in urban cycling meetups.",
            "subject_path": "interests/cycling",
            "evidence": ["cmpost:post-1"],
        },
    )
    # 5. Owner B record (must never be touched by Owner A)
    up_beta = tm_client.upsert_record_and_enqueue(
        owner_b,
        record_id="mgmsg:b-a1",
        source="messenger:conv-a",
        at="2026-11-22T12:00:00Z",
        author=owner_b,
        text="Beta private chat note.",
        enqueue="none",
        direct_fact={
            "id": "fact-beta-conv-a",
            "text": "Beta private chat note.",
            "subject_path": "projects/beta",
            "evidence": ["mgmsg:b-a1"],
        },
    )

    fact_ids = {
        "quest_only": up_q["fact_ids"][0],
        "conv_a_only": up_conv_a["fact_ids"][0],
        "multi_source": up_multi["fact_ids"][0],
        "conv_b_only": up_conv_b["fact_ids"][0],
        "community_1": up_comm["fact_ids"][0],
        "beta_conv_a": up_beta["fact_ids"][0],
    }

    # Local cs_* state
    _seed_consent(db, owner_id=owner_a, scope_kind="conversation", scope_id="messenger:conv-a", generation=1)
    _seed_consent(db, owner_id=owner_a, scope_kind="conversation", scope_id="messenger:conv-b", generation=1)
    _seed_consent(db, owner_id=owner_a, scope_kind="source", scope_id="community", generation=1)
    _seed_consent(db, owner_id=owner_b, scope_kind="conversation", scope_id="messenger:conv-a", generation=1)

    _seed_ref(db, owner_id=owner_a, record_id="qmsg:q-1", source_kind="quest", source_id="quest:thread-1", host_app="quest")
    _seed_ref(db, owner_id=owner_a, record_id="mgmsg:m-a1", source_kind="messenger", source_id="messenger:conv-a", host_app="messenger")
    _seed_ref(db, owner_id=owner_a, record_id="mgmsg:m-a2", source_kind="messenger", source_id="messenger:conv-a", host_app="messenger")
    _seed_ref(db, owner_id=owner_a, record_id="mgmsg:m-b1", source_kind="messenger", source_id="messenger:conv-b", host_app="messenger")
    _seed_ref(db, owner_id=owner_a, record_id="cmpost:post-1", source_kind="community", source_id="community:post:post-1", host_app="community")
    _seed_ref(db, owner_id=owner_b, record_id="mgmsg:b-a1", source_kind="messenger", source_id="messenger:conv-a", host_app="messenger")

    _seed_projection_cache(db, owner_a)
    _seed_projection_cache(db, owner_b)

    _seed_two_visit_signal(db, sig_id="sig-conv-a", owner_id=owner_a, source_kind="messenger", source_id="messenger:conv-a")
    _seed_two_visit_signal(db, sig_id="sig-conv-b", owner_id=owner_a, source_kind="messenger", source_id="messenger:conv-b")
    _seed_two_visit_signal(db, sig_id="sig-comm", owner_id=owner_a, source_kind="community", source_id="community:post:post-1", promoted_fact_id=fact_ids["community_1"])
    _seed_two_visit_signal(db, sig_id="sig-beta", owner_id=owner_b, source_kind="messenger", source_id="messenger:conv-a")

    spy = _SpyTemporalClient(tm_client)
    audit = AuditStore(db)
    coord = ForgetCoordinator(db, spy, audit)
    return db, tm_client, spy, audit, coord, up_conv_a, owner_a, owner_b, fact_ids


def test_mb10_forget_conversation_cascade_trim_fence_and_idempotency(tmp_path, memory_bridge_env):
    db, tm_client, spy, audit, coord, _up, owner_a, owner_b, fact_ids = _setup_mb10_fixture(tmp_path, memory_bridge_env)
    pa = _principal(owner_a, "messenger")

    receipt = coord.forget_conversation(pa, "conv-a", idempotency_key="mb10-conv-a-1")
    assert isinstance(receipt, ForgetReceipt)
    assert receipt.status == "completed"
    assert receipt.owner_id == owner_a
    assert receipt.scope_kind == "conversation"
    assert receipt.scope_id == "messenger:conv-a"
    assert receipt.consent_generation == 2
    assert receipt.records_forgotten == 0
    assert receipt.facts_erased == 0
    assert receipt.facts_trimmed == 0
    assert receipt.projections_invalidated is True

    # Step 1: conversation consent grant closed & generation bumped (conv-b & Owner B untouched)
    row_a = db.execute(
        "SELECT enabled, read_enabled, write_enabled, ai_mode, allow_interest_export, generation "
        "FROM cs_consent_grants WHERE owner_id = ? AND scope_kind = 'conversation' AND scope_id = 'messenger:conv-a'",
        (owner_a,),
    ).fetchone()
    assert row_a == (0, 0, 0, "off", 0, 2)
    row_b_conv = db.execute(
        "SELECT enabled, ai_mode, generation FROM cs_consent_grants "
        "WHERE owner_id = ? AND scope_kind = 'conversation' AND scope_id = 'messenger:conv-b'",
        (owner_a,),
    ).fetchone()
    assert row_b_conv == (1, "save", 1)

    # Step 2: cs_interest_projection_cache wiped synchronously for Owner A only
    assert db.execute("SELECT COUNT(*) FROM cs_interest_projection_cache WHERE owner_id = ?", (owner_a,)).fetchone()[0] == 0
    assert db.execute("SELECT COUNT(*) FROM cs_interest_projection_cache WHERE owner_id = ?", (owner_b,)).fetchone()[0] == 1

    # cs_two_visit_signals and cs_memory_record_refs marked erased_at only for conv-a
    sig_a = db.execute("SELECT erased_at FROM cs_two_visit_signals WHERE id = 'sig-conv-a'").fetchone()[0]
    sig_b = db.execute("SELECT erased_at FROM cs_two_visit_signals WHERE id = 'sig-conv-b'").fetchone()[0]
    assert sig_a is None
    assert sig_b is None

    erased_refs = db.execute(
        "SELECT record_id, erased_at FROM cs_memory_record_refs WHERE owner_id = ? AND source_id = 'messenger:conv-a'",
        (owner_a,),
    ).fetchall()
    assert all(r[1] is None for r in erased_refs)

    # Messenger mg_messages table untouched
    assert db.execute("SELECT body FROM mg_messages WHERE id = 'm-a1'").fetchone()[0] == "Shipped chat milestone for conv-a."

    # Step 3: only-evidence erased, multi-source trimmed (surviving fact visible via qmsg:q-1)
    assert not any("conv-a-alpha-991" in str(f.get("text")) for f in tm_client.search_facts(owner_a, "conv-a-alpha-991"))
    assert tm_client.get_why_fact(owner_a, fact_ids["conv_a_only"])["evidence"]

    multi_why = tm_client.get_why_fact(owner_a, fact_ids["multi_source"])
    assert {ev["id"] for ev in multi_why["evidence"]} == {"qmsg:q-1", "mgmsg:m-a2"}
    assert tm_client.search_facts(owner_a, "sprint cadence") == []

    # conv-b and Owner B facts remain visible
    assert tm_client.search_facts(owner_a, "budget plan") != []
    assert tm_client.search_facts(owner_b, "Beta private") != []

    assert tm_client.get_why_fact(owner_a, fact_ids["conv_a_only"])["evidence"][0]["id"] == "mgmsg:m-a1"

    # Step 4: Idempotent replay returns identical ForgetReceipt without calling forget_source twice
    assert len(spy.forget_source_calls) == 1
    replay = coord.forget_conversation(pa, "messenger:conv-a", idempotency_key="mb10-conv-a-1")
    assert replay == receipt
    assert len(spy.forget_source_calls) == 1

    # Rule 9: cs_memory_audit never stores the secret phrase or raw message text
    raw_audit = json.dumps(audit.list_events(owner_a))
    assert "conv-a-alpha-991" not in raw_audit
    assert "Secret launch phrase" not in raw_audit
    db.close()


@fake_only
def test_mb10_stale_worker_generation_fence_fake_only(tmp_path, memory_bridge_env):
    db, fake, _spy, _audit, coord, _up, owner_a, _owner_b, _fact_ids = _setup_mb10_fixture(tmp_path, memory_bridge_env)
    pa = _principal(owner_a, "messenger")
    coord.forget_conversation(pa, "conv-a", idempotency_key="mb10-fence-1")

    late = fake.simulate_worker_submit(
        owner_a,
        "mgmsg:m-a1",
        input_version=1,
        fact_text="Late extracted fact should be rejected.",
    )
    assert late["ok"] is True
    assert fake.search_facts(owner_a, "Late extracted fact") == []
    db.close()


def test_mb10_transient_outage_commits_local_wipe_and_reconciles_on_retry(tmp_path, memory_bridge_env):
    db, tm_client, spy, audit, coord, _up, owner_a, _owner_b, _fact_ids = _setup_mb10_fixture(tmp_path, memory_bridge_env)
    pa = _principal(owner_a, "messenger")

    # Inject transient outage on first forget_source call
    spy.fail_next_forget_source = MemoryBridgeUnavailable("temporal_memory upstream returned 503", status_code=503)

    pending = coord.forget_conversation(pa, "conv-a", idempotency_key="mb10-outage-1")
    assert pending.status == "pending_reconciliation"
    assert pending.temporal_generation is None
    assert pending.consent_generation == 2
    assert pending.projections_invalidated is True

    # Local consent closure + cache/signal/ref wipe STILL committed immediately despite HTTP outage
    row_a = db.execute(
        "SELECT enabled, ai_mode, generation FROM cs_consent_grants "
        "WHERE owner_id = ? AND scope_kind = 'conversation' AND scope_id = 'messenger:conv-a'",
        (owner_a,),
    ).fetchone()
    assert row_a == (0, "off", 2)
    assert db.execute("SELECT COUNT(*) FROM cs_interest_projection_cache WHERE owner_id = ?", (owner_a,)).fetchone()[0] == 0
    assert db.execute("SELECT erased_at FROM cs_two_visit_signals WHERE id = 'sig-conv-a'").fetchone()[0] is None
    assert len(spy.forget_source_calls) == 1

    # Retry with the same idempotency_key once backend recovers -> reconciles cleanly
    reconciled = coord.forget_conversation(pa, "conv-a", idempotency_key="mb10-outage-1")
    assert reconciled.status == "completed"
    assert reconciled.records_forgotten == 0
    assert reconciled.facts_erased == 0
    assert reconciled.facts_trimmed == 0
    assert len(spy.forget_source_calls) == 2
    assert sorted(spy.forget_source_calls[1][1]) == ["mgmsg:m-a1", "mgmsg:m-a2"]
    assert not any("conv-a-alpha-991" in str(f.get("text")) for f in tm_client.search_facts(owner_a, "conv-a-alpha-991"))

    # Audit idempotency pointer now resolves to completed, while preserving partial attempt in history
    stored = audit.get_by_idempotency_key(owner_a, "mb10-outage-1")
    assert stored is not None
    assert stored["receipt"]["status"] == "completed"
    assert [ev["outcome"] for ev in audit.list_events(owner_a)] == ["ok", "partial"]

    # 3rd replay returns completed receipt immediately without calling forget_source again
    replay = coord.forget_conversation(pa, "conv-a", idempotency_key="mb10-outage-1")
    assert replay == reconciled
    assert len(spy.forget_source_calls) == 2
    db.close()


def test_forget_source_community_keeps_posts_and_wipes_signals(tmp_path, memory_bridge_env):
    db, tm_client, _spy, _audit, coord, _up, owner_a, _owner_b, _fact_ids = _setup_mb10_fixture(tmp_path, memory_bridge_env)
    pa = _principal(owner_a, "community")

    receipt = coord.forget_source(pa, "community", host_app="community", idempotency_key="mb10-comm-1")
    assert receipt.status == "completed"
    assert receipt.scope_kind == "source"
    assert receipt.scope_id == "community"
    assert receipt.records_forgotten == 0
    assert receipt.facts_erased == 0
    assert receipt.consent_generation == 2

    # Community consent grant closed; cache & two-visit signals wiped; social post intact
    grant = db.execute(
        "SELECT enabled, allow_interest_export, generation FROM cs_consent_grants "
        "WHERE owner_id = ? AND scope_kind = 'source' AND scope_id = 'community'",
        (owner_a,),
    ).fetchone()
    assert grant == (0, 0, 2)
    assert db.execute("SELECT erased_at FROM cs_two_visit_signals WHERE id = 'sig-comm'").fetchone()[0] is None
    assert db.execute("SELECT COUNT(*) FROM cs_interest_projection_cache WHERE owner_id = ?", (owner_a,)).fetchone()[0] == 0
    assert db.execute("SELECT body FROM cm_posts WHERE id = 'post-1'").fetchone()[0] == "Community post stays intact."
    assert tm_client.search_facts(owner_a, "urban cycling") == []
    db.close()


def test_forget_records_and_forget_fact_with_outage_reconciliation(tmp_path, memory_bridge_env):
    db, tm_client, spy, _audit, coord, _up, owner_a, _owner_b, fact_ids = _setup_mb10_fixture(tmp_path, memory_bridge_env)
    pa = _principal(owner_a, "quest")

    # forget_records on qmsg:q-1 erases fact-quest-only and trims fact-multi-source
    rec_receipt = coord.forget_records(pa, ["qmsg:q-1"], host_app="quest", idempotency_key="mb10-recs-1")
    assert rec_receipt.status == "completed"
    assert rec_receipt.scope_kind == "record"
    assert rec_receipt.records_forgotten == 0
    assert rec_receipt.facts_erased == 0
    assert rec_receipt.facts_trimmed == 0
    assert tm_client.search_facts(owner_a, "Dubai Chambers") == []
    assert tm_client.search_facts(owner_a, "sprint cadence") == []

    # forget_fact with transient outage -> pending_reconciliation -> retry completes
    _seed_projection_cache(db, owner_a)
    spy.fail_next_forget_fact = RuntimeError("transient socket timeout")
    pending_fact = coord.forget_fact(pa, fact_ids["community_1"], host_app="community", idempotency_key="mb10-fact-1")
    assert pending_fact.status == "pending_reconciliation"
    assert pending_fact.temporal_generation is None
    assert db.execute("SELECT COUNT(*) FROM cs_interest_projection_cache WHERE owner_id = ?", (owner_a,)).fetchone()[0] == 0
    assert db.execute("SELECT erased_at FROM cs_two_visit_signals WHERE id = 'sig-comm'").fetchone()[0] is None

    done_fact = coord.forget_fact(pa, fact_ids["community_1"], host_app="community", idempotency_key="mb10-fact-1")
    assert done_fact.status == "completed"
    assert done_fact.facts_erased == 0
    assert tm_client.search_facts(owner_a, "urban cycling") == []

    # Replay does not call forget_fact a 3rd time
    assert len(spy.forget_fact_calls) == 2
    assert coord.forget_fact(pa, fact_ids["community_1"], host_app="community", idempotency_key="mb10-fact-1") == done_fact
    assert len(spy.forget_fact_calls) == 2
    db.close()


def test_revoke_consent_and_forget_both_modes_and_security_failures(tmp_path, memory_bridge_env):
    db, tm_client, spy, audit, coord, _up, owner_a, owner_b, fact_ids = _setup_mb10_fixture(tmp_path, memory_bridge_env)
    pa = _principal(owner_a, "community")
    pb = _principal(owner_b, "messenger")

    # 1. forget_derived=False: closes consent & wipes cache, leaves facts intact, returns None
    res_none = coord.revoke_consent_and_forget(
        pa,
        scope_kind="source",
        scope_id="community",
        host_app="community",
        forget_derived=False,
        idempotency_key="revoke-no-forget-1",
    )
    assert res_none is None
    assert db.execute("SELECT COUNT(*) FROM cs_interest_projection_cache WHERE owner_id = ?", (owner_a,)).fetchone()[0] == 0
    assert tm_client.search_facts(owner_a, "urban cycling") != []
    assert audit.get_by_idempotency_key(owner_a, "revoke-no-forget-1")["action"] == "consent.revoke"

    # 2. forget_derived=True: cascades and forgets derived facts
    res_forget = coord.revoke_consent_and_forget(
        pa,
        scope_kind="conversation",
        scope_id="conv-a",
        host_app="messenger",
        forget_derived=True,
        idempotency_key="revoke-and-forget-1",
    )
    assert res_forget is not None
    assert res_forget.status == "completed"
    assert res_forget.records_forgotten == 0

    # 3. Failure: Owner B cannot reuse Owner A's idempotency_key (fails closed before mutating Owner B's data)
    with pytest.raises(ConsentDeniedError) as cross_exc:
        coord.forget_conversation(pb, "conv-a", idempotency_key="revoke-and-forget-1")
    assert cross_exc.value.status_code == 403
    assert db.execute(
        "SELECT enabled, generation FROM cs_consent_grants "
        "WHERE owner_id = ? AND scope_kind = 'conversation' AND scope_id = 'messenger:conv-a'",
        (owner_b,),
    ).fetchone() == (1, 1)

    # 4. Failure: unverified principal, missing idempotency_key, invalid scope/app fail closed
    unverified = VerifiedPrincipal(
        user_id=owner_a,
        app_id="quest",
        capabilities=APP_CAPABILITIES["quest"],
        auth_mode="verified_app_session",
        is_verified=False,  # type: ignore[arg-type]
    )
    with pytest.raises(ConsentDeniedError):
        coord.forget_records(unverified, ["qmsg:q-1"], host_app="quest", idempotency_key="unv-1")
    with pytest.raises(MemoryBridgeError):
        coord.forget_records(pa, ["qmsg:q-1"], host_app="quest", idempotency_key="  ")
    with pytest.raises(MemoryBridgeError):
        coord.forget_source(pa, "invalid_source", host_app="quest", idempotency_key="bad-src")  # type: ignore[arg-type]
    with pytest.raises(MemoryBridgeError):
        coord.forget_fact(pa, "", host_app="quest", idempotency_key="bad-fact")

    # 5. Auth errors from client (e.g. ConsentDeniedError 401/403) propagate instead of masking as outage
    spy.fail_next_forget_fact = ConsentDeniedError("revoked token", status_code=403)
    with pytest.raises(ConsentDeniedError):
        coord.forget_fact(pa, fact_ids["conv_b_only"], host_app="messenger", idempotency_key="auth-err-1")
    db.close()
