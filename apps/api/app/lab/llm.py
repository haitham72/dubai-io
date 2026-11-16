"""Local LM Studio client for the lab: chat-to-JSON, embeddings, context-budget maths.

Only the local server is used (settings.lab_*). Thinking is switched off per request.
Context safety: the batch budget comes from the model's *loaded* context length; a call that
still overflows raises ContextOverflow so the caller can split the batch and retry.
"""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request

from app.config import settings

OUTPUT_RESERVE = 1800  # tokens kept free for the JSON answer
SAFETY = 0.80  # use at most 80% of what is left
CHARS_PER_TOKEN = 2.2  # deliberately pessimistic: Arabic / Arabizi / emoji tokenise badly


USAGE = {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "seconds": 0.0}  # real numbers reported by LM Studio


class LabLLMError(Exception):
    pass


class ContextOverflow(LabLLMError):
    pass


def est_tokens(text: str) -> int:
    return int(len(text) / CHARS_PER_TOKEN) + 1


def _http(path: str, payload: dict | None = None, timeout: float = 600) -> dict:
    url = settings.lab_base_url + path
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        if exc.code == 400 and re.search(r"context|too (long|many)|exceed", body, re.I):
            raise ContextOverflow(body[:300]) from exc
        raise LabLLMError(f"LM Studio HTTP {exc.code}: {body[:300]}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise LabLLMError(f"LM Studio not reachable at {settings.lab_base_url}: {exc}") from exc


def loaded_context(model: str | None = None) -> int:
    """Context length LM Studio actually loaded the model with (not the model's maximum)."""
    if settings.lab_context_override:
        return settings.lab_context_override
    model = model or settings.lab_model
    info = _http("/api/v0/models", timeout=10)
    for m in info.get("data", []):
        if m.get("id") == model:
            if m.get("state") != "loaded":
                raise LabLLMError(f"{model} is not loaded in LM Studio (state={m.get('state')})")
            return int(m.get("loaded_context_length") or 4096)
    raise LabLLMError(f"{model} is not listed by LM Studio")


def input_budget(context: int, overhead_tokens: int, reserve: int = OUTPUT_RESERVE) -> int:
    """Tokens of chat text one call may carry."""
    return max(400, int((context - reserve - overhead_tokens) * SAFETY))


def _strip_think(text: str) -> str:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    return text.strip()


def _parse_json(text: str) -> dict:
    text = _strip_think(text)
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise LabLLMError("model returned no JSON object")
    return json.loads(text[start : end + 1])


def chat_json(system: str, user: str, schema: dict, *, name: str = "answer", max_tokens: int = OUTPUT_RESERVE,
              model: str | None = None) -> dict:
    payload = {
        "model": model or settings.lab_model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": 0,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_schema", "json_schema": {"name": name, "strict": True, "schema": schema}},
        "chat_template_kwargs": {"enable_thinking": False},
    }
    started = time.time()
    out = _http("/v1/chat/completions", payload)
    usage = out.get("usage") or {}
    USAGE["calls"] += 1
    USAGE["prompt_tokens"] += usage.get("prompt_tokens", 0)
    USAGE["completion_tokens"] += usage.get("completion_tokens", 0)
    USAGE["seconds"] += time.time() - started
    choice = out["choices"][0]
    try:
        # Some LM Studio / template combinations route the whole answer into `reasoning_content` and leave `content`
        # empty (seen with qwen3.5: 790 reasoning tokens, valid JSON, empty content). The JSON is the same either way.
        message = choice["message"]
        return _parse_json(message.get("content") or message.get("reasoning_content") or "")
    except (LabLLMError, json.JSONDecodeError) as exc:
        if choice.get("finish_reason") == "length":
            raise ContextOverflow("output hit max_tokens before the JSON closed") from exc
        raise LabLLMError(f"unparseable model output: {exc}") from exc


def embed(texts: list[str], *, kind: str = "document") -> list[list[float]]:
    """nomic-embed needs a task prefix; documents and queries use different ones."""
    prefix = "search_query: " if kind == "query" else "search_document: "
    vectors: list[list[float]] = []
    for i in range(0, len(texts), 16):
        batch = [prefix + t[:2400] for t in texts[i : i + 16]]  # nomic context is 2048 tokens
        out = _http("/v1/embeddings", {"model": settings.lab_embed_model, "input": batch}, timeout=300)
        vectors.extend(item["embedding"] for item in sorted(out["data"], key=lambda d: d["index"]))
    return vectors


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    return dot / (na * nb) if na and nb else 0.0
