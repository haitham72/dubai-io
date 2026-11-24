"""One voice WebSocket: audio (or typed text) in, transcript partials and action events out.

Client → server   {"type":"start","contacts":[{id,name}]} · binary PCM16 24 kHz mono · {"type":"text","text":…}
                  · {"type":"end"} · {"type":"outcome","id":…,"outcome":"done|undone|confirmed|declined"}
Server → client   {"type":"ready","stt":"live|fake"} · {"type":"partial","text"} · {"type":"final","text"}
                  · {"type":"listening","awaiting":"reply"} · engine events (act | undo | confirm | ask | cancel | chat)
                  · {"type":"done"} · {"type":"error"}
"""
from __future__ import annotations

import asyncio
import contextlib
import time
from typing import Awaitable, Callable

from .contacts import Contact
from .engine import Conversation, Event, Policy
from .spend import BudgetExceeded
from .stt import FakeTranscriber, Transcriber
from .trace import Tracer
from .text import REPLY, send_parts, split_clauses

Send = Callable[[dict], Awaitable[None]]


class VoiceSession:
    TICK_S = 0.1

    def __init__(self, conversation: Conversation, stt: Transcriber, tracer: Tracer, send: Send, undo_ms: int) -> None:
        self.conv, self.stt, self.tracer, self.send, self.undo_ms = conversation, stt, tracer, send, undo_ms
        self.t0 = time.monotonic()
        self.speech_end: float | None = None
        self.last_partial_at = 0.0
        self.final_text: str | None = None
        self.events: list[Event] = []
        self.dictation_hold = False
        self.reply_opened = False
        self._tasks: list[asyncio.Task] = []
        self.engine = conversation.begin()

    def now(self) -> float:
        return time.monotonic() - self.t0

    async def start(self) -> None:
        await self.stt.open()
        self._tasks = [asyncio.create_task(self._read_stt()), asyncio.create_task(self._tick())]

    async def _emit(self, events: list[Event]) -> None:
        for e in events:
            self.events.append(e)
            await self.send({**e.wire(), "undoMs": self.undo_ms} if e.type == "undo" else e.wire())

    async def _read_stt(self) -> None:
        try:
            async for kind, text in self.stt.stream():
                self.last_partial_at = self.now()
                self.engine.partial(text, self.now())
                self.final_text = text if kind == "final" else None
                await self.send({"type": kind, "text": text})
                await self._hold_dictation()
        except BudgetExceeded as err:
            await self.send({"type": "error", "message": str(err), "budget": True})
        except Exception as err:  # noqa: BLE001 — report and let the browser fall back to batch voice
            await self.send({"type": "error", "message": f"transcription failed ({type(err).__name__})"})

    async def _tick(self) -> None:
        while self.speech_end is None:
            await self._hold_dictation()
            await self._emit(await self.conv.tick(self.now()))
            # Listening is a transport status, separate from an act: the chat may have opened before "reply"
            # arrived, or this may be a standalone send. Once dictation starts, hold until this turn ends.
            await self._hold_dictation()
            await asyncio.sleep(self.TICK_S)

    async def _hold_dictation(self) -> None:
        pending = self.conv.pending
        dictating_answer = pending and pending.action == "send_message" and pending.contact is not None
        if not self.dictation_hold and (dictating_answer or any(send_parts(p) for p in split_clauses(self.engine.text))):
            self.dictation_hold = True
            await self.send({"type": "listening", "awaiting": "reply"})
        parts = split_clauses(self.engine.text)
        first = send_parts(parts[0]) if parts else None
        if not self.reply_opened and not self.conv.pending and first and REPLY.match(parts[0]) \
                and first.recipient.lower() in ("him", "her", "them") and self.conv.contacts:
            # A standalone pronoun reply follows the browser's last interaction. This
            # navigation is reversible; only the completed message gets an undo/send.
            contact = self.conv.contacts[0]
            self.engine.last_contact = contact
            self.reply_opened = True
            event = Event("act", self.now(), action="open_chat", args={"contactId": contact.id, "name": contact.name},
                          label=f"Opening your chat with {contact.name}", clause=parts[0], source="context", awaiting="reply")
            self.engine.events.append(event)
            await self._emit([event])

    async def text(self, text: str) -> None:
        """Typed or test input: streams the words through the same path as speech."""
        if isinstance(self.stt, FakeTranscriber):
            await self.stt.feed_text(text.split())

    async def audio(self, chunk: bytes) -> None:
        await self.stt.audio(chunk)

    async def end(self) -> list[Event]:
        """End of speech (detected by the browser). Commit, wait briefly for the final words, then decide."""
        await self.stt.commit()
        deadline = self.now() + 1.5
        while self.final_text is None and self.now() < deadline:
            if isinstance(self.stt, FakeTranscriber) and self.engine.text == self.stt.text and self.now() - self.last_partial_at > 0.05:
                break
            await asyncio.sleep(0.02)
        self.speech_end = self.now()
        if self.final_text:
            self.engine.partial(self.final_text, self.speech_end)
        # Freeze the final snapshot and await cancellation before final classification,
        # so an in-flight early decision cannot race the end-of-speech decision.
        for t in self._tasks:
            t.cancel()
        for t in self._tasks:
            with contextlib.suppress(asyncio.CancelledError):
                await t
        events = await self.conv.finish(self.now())
        await self._emit(events)
        await self.tracer.record(
            "voice", utterance=self.engine.text, events=[e.wire() for e in self.events], decisions=self.engine.decisions,
            speechEndS=round(self.speech_end, 3), clausePlan=self.engine.plan, dictationHold=self.dictation_hold,
        )
        await self.send({"type": "done"})
        return self.events

    async def outcome(self, msg: dict) -> None:
        await self.tracer.record("outcome", id=msg.get("id"), outcome=msg.get("outcome"))

    async def close(self) -> None:
        for t in self._tasks:
            t.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await t
        await self.stt.close()


class Conversations:
    """Per-browser conversations (so an answer to "Sara Ali or Sarah Malik?" can come in a new utterance)."""

    def __init__(self, decider, policy: Policy, keep: int = 200) -> None:
        self.decider, self.policy, self.keep = decider, policy, keep
        self._by_sid: dict[str, tuple[Conversation, float]] = {}

    def get(self, sid: str, contacts: list[Contact]) -> Conversation:
        conv = self._by_sid.get(sid, (None, 0))[0]
        if conv is None or [c.id for c in conv.contacts] != [c.id for c in contacts]:
            # The chat list reorders whenever a message arrives — often between a question and its answer.
            # A rebuild must keep everything the answer may need, or the next turn starts deaf.
            saved = (conv.pending, conv.carry, conv.carry_at,
                     conv.last_contact, conv.last_contact_at, conv.last_message, conv.last_message_contact) if conv else (None, "", 0.0, None, 0.0, "", "")
            conv = Conversation(self.decider, contacts, self.policy)
            conv.pending, conv.carry, conv.carry_at, conv.last_contact, conv.last_contact_at, conv.last_message, conv.last_message_contact = saved
        self._by_sid[sid] = (conv, time.time())
        if len(self._by_sid) > self.keep:
            oldest = min(self._by_sid, key=lambda k: self._by_sid[k][1])
            self._by_sid.pop(oldest, None)
        return conv
