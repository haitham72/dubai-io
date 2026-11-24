"""Host-side CLI worker loop pulling jobs over MCP StreamableHTTP (WP-D)."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date, timedelta
import json
import os
import re
import shlex
import subprocess
import time
from typing import Any, Callable

import httpx
import json_repair

DEFAULT_CLI_CMD = (
    'claude -p --model {model} --effort medium --output-format json --tools "" --disable-slash-commands'
)


@dataclass(frozen=True)
class CliInvocationResult:
    """Normalized structured output and token/cost telemetry from an agent CLI invocation."""

    output: dict[str, Any]
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    model_observed: str | None = None


InvokeCliFn = Callable[[dict[str, Any], str, str], CliInvocationResult | dict[str, Any]]


def compute_week_range(week_start: str) -> tuple[str, str]:
    """Return inclusive 7-day (day_from, day_to) ISO date bounds starting at week_start (YYYY-MM-DD)."""
    start = date.fromisoformat(week_start)
    end = start + timedelta(days=6)
    return start.isoformat(), end.isoformat()


def format_bundle_prompt(bundle: dict[str, Any]) -> str:
    """Render a claimed JobBundle dict into system + context + <untrusted_records> prompt text."""
    system_prompt = str(bundle.get("system_prompt") or "")
    ctx = bundle.get("context") or {}

    ent_lines = [
        f"{e.get('id')} | {e.get('name')} | {e.get('kind')} | rel={e.get('relation_to_user')} | aliases: {', '.join(e.get('aliases') or [])}"
        for e in (ctx.get("entities") or [])
    ]
    subj_lines = [
        f"{s.get('id')} | {s.get('path')} | {s.get('label')}"
        for s in (ctx.get("subjects") or [])
    ]
    fact_lines = [
        f"{f.get('id')} | {f.get('valid_from', '')} | {f.get('text')}"
        for f in (ctx.get("facts") or [])
    ]
    rec_lines = []
    for r in bundle.get("records") or []:
        safe_text = str(r.get("text") or "").replace("</untrusted_records>", "<\\/untrusted_records>")
        rec_lines.append(
            f"[{r.get('id')}] ({r.get('at')}) {r.get('source')} | {r.get('author')}: {safe_text}"
        )

    user_prompt = (
        "KNOWN ENTITIES:\n"
        + ("\n".join(ent_lines) or "(none yet)")
        + "\n\nKNOWN SUBJECTS:\n"
        + ("\n".join(subj_lines) or "(none yet)")
        + "\n\nACTIVE FACTS:\n"
        + ("\n".join(fact_lines) or "(none yet)")
        + "\n\n<untrusted_records>\n"
        + ("\n".join(rec_lines) or "(none)")
        + "\n</untrusted_records>"
    )
    return f"{system_prompt}\n\n{user_prompt}".strip()


def _extract_json_dict(text: str) -> dict[str, Any]:
    cleaned = re.sub(r"<think>.*?</think>", "", text or "", flags=re.S).strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", cleaned, flags=re.S)
    if fence:
        cleaned = fence.group(1).strip()
    i, j = cleaned.find("{"), cleaned.rfind("}")
    if i < 0 or j <= i:
        raise ValueError("CLI output contained no JSON object")
    snippet = cleaned[i : j + 1]
    try:
        parsed = json.loads(snippet)
    except json.JSONDecodeError:
        parsed = json_repair.loads(snippet)
    if not isinstance(parsed, dict):
        raise ValueError("CLI JSON output is not an object")
    return parsed


def _clean_model_str(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        if stripped:
            return stripped
    return None


def _usage_map_score(entry: Any) -> float:
    if isinstance(entry, bool):
        return 0.0
    if isinstance(entry, (int, float)):
        return float(entry)
    if not isinstance(entry, dict):
        return 0.0
    if isinstance(entry.get("tokens"), dict):
        return _usage_map_score(entry["tokens"])
    for total_key in ("total", "total_tokens", "totalTokens"):
        val = entry.get(total_key)
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            return float(val)
    total = 0.0
    for k, v in entry.items():
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            kl = str(k).lower()
            if any(
                tok in kl
                for tok in ("token", "input", "output", "prompt", "candidate", "response", "cached", "thought")
            ):
                total += float(v)
    return total


def _pick_model_from_usage(usage_map: Any) -> str | None:
    if not isinstance(usage_map, dict) or not usage_map:
        return None
    candidates: list[tuple[str, float]] = []
    for raw_key, val in usage_map.items():
        name = _clean_model_str(raw_key)
        if name:
            candidates.append((name, _usage_map_score(val)))
    if not candidates:
        return None
    best_name, _ = max(candidates, key=lambda item: item[1])
    return best_name


def extract_observed_model(parsed: dict[str, Any]) -> str | None:
    """Extract the model reported by CLI runner metadata (contract v1.2)."""
    if not isinstance(parsed, dict):
        return None
    picked = _pick_model_from_usage(parsed.get("modelUsage"))
    if picked:
        return picked
    stats = parsed.get("stats")
    if isinstance(stats, dict):
        picked = _pick_model_from_usage(stats.get("models"))
        if picked:
            return picked
    for key in ("model", "model_id", "modelVersion"):
        cleaned = _clean_model_str(parsed.get(key))
        if cleaned:
            return cleaned
    return None


def default_invoke_cli(bundle: dict[str, Any], model: str, command: str) -> CliInvocationResult:
    """Run an agent CLI subprocess (e.g. claude -p / codex exec / gemini) for one JobBundle."""
    cmd_str = command.format(model=model)
    cmd = shlex.split(cmd_str)
    prompt = format_bundle_prompt(bundle)
    proc = subprocess.run(
        cmd,
        input=prompt,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=900,
        check=False,
    )
    stdout = (proc.stdout or "").strip()
    if proc.returncode != 0 and not stdout:
        raise RuntimeError(f"agent CLI exited with {proc.returncode}: {(proc.stderr or '').strip()[:500]}")

    parsed = _extract_json_dict(stdout)
    model_observed = extract_observed_model(parsed)
    tokens_in = 0
    tokens_out = 0
    cost_usd = 0.0
    if "result" in parsed and "facts" not in parsed and "entities" not in parsed:
        if parsed.get("is_error"):
            raise RuntimeError(f"agent CLI reported error: {str(parsed.get('result'))[:500]}")
        usage = parsed.get("usage") or {}
        tokens_in = int(
            (usage.get("input_tokens") or 0)
            + (usage.get("cache_read_input_tokens") or 0)
            + (usage.get("cache_creation_input_tokens") or 0)
        )
        tokens_out = int(usage.get("output_tokens") or 0)
        cost_usd = round(float(parsed.get("total_cost_usd") or 0.0), 6)
        inner = parsed.get("result")
        payload = inner if isinstance(inner, dict) else _extract_json_dict(str(inner or ""))
    else:
        payload = parsed

    return CliInvocationResult(
        output=payload,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_usd=cost_usd,
        model_observed=model_observed,
    )


class MCPHttpClient:
    """Minimal stateless JSON-RPC 2.0 client for the temporal-memory MCP endpoint."""

    def __init__(
        self,
        url: str,
        token: str,
        *,
        transport: Any | None = None,
        http_client: Any | None = None,
        timeout: float = 120.0,
    ) -> None:
        self.url = url
        self._token = token
        self._seq = 0
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        }
        if http_client is not None:
            self._client = http_client
            self._owns_client = False
        elif transport is not None and callable(getattr(transport, "post", None)):
            self._client = transport
            self._owns_client = False
        else:
            self._client = httpx.Client(
                transport=transport,
                follow_redirects=True,
                timeout=timeout,
            )
            self._owns_client = True

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> MCPHttpClient:
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        self._seq += 1
        resp = self._client.post(
            self.url,
            headers=self._headers,
            json={
                "jsonrpc": "2.0",
                "id": self._seq,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments or {}},
            },
        )
        resp.raise_for_status()
        body = resp.json()
        if "error" in body:
            raise RuntimeError(f"MCP JSON-RPC error: {body['error']}")
        result = body.get("result") or {}
        content = result.get("content") or []
        text = content[0].get("text", "") if content and isinstance(content[0], dict) else ""
        if result.get("isError"):
            raise RuntimeError(f"MCP tool {name} failed: {text}")
        if not text:
            return {}
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {"value": parsed}


def _normalize_cli_result(raw: CliInvocationResult | dict[str, Any]) -> CliInvocationResult:
    if isinstance(raw, CliInvocationResult):
        return raw
    if "output" in raw and isinstance(raw["output"], dict):
        return CliInvocationResult(
            output=raw["output"],
            tokens_in=int(raw.get("tokens_in", 0)),
            tokens_out=int(raw.get("tokens_out", 0)),
            cost_usd=float(raw.get("cost_usd", 0.0)),
            model_observed=_clean_model_str(raw.get("model_observed")),
        )
    return CliInvocationResult(output=raw)


def run_worker(
    *,
    url: str,
    token: str,
    model: str,
    command: str = DEFAULT_CLI_CMD,
    owner: str | None = None,
    week: str | None = None,
    day_from: str | None = None,
    day_to: str | None = None,
    limit: int = 7,
    once: bool = False,
    runner: str = "agent-cli",
    worker_id: str | None = None,
    poll_interval: float = 5.0,
    invoke_cli_fn: InvokeCliFn | None = None,
    transport: Any | None = None,
    http_client: Any | None = None,
) -> list[dict[str, Any]]:
    """Claim jobs over MCP, invoke the CLI extractor, and submit results with explicit model."""
    if not model or not model.strip():
        raise ValueError("--model is required")

    eff_from, eff_to = (compute_week_range(week) if week else (day_from, day_to))
    invoker = invoke_cli_fn or default_invoke_cli
    wid = worker_id or f"{runner}:{model}"
    verdicts: list[dict[str, Any]] = []

    with MCPHttpClient(url=url, token=token, transport=transport, http_client=http_client) as mcp:
        while True:
            claimed = mcp.call_tool(
                "memory_claim_job",
                {
                    "owner": owner,
                    "day_from": eff_from,
                    "day_to": eff_to,
                    "limit": int(limit),
                    "model": model,
                    "runner": runner,
                    "worker_id": wid,
                },
            )
            bundles = claimed.get("jobs") or []
            if not bundles:
                if once:
                    break
                time.sleep(poll_interval)
                continue

            for bundle in bundles:
                job = bundle["job"]
                cli_res = _normalize_cli_result(invoker(bundle, model, command))
                submit_args: dict[str, Any] = {
                    "job_id": job["id"],
                    "fence_token": job["fence_token"],
                    "attempt_no": int(job["attempt_no"]),
                    "output": cli_res.output,
                    "model": model,
                    "tokens_in": cli_res.tokens_in,
                    "tokens_out": cli_res.tokens_out,
                    "cost_usd": cli_res.cost_usd,
                    "worker_id": wid,
                    "worker_kind": "agent-cli",
                }
                if cli_res.model_observed is not None:
                    submit_args["model_observed"] = cli_res.model_observed
                verdict = mcp.call_tool("memory_submit_result", submit_args)
                verdicts.append(verdict)

            if once:
                break

    return verdicts


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Temporal Memory external agent-CLI MCP worker.")
    parser.add_argument("--url", default=os.environ.get("TM_MCP_URL", "http://127.0.0.1:8000/mcp"))
    parser.add_argument("--token", default=os.environ.get("TM_MCP_TOKEN", ""))
    parser.add_argument("--model", required=True, help="Explicit model name recorded on every attempt.")
    parser.add_argument("--command", default=os.environ.get("TM_AGENT_CLI_CMD", DEFAULT_CLI_CMD))
    parser.add_argument("--owner", default=None, help="Optional owner id filter.")
    parser.add_argument("--week", default=None, help="ISO start date YYYY-MM-DD (claims 7-day range).")
    parser.add_argument("--day-from", default=None, help="Optional inclusive start day (YYYY-MM-DD).")
    parser.add_argument("--day-to", default=None, help="Optional inclusive end day (YYYY-MM-DD).")
    parser.add_argument("--limit", type=int, default=7, help="Max jobs to claim per batch (default: 7).")
    parser.add_argument("--once", action="store_true", help="Claim and process one batch, then exit.")
    parser.add_argument("--runner", default="agent-cli", help="Runner label reported during claim.")
    parser.add_argument("--worker-id", default=None, help="Explicit worker_id override.")
    parser.add_argument("--poll-interval", type=float, default=5.0, help="Sleep seconds when queue is empty.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.token:
        parser.error("--token (or TM_MCP_TOKEN) is required")

    verdicts = run_worker(
        url=args.url,
        token=args.token,
        model=args.model,
        command=args.command,
        owner=args.owner,
        week=args.week,
        day_from=args.day_from,
        day_to=args.day_to,
        limit=args.limit,
        once=args.once,
        runner=args.runner,
        worker_id=args.worker_id,
        poll_interval=args.poll_interval,
    )
    print(json.dumps({"processed": len(verdicts), "verdicts": verdicts}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
