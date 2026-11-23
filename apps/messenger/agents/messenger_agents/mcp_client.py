"""A minimal MCP client (Streamable HTTP transport, JSON-RPC 2.0) for calling one tool on a remote MCP server.

Messenger talks to two separate backends this way: Diwan (UAE events) and, later, Messenger Builder (sticker packs). Their
logic lives in their own MCP servers; this service only calls a tool and validates what comes back.

Handshake: `initialize` → `notifications/initialized` → `tools/call`. Responses may be plain JSON or an SSE stream
(`text/event-stream`, one `data:` line per JSON-RPC message); both are handled. The `Mcp-Session-Id` header is kept.
"""
from __future__ import annotations

import json
from typing import Any

import httpx2 as httpx  # ships with the openai SDK

PROTOCOL = "2025-06-18"


class McpError(RuntimeError):
    pass


class McpClient:
    def __init__(self, url: str, token: str = "", http: httpx.AsyncClient | None = None, timeout: float = 10.0) -> None:
        self.url, self.token = url, token
        self.http = http or httpx.AsyncClient(timeout=timeout)
        self.session: str | None = None
        self._id = 0

    def _headers(self) -> dict[str, str]:
        h = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream", "MCP-Protocol-Version": PROTOCOL}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        if self.session:
            h["Mcp-Session-Id"] = self.session
        return h

    async def _rpc(self, method: str, params: dict | None = None, notify: bool = False) -> Any:
        body: dict[str, Any] = {"jsonrpc": "2.0", "method": method, **({"params": params} if params is not None else {})}
        if not notify:
            self._id += 1
            body["id"] = self._id
        res = await self.http.post(self.url, json=body, headers=self._headers())
        if sid := res.headers.get("mcp-session-id"):
            self.session = sid
        if notify:
            return None
        res.raise_for_status()
        for msg in _messages(res.headers.get("content-type", ""), res.text):
            if msg.get("id") == body["id"]:
                if "error" in msg:
                    raise McpError(str(msg["error"].get("message", msg["error"])))
                return msg.get("result")
        raise McpError(f"No response to {method}")

    async def call(self, tool: str, arguments: dict) -> Any:
        """Call `tool` and return its structured result (structuredContent, else the first text block parsed as JSON)."""
        if self.session is None:
            await self._rpc("initialize", {"protocolVersion": PROTOCOL, "capabilities": {},
                                           "clientInfo": {"name": "messenger-agents", "version": "0.1"}})
            await self._rpc("notifications/initialized", notify=True)
        result = await self._rpc("tools/call", {"name": tool, "arguments": arguments}) or {}
        if result.get("isError"):
            raise McpError(_text(result) or f"{tool} failed")
        if "structuredContent" in result:
            return result["structuredContent"]
        text = _text(result)
        try:
            return json.loads(text)
        except (TypeError, ValueError) as err:
            raise McpError(f"{tool} returned no JSON") from err


def _text(result: dict) -> str:
    return next((c.get("text", "") for c in result.get("content", []) if c.get("type") == "text"), "")


def _messages(content_type: str, text: str) -> list[dict]:
    if "text/event-stream" in content_type:
        out = []
        for line in text.splitlines():
            if line.startswith("data:"):
                try:
                    out.append(json.loads(line[5:].strip()))
                except ValueError:
                    continue
        return out
    data = json.loads(text) if text.strip() else {}
    return data if isinstance(data, list) else [data]
