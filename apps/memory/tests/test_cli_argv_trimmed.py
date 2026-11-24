"""The claude CLI runner uses the trimmed flag set and a neutral cwd (no real call is made)."""
from __future__ import annotations

import json
import os
from types import SimpleNamespace

import pytest

from temporal_memory.core import extract


def _flag(argv: list[str], name: str) -> str:
    return argv[argv.index(name) + 1]


def test_argv_has_trimmed_flags_and_never_bare() -> None:
    argv, prefix = extract.agent_cli_argv("claude-haiku-5-5", "SYS", "claude")
    assert argv[:2] == ["claude", "-p"]
    assert "--bare" not in argv
    assert _flag(argv, "--model") == "haiku"
    assert _flag(argv, "--effort") == "medium"
    assert _flag(argv, "--output-format") == "json"
    assert _flag(argv, "--system-prompt") == "SYS"
    assert "--strict-mcp-config" in argv
    assert _flag(argv, "--tools") == ""
    assert "--disable-slash-commands" in argv
    cfg = _flag(argv, "--mcp-config")
    assert json.load(open(cfg, encoding="utf-8")) == {"mcpServers": {}}
    assert prefix == ""


def test_long_system_prompt_goes_to_stdin_not_argv() -> None:
    big = "x" * (extract._MAX_SYSTEM_PROMPT_ARG + 1)
    argv, prefix = extract.agent_cli_argv("haiku", big, "claude")
    assert "--system-prompt" not in argv and prefix.startswith(big)


def test_model_alias_mapping() -> None:
    assert extract.cli_model_alias("claude-haiku-5-5") == "haiku"
    assert extract.cli_model_alias("claude-haiku-4-5-20251001") == "haiku"
    assert extract.cli_model_alias("default") == "haiku"
    assert extract.cli_model_alias("claude-sonnet-5-5") == "sonnet"
    assert extract.cli_model_alias("gemini-x") == "gemini-x"


def test_custom_non_claude_command_is_run_as_is() -> None:
    argv, prefix = extract.agent_cli_argv("m1", "SYS", "codex exec --model {model}")
    assert argv == ["codex", "exec", "--model", "m1"] and prefix.startswith("SYS")


def test_default_model_matches_observed_model() -> None:
    from temporal_memory.config import get_settings

    assert get_settings().cloud_model == "claude-haiku-5-5"


def test_runner_and_classifier_use_neutral_cwd(monkeypatch: pytest.MonkeyPatch) -> None:
    from temporal_memory.privacy import sensitive

    seen: list[dict] = []

    def fake_run(argv, **kw):
        seen.append({"argv": argv, **kw})
        if "Labels" in kw.get("input", ""):
            out = {"result": json.dumps({"items": [{"n": 1, "category": "none"}]})}
        else:
            out = {"result": json.dumps({"entities": [], "facts": []}), "usage": {"input_tokens": 1, "output_tokens": 1}}
        return SimpleNamespace(returncode=0, stdout=json.dumps(out), stderr="")

    monkeypatch.setattr(extract.subprocess, "run", fake_run)
    monkeypatch.setenv("TM_CLASSIFIER_RUNNER", "agent-cli")
    monkeypatch.delenv("TM_AGENT_CLI_CMD", raising=False)
    extract._run_cli("sys", "user", "claude-haiku-5-5")
    sensitive.screen(["padel league"])
    assert len(seen) == 2
    neutral = extract.neutral_cwd()
    for call in seen:
        assert call["cwd"] == neutral and os.listdir(neutral) == ["empty-mcp.json"]
        assert "--bare" not in call["argv"] and "--tools" in call["argv"]
