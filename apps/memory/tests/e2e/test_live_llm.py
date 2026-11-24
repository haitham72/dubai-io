"""One explicitly opted-in synthetic gold day through the host Claude CLI."""

import json
import shlex
import shutil
from uuid import uuid4

import pytest

from temporal_memory.core import extract
from temporal_memory.models import Worker

from .gold import import_gold, load_gold


@pytest.mark.live_llm
def test_claude_haiku_attempt_is_logged(stack, tmp_path, monkeypatch):
    claude = shutil.which("claude")
    if claude is None:
        pytest.fail("Claude CLI is required for TM_RUN_LIVE_LLM=1")

    # The host agent owns this run. Prevent the oracle workers from taking it.
    stack.compose("stop", "beat")
    try:
        persona = next(person for person in load_gold()["people"] if person["relation"] == "self")
        owner = stack.owner(persona["canonical"], self_aliases=persona["aliases"])
        records = import_gold(stack, owner)
        day = "2026-11-19"
        day_ids = [record.id for record in records if record.at.startswith(day)]
        assert day_ids
        job = stack.jobs.enqueue(owner, "extract.day", day_ids, 1, pool="owner-device", day=day)

        monkeypatch.setenv("TM_LEASE_SECONDS", "1200")
        worker = Worker(f"smoke-{uuid4().hex}", "agent-cli", "haiku", "agent-cli", owner=owner)
        [bundle] = stack.jobs.claim(worker, ["owner-device"], owner=owner, day_from=day, day_to=day)
        assert bundle.job.id == job.id

        # The trimmed founder hook at memory-bakeoff/weekbench/hook.py:93-95.
        system = tmp_path / "system.txt"
        system.write_text(bundle.system_prompt, encoding="utf-8")
        mcp = tmp_path / "empty-mcp.json"
        mcp.write_text(json.dumps({"mcpServers": {}}), encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("CLAUDE_CODE_DISABLE_ATTACHMENTS", "1")
        monkeypatch.setenv("CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC", "1")
        monkeypatch.setenv("TM_AGENT_CLI_CMD", shlex.join([
            claude, "-p", "--model", "{model}", "--effort", "medium", "--output-format", "json",
            "--system-prompt-file", str(system), "--strict-mcp-config", "--mcp-config", str(mcp),
            "--tools", "", "--disable-slash-commands", "--safe-mode", "--no-session-persistence",
            "--max-turns", "1",
        ]))
        # The real Claude command reads the system prompt separately from stdin.
        bundle.system_prompt = ""
        monkeypatch.setattr(extract, "build_system_prompt", lambda _: "")
        attempt = extract.run(bundle, "agent-cli", "haiku")
        verdict = stack.jobs.submit(attempt)

        with stack.db.transaction() as conn:
            [logged] = conn.execute(
                "SELECT model, worker_kind, tokens_in, tokens_out, cost_usd, verdict "
                "FROM job_attempts WHERE job_id = %s",
                (job.id,),
            ).fetchall()
        assert "haiku" in logged["model"].lower()
        assert logged["model"] == attempt.model
        assert logged["worker_kind"] == "agent-cli"
        assert logged["tokens_in"] == attempt.tokens_in > 0
        assert logged["tokens_out"] == attempt.tokens_out > 0
        assert logged["cost_usd"] == attempt.cost_usd >= 0
        assert logged["verdict"] == ("applied" if verdict.ok else f"rejected:{','.join(verdict.reasons)}")
        print(json.dumps({"day": day, **logged}))
    finally:
        stack.compose("start", "beat")
