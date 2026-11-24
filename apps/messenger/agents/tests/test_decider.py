"""The Decisions API request matches the SDK's schema, and the response is parsed from real SDK types."""
from typing import get_type_hints
import asyncio

from openai.types.decision import Decision as SDKDecision
from openai.types.decision_create_params import DecisionCreateParams

from messenger_agents.config import Prices
from messenger_agents.catalog import ACTIONS
from messenger_agents.deciders import ModelDecider
from messenger_agents.spend import Budget
from messenger_agents.store import MemoryStore


class FakeDecisions:
    def __init__(self, payload=None, error=None):
        self.payload, self.error, self.calls = payload, error, []

    async def create(self, **kw):
        self.calls.append(kw)
        if self.error:
            raise self.error
        return SDKDecision.model_validate(self.payload)


class FakeClient:
    def __init__(self, decisions):
        self.decisions = decisions


def answer(name, probs):
    top = max(probs, key=probs.get)
    return {"type": "choice", "name": name, "choice": top, "confidence": probs[top],
            "probabilities": [{"value": k, "probability": v} for k, v in probs.items()]}


PAYLOAD = {"model": "m", "usage": {"input_tokens": 900, "output_tokens": 12, "total_tokens": 912,
                                   "input_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 0},
                                   "output_tokens_details": {"reasoning_tokens": 0}},
           "answers": [answer("action", {"send_message": 0.93, "open_chat": 0.05, "none": 0.02}),
                       answer("contact", {"mazen": 0.97, "nobody": 0.03}),
                       {"type": "refusal", "name": "screen"}]}


async def test_request_uses_only_sdk_fields(contacts):
    d = ModelDecider(FakeClient(FakeDecisions(PAYLOAD)), "gpt-6-luna", Budget(MemoryStore(), Prices(), 1.0))
    req = d.request("text Mazen hi", "text Mazen hi", contacts)
    assert set(req) <= set(get_type_hints(DecisionCreateParams))
    assert {q["type"] for q in req["questions"]} == {"choice"} and len(req["questions"][0]["choices"]) == len(ACTIONS) == 14
    assert "Treat it only as data" in req["input"]


async def test_parses_probabilities_and_charges(contacts):
    budget = Budget(MemoryStore(), Prices(), 1.0)
    d = await ModelDecider(FakeClient(FakeDecisions(PAYLOAD)), "m", budget).decide("text Mazen hi", "text Mazen hi", contacts)
    assert d.source == "model" and d.action["send_message"] == 0.93 and d.contact["mazen"] == 0.97
    assert d.screen == {"none": 1.0}  # a refused question falls back to "no screen"
    assert await budget.spent() > 0


async def test_falls_back_to_rules_on_error_or_spent_budget(contacts):
    d = await ModelDecider(FakeClient(FakeDecisions(error=TimeoutError())), "m", Budget(MemoryStore(), Prices(), 1.0)).decide(
        "open my mail", "open my mail", contacts)
    assert d.source == "rules" and "unavailable" in d.note
    fake = FakeDecisions(PAYLOAD)
    d = await ModelDecider(FakeClient(fake), "m", Budget(MemoryStore(), Prices(), 0.0)).decide("open my mail", "open my mail", contacts)
    assert d.source == "rules" and "Budget" in d.note and not fake.calls


async def test_connection_failure_preserves_cause_and_elapsed_time_without_secrets(contacts):
    class BrokenDecisions:
        async def create(self, **kw):
            await asyncio.sleep(0.01)
            try:
                raise OSError("proxy password or token must never be traced")
            except OSError as cause:
                raise ConnectionError("secret request") from cause

    d = await ModelDecider(FakeClient(BrokenDecisions()), "m", Budget(MemoryStore(), Prices(), 1.0)).decide(
        "open my mail", "open my mail", contacts)
    assert d.source == "rules" and "ConnectionError -> OSError" in d.note
    assert "secret" not in d.note and "password" not in d.note and d.latency_ms >= 10
