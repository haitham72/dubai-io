"""Tests for export_cli and Contract v1.2 model_observed end-to-end."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from typing import Any, Iterator

from fastapi.testclient import TestClient
import pytest

from temporal_memory.api.app import create_app
from temporal_memory.core import extract
from temporal_memory.core.graph_store import PostgresGraphStore
from temporal_memory.core.validator import validate
from temporal_memory.db.db import Database, create_test_schema, drop_test_schema, migrate
from temporal_memory.ingest.export_cli import export_owner_tree, find_repo_root
from temporal_memory.mcp.server import create_mcp_app
from temporal_memory.mcp.tokens import create_token
from temporal_memory.models import (
    Attempt,
    ExtractionOutput,
    FactEntity,
    Job,
    JobBundle,
    OutEntity,
    OutFact,
    Owner,
    Record,
    Worker,
)
from temporal_memory.queue.jobs import PostgresJobs

HOOKS_DIR = Path(__file__).resolve().parent.parent / "hooks"
if str(HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(HOOKS_DIR))

import agent_worker  # noqa: E402


@pytest.fixture()
def isolated_db() -> Iterator[Database]:
    db, schema = create_test_schema()
    try:
        yield db
    finally:
        drop_test_schema(db, schema)


def _sample_bundle(*, worker_id: str = "w-test") -> JobBundle:
    now = datetime(2026, 10, 5, 12, 0, 0, tzinfo=timezone.utc)
    records = [
        Record(
            id="wa-101",
            owner="karim",
            source="whatsapp:work",
            at="2026-10-05T09:00:00Z",
            author="Karim",
            text="Nadia Mansour joined Falcon Tech in DIFC.",
            generation=0,
        )
    ]
    job = Job(
        id="job-obs-1",
        owner="karim",
        kind="extract.day",
        priority=1,
        pool="internal",
        input_ref=["wa-101"],
        input_version=0,
        context_hash="ctx1",
        prompt_version="extract@3",
        day="2026-10-05",
        state="leased",
        attempt_no=1,
        fence_token="fence-obs-1",
        worker_id=worker_id,
        lease_expires_at=(now + timedelta(minutes=5)).isoformat(),
    )
    return JobBundle(
        job=job,
        records=records,
        context={"entities": [], "facts": [], "subjects": []},
        system_prompt="Extract facts.",
        output_schema=extract.OUTPUT_SCHEMA,
    )


def _valid_output() -> ExtractionOutput:
    return ExtractionOutput(
        entities=[
            OutEntity(ref="new:Nadia Mansour", kind="person", aliases=["Nadia"], relation_to_user="colleague"),
            OutEntity(ref="new:Falcon Tech", kind="org", aliases=[], relation_to_user=None),
        ],
        facts=[
            OutFact(
                text="Nadia Mansour joined Falcon Tech in DIFC",
                text_orig=None,
                subject_path="work/network",
                entities=[
                    FactEntity(entity_id="new:Nadia Mansour", role="colleague"),
                    FactEntity(entity_id="new:Falcon Tech", role="employer"),
                ],
                op="new",
                target=None,
                valid_from="2026-10-05",
                evidence=["wa-101"],
                sensitive=None,
            )
        ],
        links=[],
    )


def _valid_output_dict() -> dict[str, Any]:
    return {
        "entities": [
            {"ref": "new:Nadia Mansour", "kind": "person", "aliases": ["Nadia"], "relation_to_user": "colleague"},
            {"ref": "new:Falcon Tech", "kind": "org", "aliases": [], "relation_to_user": None},
        ],
        "facts": [
            {
                "text": "Nadia Mansour joined Falcon Tech in DIFC",
                "text_orig": None,
                "subject_path": "work/network",
                "entities": [
                    {"entity_id": "new:Nadia Mansour", "role": "colleague"},
                    {"entity_id": "new:Falcon Tech", "role": "employer"},
                ],
                "op": "new",
                "target": None,
                "valid_from": "2026-10-05",
                "evidence": ["wa-101"],
                "sensitive": None,
            }
        ],
        "links": [],
    }


# ---------------------------------------------------------------- 1. export_cli
def test_find_repo_root_and_export_owner_tree(isolated_db: Database, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = PostgresGraphStore(isolated_db)
    jobs = PostgresJobs(isolated_db, store)
    store.create_owner(
        Owner(id="karim", label="Karim Haddad", kind="demo", display_name="Karim Haddad", self_aliases=["Karim"])
    )
    store.upsert_records(
        "karim",
        [
            Record(
                id="wa-101",
                owner="karim",
                source="whatsapp:work",
                at="2026-10-05T09:00:00Z",
                author="Karim",
                text="Nadia Mansour joined Falcon Tech in DIFC.",
                generation=0,
            )
        ],
    )
    job = jobs.enqueue("karim", "extract.day", ["wa-101"], priority=1, day="2026-10-05")
    bundles = jobs.claim(Worker(id="w-1", kind="internal-cloud", model="claude-haiku-5-5", runner="anthropic"), ["internal"])
    assert len(bundles) == 1
    att = Attempt(
        job_id=job.id,
        attempt_no=bundles[0].job.attempt_no,
        fence_token=bundles[0].job.fence_token or "",
        worker_id="w-1",
        worker_kind="internal-cloud",
        model="claude-haiku-5-5",
        prompt_version=job.prompt_version,
        output=_valid_output(),
    )
    assert jobs.submit(att).ok is True

    # find_repo_root finds .git above apps/memory
    detected_root = find_repo_root()
    assert (detected_root / ".git").exists()
    # Fallback when starting outside any git repo
    outside_dir = tmp_path / "no_git_here"
    outside_dir.mkdir()
    assert find_repo_root(outside_dir) == Path(__file__).resolve().parents[1]

    # Refuses writing inside repo root or equal to repo root
    fake_repo = tmp_path / "repo"
    (fake_repo / "nested").mkdir(parents=True)
    with pytest.raises(ValueError, match="Refusing to write export inside repository"):
        export_owner_tree(isolated_db, "karim", fake_repo, repo_root=fake_repo)
    with pytest.raises(ValueError, match="Refusing to write export inside repository"):
        export_owner_tree(isolated_db, "karim", fake_repo / "nested" / "vault", repo_root=fake_repo)

    # Writes Quest tree outside repo root
    out_dir = tmp_path / "exported_vault"
    summary = export_owner_tree(isolated_db, "karim", out_dir, repo_root=fake_repo)
    assert summary["owner"] == "karim"
    assert summary["out_dir"] == str(out_dir.resolve())
    assert summary["files_written"] == len(summary["files"])
    assert "MEMORIES.md" in summary["files"]
    assert "USER.md" in summary["files"]
    assert "02-career-and-craft/network.md" in summary["files"]
    assert "orgs/falcon-tech.md" not in summary["files"]
    assert "people/nadia-mansour.md" not in summary["files"]
    leaf = (out_dir / "02-career-and-craft" / "network.md").read_text(encoding="utf-8")
    assert leaf.startswith("---\n")
    assert "Nadia Mansour joined Falcon Tech" in leaf

    # Refuses path traversal in rendered paths
    monkeypatch.setattr(
        "temporal_memory.ingest.export_cli.render",
        lambda _owner, *, store: {"../escape.md": "bad"},
    )
    with pytest.raises(ValueError, match="Refusing path traversal"):
        export_owner_tree(isolated_db, "karim", out_dir, repo_root=fake_repo)


# ---------------------------------------------------------------- 2. model_observed extraction
@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        (
            {
                "modelUsage": {
                    "claude-haiku-4-5-20251001": {"inputTokens": 40, "outputTokens": 10},
                    "claude-sonnet-4-5-20250929": {"inputTokens": 400, "outputTokens": 120},
                }
            },
            "claude-sonnet-4-5-20250929",
        ),
        (
            {"modelUsage": {"claude-opus-4-1": {}, "claude-haiku-4-5": {}}},
            "claude-opus-4-1",
        ),
        (
            {
                "stats": {
                    "models": {
                        "gemini-2.5-flash": {"tokens": {"prompt": 100, "candidates": 20, "total": 120}},
                        "gemini-2.5-pro": {"tokens": {"prompt": 300, "candidates": 90, "total": 390}},
                    }
                }
            },
            "gemini-2.5-pro",
        ),
        (
            {"stats": {"models": {"gemini-2.5-flash": {"api": {"totalRequests": 1}}}}},
            "gemini-2.5-flash",
        ),
        ({"model": "gpt-5-codex"}, "gpt-5-codex"),
        ({"model_id": "qwen3-coder-plus"}, "qwen3-coder-plus"),
        ({"modelVersion": "gemini-2.5-flash-001"}, "gemini-2.5-flash-001"),
        ({"entities": [], "facts": [], "links": []}, None),
    ],
)
def test_extract_observed_model_rules(payload: dict[str, Any], expected: str | None) -> None:
    assert extract.extract_observed_model(payload) == expected
    assert agent_worker.extract_observed_model(payload) == expected


def test_extract_run_captures_model_observed_for_all_runners(monkeypatch: pytest.MonkeyPatch) -> None:
    bundle = _sample_bundle()
    raw_out = _valid_output_dict()

    # 1) Anthropic mocked
    class FakeMessages:
        def create(self, **_: Any) -> Any:
            return SimpleNamespace(
                model="claude-sonnet-4-5-20250929",
                content=[SimpleNamespace(type="text", text=json.dumps(raw_out))],
                usage=SimpleNamespace(input_tokens=500, output_tokens=100),
            )

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-dummy")
    monkeypatch.setattr(extract, "anthropic", SimpleNamespace(Anthropic=lambda api_key: SimpleNamespace(messages=FakeMessages())))
    att_anth = extract.run(bundle, "anthropic", "claude-haiku-5-5")
    assert att_anth.model == "claude-haiku-5-5"
    assert att_anth.model_observed == "claude-sonnet-4-5-20250929"

    # 2) LM Studio mocked
    monkeypatch.setattr(
        extract.httpx,
        "post",
        lambda *a, **kw: SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {
                "model": "qwen/qwen3-30b-a3b",
                "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(raw_out)}}],
                "usage": {"prompt_tokens": 120, "completion_tokens": 40},
            },
        ),
    )
    att_lms = extract.run(bundle, "lmstudio", "qwen/qwen3-4b-2507")
    assert att_lms.model == "qwen/qwen3-4b-2507"
    assert att_lms.model_observed == "qwen/qwen3-30b-a3b"

    # 3) CLI mocked: claude -p, gemini, codex, unknown
    cli_outputs = [
        json.dumps(
            {
                "result": json.dumps(raw_out),
                "usage": {"input_tokens": 100, "output_tokens": 50},
                "total_cost_usd": 0.002,
                "modelUsage": {"claude-sonnet-4-5-20250929": {"inputTokens": 100, "outputTokens": 50}},
            }
        ),
        json.dumps(
            {
                **raw_out,
                "stats": {"models": {"gemini-2.5-pro": {"tokens": {"total": 250}}}},
            }
        ),
        json.dumps({**raw_out, "model": "gpt-5-codex"}),
        json.dumps(raw_out),
    ]
    expected_obs = ["claude-sonnet-4-5-20250929", "gemini-2.5-pro", "gpt-5-codex", None]
    for stdout_str, exp in zip(cli_outputs, expected_obs, strict=True):
        monkeypatch.setattr(
            extract.subprocess,
            "run",
            lambda *a, _out=stdout_str, **kw: SimpleNamespace(returncode=0, stdout=_out, stderr=""),
        )
        att_cli = extract.run(bundle, "agent-cli", "declared-model")
        assert att_cli.model == "declared-model"
        assert att_cli.model_observed == exp


def test_agent_worker_model_observed_end_to_end(monkeypatch: pytest.MonkeyPatch) -> None:
    raw_out = _valid_output_dict()
    bundle_dict = {
        "job": {"id": "j-1", "fence_token": "f-1", "attempt_no": 1},
        "records": [{"id": "wa-101", "at": "2026-10-05T09:00:00Z", "source": "whatsapp", "author": "Karim", "text": "Hi"}],
        "context": {"entities": [], "facts": [], "subjects": []},
        "system_prompt": "Extract.",
    }

    # default_invoke_cli across claude -p, gemini, codex, unknown
    samples = [
        json.dumps({"result": json.dumps(raw_out), "usage": {"input_tokens": 10, "output_tokens": 5}, "modelUsage": {"claude-sonnet-4-5": {"inputTokens": 10}}}),
        json.dumps({**raw_out, "stats": {"models": {"gemini-2.5-flash": {"tokens": {"total": 99}}}}}),
        json.dumps({**raw_out, "model": "gpt-5-codex"}),
        json.dumps(raw_out),
    ]
    for stdout_str, exp in zip(samples, ["claude-sonnet-4-5", "gemini-2.5-flash", "gpt-5-codex", None], strict=True):
        monkeypatch.setattr(
            agent_worker.subprocess,
            "run",
            lambda *a, _out=stdout_str, **kw: SimpleNamespace(returncode=0, stdout=_out, stderr=""),
        )
        res = agent_worker.default_invoke_cli(bundle_dict, "declared", "echo --model {model}")
        assert res.model_observed == exp

    # _normalize_cli_result preserves model_observed from dict
    norm = agent_worker._normalize_cli_result({"output": raw_out, "tokens_in": 5, "model_observed": "  claude-sonnet-4-5  "})
    assert norm.model_observed == "claude-sonnet-4-5"

    # run_worker sends model_observed only when non-None
    submitted: list[dict[str, Any]] = []

    class FakeMCPClient:
        def __init__(self, **_kw: Any) -> None:
            pass

        def __enter__(self) -> FakeMCPClient:
            return self

        def __exit__(self, *_: Any) -> None:
            return None

        def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
            if name == "memory_claim_job":
                return {"jobs": [bundle_dict], "count": 1}
            if name == "memory_submit_result":
                submitted.append(dict(arguments or {}))
                return {"ok": True}
            return {}

    monkeypatch.setattr(agent_worker, "MCPHttpClient", FakeMCPClient)
    agent_worker.run_worker(
        url="http://localhost:8000/mcp",
        token="tok",
        model="claude-haiku-5-5",
        once=True,
        invoke_cli_fn=lambda _b, _m, _c: agent_worker.CliInvocationResult(
            output=raw_out, tokens_in=10, tokens_out=5, model_observed="claude-sonnet-4-5"
        ),
    )
    agent_worker.run_worker(
        url="http://localhost:8000/mcp",
        token="tok",
        model="claude-haiku-5-5",
        once=True,
        invoke_cli_fn=lambda _b, _m, _c: agent_worker.CliInvocationResult(
            output=raw_out, tokens_in=10, tokens_out=5, model_observed=None
        ),
    )
    assert submitted[0]["model_observed"] == "claude-sonnet-4-5"
    assert "model_observed" not in submitted[1]


# ---------------------------------------------------------------- 3. validator, jobs, graph_store, api, mcp, ops
def test_validator_model_mismatch_is_non_blocking() -> None:
    bundle = _sample_bundle()
    out = _valid_output()
    now = datetime(2026, 10, 5, 12, 0, 0, tzinfo=timezone.utc)

    # Mismatch: non-blocking warning
    att_mismatch = Attempt(
        job_id=bundle.job.id,
        attempt_no=1,
        fence_token=bundle.job.fence_token or "",
        worker_id="w-test",
        worker_kind="agent-cli",
        model="claude-haiku-5-5",
        prompt_version="extract@3",
        output=out,
        model_observed="claude-sonnet-4-5",
    )
    v_warn = validate(bundle.job, bundle, att_mismatch, now=now)
    assert v_warn.ok is True
    assert v_warn.reasons == ["model_mismatch"]

    # Case-insensitive match: no warning
    att_match = Attempt(
        job_id=bundle.job.id,
        attempt_no=1,
        fence_token=bundle.job.fence_token or "",
        worker_id="w-test",
        worker_kind="agent-cli",
        model="Claude-Haiku-5-5",
        prompt_version="extract@3",
        output=out,
        model_observed="claude-haiku-5-5",
    )
    v_ok = validate(bundle.job, bundle, att_match, now=now)
    assert v_ok.ok is True
    assert v_ok.reasons == []

    # Real error + mismatch still rejects
    att_stale = Attempt(
        job_id=bundle.job.id,
        attempt_no=1,
        fence_token="wrong-fence",
        worker_id="w-test",
        worker_kind="agent-cli",
        model="claude-haiku-5-5",
        prompt_version="extract@3",
        output=out,
        model_observed="claude-sonnet-4-5",
    )
    v_bad = validate(bundle.job, bundle, att_stale, now=now)
    assert v_bad.ok is False
    assert "fence_stale" in v_bad.reasons
    assert "model_mismatch" in v_bad.reasons


def test_migrate_adds_model_observed_to_existing_schema(isolated_db: Database) -> None:
    with isolated_db.transaction() as conn:
        conn.execute("ALTER TABLE job_attempts DROP COLUMN IF EXISTS model_observed")
    migrate(isolated_db)
    with isolated_db.connection() as conn:
        col = conn.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND table_name = 'job_attempts'
              AND column_name = 'model_observed'
            """
        ).fetchone()
    assert col is not None


