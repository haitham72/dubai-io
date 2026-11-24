"""Routes: Streaming voice commands over WebSocket."""
from __future__ import annotations

from fastapi import FastAPI

import contextlib
import json

from fastapi import Request, WebSocket, WebSocketDisconnect

from ..contacts import Contact
from ..deciders import FastPathDecider, ModelDecider
from ..session import VoiceSession
from ..spend import BudgetExceeded
from ..stt import FakeTranscriber
def register(app: FastAPI, S, user) -> None:
    @app.websocket("/agents/voice")
    async def voice(ws: WebSocket):
        await ws.accept()
        s = S(ws)
        sid = (ws.query_params.get("sid") or "anon")[:60]

        async def send(msg: dict) -> None:
            with contextlib.suppress(Exception):
                await ws.send_text(json.dumps(msg, ensure_ascii=False))

        session: VoiceSession | None = None
        try:
            start = json.loads(await ws.receive_text())
            contacts = [Contact(str(c["id"]), str(c["name"])) for c in start.get("contacts", [])][:500]
            stt = s.transcriber([c.name for c in contacts]) if start.get("audio", True) else FakeTranscriber()
            session = VoiceSession(s.conversations.get(sid, contacts), stt, s.tracer, send, s.cfg.undo_ms)
            await session.start()
            await send({"type": "ready", "stt": "fake" if isinstance(stt, FakeTranscriber) else "live",
                        "decider": "model" if isinstance(s.decider, (ModelDecider, FastPathDecider)) else "rules"})
            while True:
                msg = await ws.receive()
                if msg.get("type") == "websocket.disconnect":
                    break
                if msg.get("bytes"):
                    await session.audio(msg["bytes"])
                    continue
                data = json.loads(msg.get("text") or "{}")
                if data.get("type") == "text":
                    await session.text(str(data.get("text", ""))[:500])
                elif data.get("type") == "end":
                    events = await session.end()
                    for e in events:
                        if e.type == "chat":
                            await s.memory.log_turn(sid, "user", e.label)
                elif data.get("type") == "outcome":
                    await session.outcome(data)
                elif data.get("type") == "close":
                    break
        except BudgetExceeded as err:
            await send({"type": "error", "message": str(err), "budget": True})
        except WebSocketDisconnect:
            pass
        finally:
            if session:
                await session.close()
            with contextlib.suppress(Exception):
                await ws.close()
