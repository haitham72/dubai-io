"""Streaming speech-to-text. The browser sends 24 kHz mono PCM16; text deltas come back while the person speaks.

OpenAITranscriber — Realtime API transcription session with gpt-realtime-whisper (schema checked against the
                    openai 3.26 SDK types): `turn_detection` must be null (no server VAD) and `prompt` is unsupported,
                    so the browser detects the end of speech and the buffer is committed here.
FakeTranscriber   — for tests and offline runs: no audio, no network; text arrives via `feed_text`.

Not verified without a live key: the connect URL (`?intent=transcription`, model in the session rather than the URL)
and whether deltas stream before the commit. If they do not, set AGENTS_STT_COMMIT_MS (e.g. 800) to commit short
segments while the person speaks; partials are then completed segments plus the current deltas.
"""
from __future__ import annotations

import asyncio
import base64
import os
from typing import AsyncIterator, Protocol

from .spend import Budget, Usage

BYTES_PER_SECOND = 24000 * 2  # 24 kHz, 16-bit mono


class Transcriber(Protocol):
    async def open(self) -> None: ...
    async def audio(self, pcm16: bytes) -> None: ...
    async def commit(self) -> None: ...
    def stream(self) -> AsyncIterator[tuple[str, str]]: ...  # ("partial", text so far) | ("final", text)
    async def close(self) -> None: ...


class FakeTranscriber:
    def __init__(self) -> None:
        self.q: asyncio.Queue[tuple[str, str]] = asyncio.Queue()
        self.text = ""

    async def open(self) -> None:
        return None

    async def audio(self, pcm16: bytes) -> None:
        return None  # audio is ignored offline: the demo uses typed text, the voice path falls back to batch

    async def feed_text(self, words: list[str], gap_s: float = 0.0) -> None:
        for i in range(len(words)):
            self.text = " ".join(words[: i + 1])
            await self.q.put(("partial", self.text))
            if gap_s:
                await asyncio.sleep(gap_s)

    async def commit(self) -> None:
        await self.q.put(("final", self.text))

    async def stream(self) -> AsyncIterator[tuple[str, str]]:
        while True:
            yield await self.q.get()

    async def close(self) -> None:
        return None


# Words the transcriber should expect: the app's own names. Contact names are added per session.
APP_WORDS = ("Mirsal", "Diwan", "Nadi", "UAE PASS", "Mirsal Updates", "AI Chat", "Dubai", "Abu Dhabi", "Sharjah",
             "chat", "message", "messages", "reply", "email", "calendar")
KEYWORD_MODELS = ("gpt-transcribe", "gpt-live-transcribe")      # take `keywords` + `languages`
PROMPT_MODELS = ("gpt-4o-transcribe", "gpt-4o-mini-transcribe")  # take a free-text `prompt`


def transcription_config(model: str, delay: str, keywords: list[str]) -> dict:
    """The realtime `transcription` block for `model`, sending only what that model supports (SDK types,
    openai/types/realtime/audio_transcription.py): `delay` only for gpt-realtime-whisper; vocabulary as `keywords`
    (gpt-transcribe, gpt-live-transcribe) or a `prompt` (gpt-4o-*-transcribe); never to gpt-realtime-whisper, which
    takes no hints. English + Arabic where the model accepts several languages."""
    words = list(dict.fromkeys([*APP_WORDS, *(k.strip() for k in keywords if k.strip())]))[:100]
    if model.startswith(KEYWORD_MODELS):
        return {"model": model, "languages": ["en", "ar"], "keywords": words}
    if model.startswith(PROMPT_MODELS):
        return {"model": model, "language": "en", "prompt": "Voice commands to a messaging app. Names and words: " + ", ".join(words)}
    if model == "gpt-realtime-whisper":
        return {"model": model, "language": "en", "delay": delay}
    return {"model": model, "language": "en"}


class OpenAITranscriber:
    def __init__(self, client, model: str, delay: str, budget: Budget, keywords: list[str] | None = None) -> None:
        self.client, self.model, self.delay, self.budget = client, model, delay, budget
        self.keywords = keywords or []
        self.conn = None
        self._manager = None
        self.bytes_unbilled = 0
        self.segments: list[str] = []
        self.current = ""
        self.commit_every = float(os.environ.get("AGENTS_STT_COMMIT_MS", "0") or 0) / 1000
        self._last_commit = 0.0
        self._bytes_since_commit = 0

    async def open(self) -> None:
        # One second of audio is the smallest unit we allow to start: refuse the session if even that is over budget.
        await self.budget.ensure(Usage(stt_seconds=1))
        self._manager = self.client.realtime.connect(extra_query={"intent": "transcription"})
        self.conn = await self._manager.__aenter__()
        await self.conn.send({
            "type": "session.update",
            "session": {
                "type": "transcription",
                "audio": {"input": {
                    "format": {"type": "audio/pcm", "rate": 24000},
                    "transcription": transcription_config(self.model, self.delay, self.keywords),
                    "turn_detection": None,
                }},
            },
        })

    async def audio(self, pcm16: bytes) -> None:
        await self.conn.send({"type": "input_audio_buffer.append", "audio": base64.b64encode(pcm16).decode()})
        self.bytes_unbilled += len(pcm16)
        self._bytes_since_commit += len(pcm16)
        if self.bytes_unbilled >= BYTES_PER_SECOND * 5:  # bill every 5 s of audio so the cap stops a long session
            await self._bill()
        if self.commit_every and self._bytes_since_commit >= BYTES_PER_SECOND * self.commit_every:
            await self.conn.send({"type": "input_audio_buffer.commit"})
            self._bytes_since_commit = 0

    async def _bill(self) -> None:
        seconds = self.bytes_unbilled / BYTES_PER_SECOND
        self.bytes_unbilled = 0
        await self.budget.charge(Usage(stt_seconds=seconds), "transcription")
        await self.budget.ensure(0.0)  # raises once the cap is reached

    async def commit(self) -> None:
        if self._bytes_since_commit:
            await self.conn.send({"type": "input_audio_buffer.commit"})
            self._bytes_since_commit = 0
        await self._bill()

    async def stream(self) -> AsyncIterator[tuple[str, str]]:
        async for ev in self.conn:
            kind = getattr(ev, "type", "")
            if kind == "conversation.item.input_audio_transcription.delta":
                self.current += ev.delta or ""
                yield "partial", " ".join(self.segments + [self.current]).strip()
            elif kind == "conversation.item.input_audio_transcription.completed":
                self.segments.append(ev.transcript.strip())
                self.current = ""
                yield ("partial" if self.commit_every else "final"), " ".join(self.segments).strip()
            elif kind == "error":
                raise RuntimeError(getattr(getattr(ev, "error", None), "message", "transcription error"))

    def reset(self) -> None:
        self.segments, self.current = [], ""

    async def close(self) -> None:
        if self._manager:
            await self._manager.__aexit__(None, None, None)
            self._manager = self.conn = None
