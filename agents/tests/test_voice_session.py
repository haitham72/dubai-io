"""Offline voice transport: late/standalone dictation holds independently of navigation acts."""
import asyncio

import pytest

from mirsal_agents.deciders import RuleDecider
from mirsal_agents.engine import Conversation
from mirsal_agents.session import VoiceSession
from mirsal_agents.stt import FakeTranscriber


class TraceCapture:
    def __init__(self):
        self.rows = []

    async def record(self, kind, **fields):
        self.rows.append({"kind": kind, **fields})


@pytest.mark.parametrize("open_first", [False, True])
async def test_dictation_hold_arrives_without_repeating_an_open_act(contacts, open_first):
    received, opened, listening, complete = [], asyncio.Event(), asyncio.Event(), asyncio.Event()
    prefix = "open my last chat and " if open_first else ""
    said = prefix + "reply to him saying Mazen is coming in January"

    async def send(message):
        received.append(message)
        if message.get("action") == "open_chat" and message["type"] == "act":
            opened.set()
        if message["type"] == "listening":
            listening.set()
        if message.get("text") == said:
            complete.set()

    trace = TraceCapture()
    session = VoiceSession(Conversation(RuleDecider(), contacts), FakeTranscriber(), trace, send, 3000)
    await session.start()
    try:
        if open_first:
            await session.text("open my last chat")
            await asyncio.wait_for(opened.wait(), 2)
            assert not listening.is_set()  # the earlier open carried no reply hint
        await session.text(prefix + "reply to him")
        await asyncio.wait_for(listening.wait(), 2)
        assert not any(m["type"] == "undo" for m in received)
        await session.text(said)
        await asyncio.wait_for(complete.wait(), 2)
        await session.end()
        sends = [m for m in received if m["type"] == "undo"]
        assert len(sends) == 1 and sends[0]["args"] == {
            "contactId": "arif", "name": "Arif Khan", "text": "Mazen is coming in January"}
        assert sum(m["type"] == "listening" for m in received) == 1
        assert sum(m["type"] == "act" and m.get("action") == "open_chat" for m in received) == 1
        assert trace.rows[-1]["dictationHold"] and trace.rows[-1]["clausePlan"]["raw"] == said
    finally:
        await session.close()


async def test_dictation_hold_does_not_wait_for_a_slow_classifier(contacts):
    entered, cancelled, listening, updated = [asyncio.Event() for _ in range(4)]
    received = []

    class SlowFirstDecision:
        calls = 0

        async def decide(self, clause, utterance, people):
            self.calls += 1
            if self.calls == 1:
                entered.set()
                try:
                    await asyncio.Event().wait()
                finally:
                    cancelled.set()
            assert cancelled.is_set()  # final classification starts only after cancellation
            return await RuleDecider().decide(clause, utterance, people)

    body = "I will see you tomorrow and bring chips and drinks too " + " ".join(["please remember the meeting details"] * 20)
    said = "reply to Arif Khan saying " + body

    async def send(message):
        received.append(message)
        if message["type"] == "listening":
            listening.set()
        if message.get("text") == said:
            updated.set()

    session = VoiceSession(Conversation(SlowFirstDecision(), contacts), FakeTranscriber(), TraceCapture(), send, 3000)
    await session.start()
    try:
        await session.text("open my chat with Arif Khan")
        await asyncio.wait_for(entered.wait(), 2)
        await session.text(said)
        await asyncio.wait_for(listening.wait(), 1)
        assert not cancelled.is_set() and not any(m["type"] == "undo" for m in received)
        await asyncio.wait_for(updated.wait(), 2)
        await session.end()
        sends = [m for m in received if m["type"] == "undo"]
        assert len(sends) == 1 and sends[0]["args"]["text"] == body
        assert sends[0]["args"]["contactId"] == "arif" and cancelled.is_set()
        assert not any(m["type"] == "act" for m in received)
    finally:
        await session.close()
