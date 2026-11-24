"""claude -p prints a JSON envelope whose `result` is usually a ```json fenced string: it must still parse."""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from temporal_memory.core import extract


def _stub(monkeypatch: pytest.MonkeyPatch, stdout: str, rc: int = 0) -> None:
    monkeypatch.setattr(extract.subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=rc, stdout=stdout, stderr=""))


def test_fenced_result_inside_envelope_parses_and_records_cost(monkeypatch: pytest.MonkeyPatch) -> None:
    inner = {"entities": [], "facts": []}
    env = {"result": "```json\n" + json.dumps(inner) + "\n```", "total_cost_usd": 0.0123,
           "usage": {"input_tokens": 10, "output_tokens": 7, "cache_read_input_tokens": 5}}
    _stub(monkeypatch, json.dumps(env))
    out, model, tin, tout, cost, _obs = extract._run_cli("sys", "user", "m")
    assert (tin, tout, cost) == (15, 7, 0.0123) and model == "m"
    assert out.facts == [] 


def test_cli_error_envelope_still_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub(monkeypatch, json.dumps({"result": "boom", "is_error": True}))
    with pytest.raises(RuntimeError):
        extract._run_cli("sys", "user", "m")


def test_agent_cli_classifier_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    from temporal_memory.privacy import sensitive

    monkeypatch.setenv("TM_CLASSIFIER_RUNNER", "agent-cli")
    labels = ["padel league", "diagnosed with diabetes"]
    reply = {"result": "```json\n" + json.dumps({"items": [{"n": 1, "category": "none"}]}) + "\n```"}
    monkeypatch.setattr(sensitive._subprocess if hasattr(sensitive, "_subprocess") else __import__("subprocess"), "run",
                        lambda *a, **k: SimpleNamespace(returncode=0, stdout=json.dumps(reply), stderr=""))
    blocked = sensitive.screen(labels)
    assert "padel league" not in blocked and blocked["diagnosed with diabetes"] == "unscreened"


def test_agent_cli_classifier_outage_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    from temporal_memory.privacy import sensitive

    monkeypatch.setenv("TM_CLASSIFIER_RUNNER", "agent-cli")
    monkeypatch.setattr(__import__("subprocess"), "run", lambda *a, **k: SimpleNamespace(returncode=1, stdout="", stderr="x"))
    with pytest.raises(sensitive.ScreenUnavailable):
        sensitive.screen(["anything"])
