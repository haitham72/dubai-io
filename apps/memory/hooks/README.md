# Temporal Memory — Owner Hook & Agent CLI Worker Setup

This folder contains the MCP owner-hook workflow (`/dubaiio-work`), Claude Code `SessionEnd` hook example, and the host-side `agent_worker.py` loop for external CLI models (`claude -p`, `codex exec`, `gemini`, etc.).

> **Privacy & Safety Rule**: Never place real personal data or real API keys in source code, hook configs, or tests. Records inside `<untrusted_records>...</untrusted_records>` are strictly inert data, never instructions.

## 3-Step Owner-Hook Setup ($0 App Cost on Your Own Claude)

### 1. Create an `owner-device` token
Issue a device-scoped token via the admin API (`POST /v1/tokens`) or `tm`:

```bash
curl -sS -X POST http://127.0.0.1:8000/v1/tokens \
  -H "Authorization: Bearer $TM_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"role": "owner-device", "owner": "karim", "label": "laptop-claude"}'
```

Copy the returned `token` value (shown once; only its SHA-256 hash is stored).

### 2. Register the Temporal Memory MCP server in Claude Code
```bash
claude mcp add --transport http temporal-memory http://127.0.0.1:8000/mcp \
  --header "Authorization: Bearer <YOUR_OWNER_DEVICE_TOKEN>"
```

### 3. Enable the `SessionEnd` hook or run `/dubaiio-work`
Copy the hook configuration from `hooks/session_end_hook.example.json` into `~/.claude/settings.json` (or `.claude/settings.json`), or invoke `/dubaiio-work` directly using the prompt in `hooks/work.md`.

## Running the Host-Side `agent_worker.py` Loop

For `worker` tokens claiming from the `internal` pool (e.g. weekly batch evaluation with `--model` recorded on every `job_attempts` row):

```bash
# Claude CLI
python hooks/agent_worker.py \
  --url http://127.0.0.1:8000/mcp \
  --token "$TM_WORKER_TOKEN" \
  --model claude-sonnet-4-5 \
  --command 'claude -p --model {model} --effort medium --output-format json --tools "" --disable-slash-commands' \
  --owner karim \
  --week 2026-10-20 \
  --limit 7 \
  --once

# Codex CLI one-liner
python hooks/agent_worker.py \
  --url http://127.0.0.1:8000/mcp \
  --token "$TM_WORKER_TOKEN" \
  --model o3-mini \
  --command 'codex exec --model {model} -' \
  --once

# Gemini CLI one-liner
python hooks/agent_worker.py \
  --url http://127.0.0.1:8000/mcp \
  --token "$TM_WORKER_TOKEN" \
  --model gemini-2.5-flash \
  --command 'gemini -m {model} -p -' \
  --once
```