def test_jobs_store_api_mcp_and_ops_model_observed(isolated_db: Database) -> None:
    store = PostgresGraphStore(isolated_db)
    jobs = PostgresJobs(isolated_db, store)
    store.create_owner(
        Owner(id="karim", label="Karim Haddad", kind="demo", display_name="Karim Haddad", self_aliases=["Karim"])
    )
    store.upsert_records(
        "karim",
        [
            Record(
                id="wa-101",
                owner="karim",
                source="whatsapp:work",
                at="2026-10-05T09:00:00Z",
                author="Karim",
                text="Nadia Mansour joined Falcon Tech in DIFC.",
                generation=0,
            ),
            Record(
                id="wa-102",
                owner="karim",
                source="whatsapp:work",
                at="2026-10-06T09:00:00Z",
                author="Karim",
                text="Salma Nasser works at QamarTech in Abu Dhabi.",
                generation=0,
            ),
            Record(
                id="wa-103",
                owner="karim",
                source="whatsapp:work",
                at="2026-10-07T09:00:00Z",
                author="Karim",
                text="Tariq Aziz moved to Marina Gate.",
                generation=0,
            ),
        ],
    )

    # 1) Direct PostgresJobs.submit with model_mismatch -> applied + flagged + persisted
    j1 = jobs.enqueue("karim", "extract.day", ["wa-101"], priority=1, day="2026-10-05")
    b1 = jobs.claim(Worker(id="w-cli", kind="agent-cli", model="claude-haiku-5-5", runner="agent-cli"), ["internal"])[0]
    v1 = jobs.submit(
        Attempt(
            job_id=j1.id,
            attempt_no=b1.job.attempt_no,
            fence_token=b1.job.fence_token or "",
            worker_id="w-cli",
            worker_kind="agent-cli",
            model="claude-haiku-5-5",
            prompt_version=j1.prompt_version,
            output=_valid_output(),
            tokens_in=100,
            tokens_out=50,
            model_observed="claude-sonnet-4-5",
        )
    )
    assert v1.ok is True
    assert "model_mismatch" in v1.reasons
    assert len(v1.applied_fact_ids) == 1
    assert any("Nadia Mansour" in f.text for f in store.visible_facts("karim"))

    attempts = store.list_attempts(job_id=j1.id)
    assert len(attempts) == 1
    assert attempts[0].model == "claude-haiku-5-5"
    assert attempts[0].model_observed == "claude-sonnet-4-5"

    with isolated_db.connection() as conn:
        att_id = conn.execute("SELECT id FROM job_attempts WHERE job_id = %s", (j1.id,)).fetchone()["id"]
    fetched = store.get_attempt(att_id)
    assert fetched is not None
    assert fetched.model_observed == "claude-sonnet-4-5"

    # 2) HTTP POST /v1/jobs/{id}/result forwards model_observed
    app = create_app(isolated_db, admin_token="adm-secret")
    client = TestClient(app)
    j2 = jobs.enqueue("karim", "extract.day", ["wa-102"], priority=1, day="2026-10-06")
    b2 = jobs.claim(Worker(id="w-http", kind="agent-cli", model="gemini-2.5-flash", runner="gemini-cli"), ["internal"])[0]
    res2 = client.post(
        f"/v1/jobs/{j2.id}/result",
        headers={"Authorization": "Bearer adm-secret"},
        json={
            "attempt_no": b2.job.attempt_no,
            "fence_token": b2.job.fence_token,
            "worker_id": "w-http",
            "worker_kind": "agent-cli",
            "model": "gemini-2.5-flash",
            "model_observed": "gemini-2.5-flash",
            "prompt_version": j2.prompt_version,
            "output": {
                "entities": [{"ref": "new:Salma Nasser", "kind": "person", "aliases": [], "relation_to_user": "colleague"}],
                "facts": [
                    {
                        "text": "Salma Nasser works at QamarTech in Abu Dhabi",
                        "text_orig": None,
                        "subject_path": "work/network",
                        "entities": [{"entity_id": "new:Salma Nasser", "role": "colleague"}],
                        "op": "new",
                        "target": None,
                        "valid_from": "2026-10-06",
                        "evidence": ["wa-102"],
                        "sensitive": None,
                    }
                ],
                "links": [],
            },
        },
    )
    assert res2.status_code == 200, res2.text
    assert res2.json()["ok"] is True
    assert res2.json()["reasons"] == []
    assert store.list_attempts(job_id=j2.id)[0].model_observed == "gemini-2.5-flash"

    # 3) MCP memory_submit_result forwards model_observed (and leaves None when omitted)
    j3 = jobs.enqueue("karim", "extract.day", ["wa-103"], priority=1, day="2026-10-07")
    b3 = jobs.claim(Worker(id="w-mcp", kind="agent-cli", model="gpt-5-codex", runner="codex-cli"), ["internal"])[0]
    worker_tok = create_token(isolated_db, role="worker", label="mcp-worker")["token"]
    mcp_app = create_mcp_app(db=isolated_db, store=store)
    mcp_client = TestClient(mcp_app)
    mcp_res = mcp_client.post(
        "/",
        headers={
            "Authorization": f"Bearer {worker_tok}",
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        },
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "memory_submit_result",
                "arguments": {
                    "job_id": j3.id,
                    "fence_token": b3.job.fence_token,
                    "attempt_no": b3.job.attempt_no,
                    "model": "gpt-5-codex",
                    "model_observed": "o3-mini",
                    "output": {
                        "entities": [{"ref": "new:Tariq Aziz", "kind": "person", "aliases": [], "relation_to_user": "friend"}],
                        "facts": [
                            {
                                "text": "Tariq Aziz moved to Marina Gate",
                                "text_orig": None,
                                "subject_path": "lifestyle/housing",
                                "entities": [{"entity_id": "new:Tariq Aziz", "role": "resident"}],
                                "op": "new",
                                "target": None,
                                "valid_from": "2026-10-07",
                                "evidence": ["wa-103"],
                                "sensitive": None,
                            }
                        ],
                        "links": [],
                    },
                },
            },
        },
    )
    assert mcp_res.status_code == 200, mcp_res.text
    payload = json.loads(mcp_res.json()["result"]["content"][0]["text"])
    assert payload["ok"] is True
    assert "model_mismatch" in payload["reasons"]
    assert store.list_attempts(job_id=j3.id)[0].model_observed == "o3-mini"

    # 4) GET /v1/ops/memory includes models_declared_vs_observed and all existing keys
    ops_res = client.get("/v1/ops/memory", headers={"Authorization": "Bearer adm-secret"})
    assert ops_res.status_code == 200
    ops_data = ops_res.json()
    for expected_key in (
        "queue_depth_by_priority",
        "oldest_job_age_seconds",
        "workers_online_by_model",
        "attempts_by_verdict_per_model",
        "cost_per_owner_per_week",
        "demo_cost_saved_usd",
        "demo_cost_saved_tokens",
        "provenance",
        "as_of",
        "models_declared_vs_observed",
    ):
        assert expected_key in ops_data

    mdo = ops_data["models_declared_vs_observed"]
    assert mdo["declared"] == {"claude-haiku-5-5": 1, "gemini-2.5-flash": 1, "gpt-5-codex": 1}
    assert mdo["observed"] == {"claude-sonnet-4-5": 1, "gemini-2.5-flash": 1, "o3-mini": 1}
    assert mdo["pairs"] == {
        "claude-haiku-5-5 -> claude-sonnet-4-5": 1,
        "gemini-2.5-flash -> gemini-2.5-flash": 1,
        "gpt-5-codex -> o3-mini": 1,
    }
    assert mdo["mismatches"] == 2
