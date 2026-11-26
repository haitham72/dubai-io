"""HTTP primary client (+ transitional /mcp fallback) for temporal_memory."""
from __future__ import annotations

import json
from typing import Any, Callable, Literal
from urllib.parse import quote

import httpx

from .models import (
    ConsentDeniedError,
    FactResolutionAction,
    MemoryBridgeError,
    MemoryBridgeUnavailable,
    SensitiveContentError,
)


def _quote(value: str) -> str:
    return quote(str(value), safe="")


def _safe_detail(resp: httpx.Response) -> tuple[str, str | None]:
    try:
        data = resp.json()
    except Exception:
        return (f"HTTP {resp.status_code}", None)
    if isinstance(data, dict):
        detail = str(data.get("detail") or data.get("message") or f"HTTP {resp.status_code}")
        cat = data.get("category") or data.get("quarantine_category")
        return (detail, str(cat) if cat else None)
    return (f"HTTP {resp.status_code}", None)


def _parse_mcp_payload(resp: httpx.Response) -> dict[str, Any]:
    content_type = (resp.headers.get("content-type") or "").lower()
    if "text/event-stream" in content_type:
        last_json: dict[str, Any] | None = None
        for line in resp.text.splitlines():
            if line.startswith("data:"):
                raw = line[5:].strip()
                if raw:
                    last_json = json.loads(raw)
        data = last_json or {}
    else:
        data = resp.json()

    if not isinstance(data, dict):
        raise MemoryBridgeError("invalid MCP JSON-RPC response", status_code=502)
    if "error" in data and data["error"] is not None:
        err = data["error"]
        msg = err.get("message", "MCP tool call failed") if isinstance(err, dict) else str(err)
        raise MemoryBridgeError(msg, code="mcp_error", status_code=502)

    result = data.get("result")
    if not isinstance(result, dict):
        raise MemoryBridgeError("missing MCP result object", status_code=502)
    if result.get("isError"):
        raise MemoryBridgeError("MCP tool returned error", code="mcp_tool_error", status_code=400)

    structured = result.get("structuredContent")
    if isinstance(structured, dict):
        return structured

    content = result.get("content")
    if isinstance(content, list) and content:
        first = content[0]
        if isinstance(first, dict) and isinstance(first.get("text"), str):
            parsed = json.loads(first["text"])
            if isinstance(parsed, dict):
                return parsed
    return result


class HttpTemporalMemoryClient:
    """TemporalMemoryClient over temporal_memory HTTP REST (+ /mcp fallback for CR-TM-4)."""

    def __init__(
        self,
        *,
        base_url: str,
        service_token: str,
        admin_token: str | None = None,
        timeout_seconds: float = 10.0,
        transport: httpx.BaseTransport | None = None,
        owner_token_resolver: Callable[[str], str | None] | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        if not base_url or not base_url.strip():
            raise MemoryBridgeUnavailable("TM_BASE_URL is required")
        if not service_token or not service_token.strip():
            raise MemoryBridgeUnavailable("TM_SERVICE_TOKEN is required")
        self._base_url = base_url.strip().rstrip("/")
        self._service_token = service_token.strip()
        self._admin_token = (admin_token or "").strip()
        self._owner_token_resolver = owner_token_resolver
        self._owns_client = http_client is None
        self._client = http_client or httpx.Client(
            base_url=self._base_url,
            timeout=timeout_seconds,
            transport=transport,
        )

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def _admin_headers(self) -> dict[str, str]:
        if not self._admin_token:
            raise MemoryBridgeUnavailable(
                "TM_ADMIN_TOKEN is required for owner and token provisioning"
            )
        return {"Authorization": f"Bearer {self._admin_token}"}

    def _owner_headers(self, owner_id: str) -> dict[str, str]:
        token = self._owner_token_resolver(owner_id) if self._owner_token_resolver else None
        effective = (token or self._service_token).strip()
        if not effective:
            raise MemoryBridgeUnavailable("no bearer token available for owner request")
        return {"Authorization": f"Bearer {effective}"}

    def _request(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str],
        json_body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        allow_404: bool = False,
    ) -> httpx.Response | None:
        try:
            resp = self._client.request(
                method,
                path,
                headers=headers,
                json=json_body,
                params=params,
            )
        except httpx.HTTPError as exc:
            raise MemoryBridgeUnavailable(
                f"temporal_memory request failed: {exc.__class__.__name__}"
            ) from exc

        if allow_404 and resp.status_code == 404:
            return None

        if resp.status_code >= 500:
            raise MemoryBridgeUnavailable(
                f"temporal_memory upstream returned {resp.status_code}",
                status_code=resp.status_code,
            )

        if resp.status_code in (401, 403):
            detail, _ = _safe_detail(resp)
            raise ConsentDeniedError(detail, status_code=resp.status_code)

        if resp.status_code == 404:
            detail, _ = _safe_detail(resp)
            raise MemoryBridgeError(detail, code="not_found", status_code=404)

        if resp.status_code >= 400:
            detail, cat = _safe_detail(resp)
            if cat or "credential" in detail.lower() or "sensitive" in detail.lower():
                raise SensitiveContentError(
                    cat or "credential",
                    detail,
                    status_code=resp.status_code,
                )
            raise MemoryBridgeError(detail, status_code=resp.status_code)

        return resp

    def _mcp_tool_call(
        self,
        owner_id: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        headers = {
            **self._owner_headers(owner_id),
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        }
        payload = {
            "jsonrpc": "2.0",
            "id": "cs-mcp-1",
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }
        resp = self._request("POST", "/mcp", headers=headers, json_body=payload)
        assert resp is not None
        return _parse_mcp_payload(resp)

    # ------------------------------------------------------------------ admin
    def ensure_owner(
        self,
        owner_id: str,
        *,
        label: str,
        display_name: str = "",
        kind: Literal["real", "simulated", "demo"] = "real",
        timezone: str = "Asia/Dubai",
    ) -> dict[str, Any]:
        resp = self._request(
            "POST",
            "/v1/owners",
            headers=self._admin_headers(),
            json_body={
                "id": owner_id,
                "label": label,
                "kind": kind,
                "display_name": display_name,
                "self_aliases": [],
                "timezone": timezone,
            },
        )
        assert resp is not None
        return dict(resp.json())

    def mint_owner_device_token(
        self,
        owner_id: str,
        *,
        label: str = "cs-bridge",
    ) -> dict[str, Any]:
        resp = self._request(
            "POST",
            "/v1/tokens",
            headers=self._admin_headers(),
            json_body={"role": "owner-device", "owner": owner_id, "label": label},
        )
        assert resp is not None
        return dict(resp.json())

    def revoke_token(self, token_id: str) -> dict[str, Any]:
        resp = self._request(
            "DELETE",
            f"/v1/tokens/{_quote(token_id)}",
            headers=self._admin_headers(),
        )
        assert resp is not None
        return dict(resp.json())

    # ------------------------------------------------------------ owner-scoped
    def upsert_record_and_enqueue(
        self,
        owner_id: str,
        *,
        record_id: str,
        source: str,
        at: str,
        author: str,
        text: str,
        enqueue: Literal["extract.live", "extract.day", "none"] = "extract.live",
        direct_fact: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "records": [
                {
                    "id": record_id,
                    "source": source,
                    "at": at,
                    "author": author,
                    "text": text,
                }
            ],
            "enqueue": enqueue,
        }
        if direct_fact is not None:
            body["direct_fact"] = direct_fact
        resp = self._request(
            "POST",
            f"/v1/owners/{_quote(owner_id)}/records",
            headers=self._owner_headers(owner_id),
            json_body=body,
        )
        assert resp is not None
        return dict(resp.json())

    def context_pack(
        self,
        owner_id: str,
        text: str,
        *,
        max_tokens: int = 1500,
    ) -> dict[str, Any]:
        resp = self._request(
            "POST",
            f"/v1/owners/{_quote(owner_id)}/context",
            headers=self._owner_headers(owner_id),
            json_body={"text": text, "max_tokens": int(max_tokens)},
            allow_404=True,
        )
        if resp is not None:
            return dict(resp.json())
        return self._mcp_tool_call(
            owner_id,
            "memory_context",
            {"text": text, "owner": owner_id, "max_tokens": int(max_tokens)},
        )

    def reinforce_recall(self, owner_id: str, fact_ids: list[str]) -> dict[str, float]:
        if not fact_ids:
            return {}
        response = self._request(
            "POST", f"/v1/owners/{_quote(owner_id)}/recall",
            headers=self._owner_headers(owner_id), json_body={"fact_ids": fact_ids},
        )
        return response.json()["weights"]

    def search_facts(
        self,
        owner_id: str,
        query: str,
        *,
        limit: int = 20,
        source_prefix: str | None = None,
        include_lowered: bool = False,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"q": query, "limit": int(limit)}
        if include_lowered:
            params.update(include_lowered=True, reinforce=False)
        if source_prefix is not None:
            params["source_prefix"] = source_prefix
        resp = self._request(
            "GET",
            f"/v1/owners/{_quote(owner_id)}/search",
            headers=self._owner_headers(owner_id),
            params=params,
            allow_404=True,
        )
        if resp is not None:
            payload = resp.json()
            facts = payload.get("facts", []) if isinstance(payload, dict) else payload
            return list(facts)

        mcp_out = self._mcp_tool_call(
            owner_id,
            "memory_search",
            {"query": query, "owner": owner_id, "limit": int(limit)},
        )
        facts = list(mcp_out.get("facts", []))
        if source_prefix is None:
            return facts
        filtered: list[dict[str, Any]] = []
        for item in facts:
            srcs = item.get("sources") or item.get("evidence_sources")
            if isinstance(srcs, list) and srcs:
                if all(str(s).startswith(source_prefix) for s in srcs):
                    filtered.append(item)
            elif isinstance(item.get("source"), str):
                if item["source"].startswith(source_prefix):
                    filtered.append(item)
        return filtered

    def get_vault_subjects(self, owner_id: str) -> dict[str, Any]:
        resp = self._request(
            "GET",
            f"/v1/owners/{_quote(owner_id)}/vault/subjects",
            headers=self._owner_headers(owner_id),
        )
        assert resp is not None
        return dict(resp.json())

    def get_vault_people(self, owner_id: str) -> dict[str, Any]:
        resp = self._request(
            "GET",
            f"/v1/owners/{_quote(owner_id)}/vault/people",
            headers=self._owner_headers(owner_id),
        )
        assert resp is not None
        return dict(resp.json())

    def get_hypotheses(self, owner_id: str) -> dict[str, Any]:
        resp = self._request(
            "GET",
            f"/v1/owners/{_quote(owner_id)}/hypotheses",
            headers=self._owner_headers(owner_id),
        )
        assert resp is not None
        return dict(resp.json())

    def get_timeline(
        self,
        owner_id: str,
        *,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 200,
        lowered: bool = False,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"limit": int(limit)}
        if lowered:
            params["lowered"] = True
        if date_from is not None:
            params["date_from"] = date_from
        if date_to is not None:
            params["date_to"] = date_to
        resp = self._request(
            "GET",
            f"/v1/owners/{_quote(owner_id)}/timeline",
            headers=self._owner_headers(owner_id),
            params=params,
        )
        assert resp is not None
        return dict(resp.json())

    def get_why_fact(self, owner_id: str, fact_id: str) -> dict[str, Any]:
        resp = self._request(
            "GET",
            f"/v1/owners/{_quote(owner_id)}/why/{_quote(fact_id)}",
            headers=self._owner_headers(owner_id),
            params={"reinforce": False},
        )
        assert resp is not None
        return dict(resp.json())

    def resolve_fact(
        self,
        owner_id: str,
        fact_id: str,
        *,
        action: FactResolutionAction,
        new_text: str | None = None,
        valid_from: str | None = None,
        evidence_record_id: str | None = None,
    ) -> dict[str, Any]:
        resp = self._request(
            "POST",
            f"/v1/owners/{_quote(owner_id)}/facts/{_quote(fact_id)}/resolve",
            headers=self._owner_headers(owner_id),
            json_body={
                "action": action,
                "new_text": new_text,
                "valid_from": valid_from,
                "evidence_record_id": evidence_record_id,
            },
        )
        assert resp is not None
        return dict(resp.json())

    def set_memory_lowered(self, owner_id: str, *, lower: bool = True, **target: Any) -> dict[str, Any]:
        response = self._request(
            "POST", f"/v1/owners/{_quote(owner_id)}/{'lower' if lower else 'restore'}",
            headers=self._owner_headers(owner_id), json_body=target,
        )
        return dict(response.json())

    def lowered_record_ids(self, owner_id: str) -> set[str]:
        response = self._request(
            "GET", f"/v1/owners/{_quote(owner_id)}/lowered-records",
            headers=self._owner_headers(owner_id),
        )
        return set(response.json()["record_ids"])

    def delete_my_data(self, owner_id: str) -> dict[str, Any]:
        response = self._request(
            "POST", f"/v1/owners/{_quote(owner_id)}/delete-my-data",
            headers=self._admin_headers(),
        )
        return dict(response.json())

    def memory_version(self, owner_id: str) -> int:
        response = self._request(
            "GET", f"/v1/owners/{_quote(owner_id)}/memory-version",
            headers=self._owner_headers(owner_id),
        )
        return int(response.json()["facts_version"])

    def forget_source(self, owner_id: str, record_ids: list[str]) -> dict[str, Any]:
        return self.set_memory_lowered(owner_id, record_ids=record_ids) if record_ids else {"ok": True, "records": 0}

    def forget_fact(self, owner_id: str, fact_id: str) -> dict[str, Any]:
        return self.set_memory_lowered(owner_id, fact_id=fact_id)

    def export_markdown_zip(self, owner_id: str) -> bytes:
        resp = self._request(
            "GET",
            f"/v1/owners/{_quote(owner_id)}/export/md.zip",
            headers=self._owner_headers(owner_id),
        )
        assert resp is not None
        return bytes(resp.content)
