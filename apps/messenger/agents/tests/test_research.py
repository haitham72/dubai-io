from messenger_agents.research import DeepResearch, FakeLLM, FakeSearch
from messenger_agents.store import MemoryStore
from messenger_agents.trace import Tracer


class Skeptic(FakeLLM):
    """Marks the first claim unsupported and records what it was shown."""
    def __init__(self):
        self.prompts = []

    async def json(self, system, user, schema, name):
        self.prompts.append((name, system, user))
        out = await super().json(system, user, schema, name)
        if name == "verify":
            out["checks"][0]["supported"] = False
        return out


async def test_unsupported_claims_are_dropped_and_counted():
    llm, store = Skeptic(), MemoryStore()
    r = await DeepResearch(llm, FakeSearch(), store, Tracer(store), live=False).run("best new phones this week")
    assert r["stats"]["claims"] == 5 and r["stats"]["verified"] == 4 and len(r["findings"]) == 4
    assert "4/5 claims verified" in r["status"] and r["ranking"] and r["mode"] == "demo"


async def test_web_text_is_fenced_as_data_and_results_are_cached():
    llm, store = Skeptic(), MemoryStore()
    research = DeepResearch(llm, FakeSearch(), store, Tracer(store), live=False)
    await research.run("UAE EV market")
    brief_system, brief_user = next((s, u) for n, s, u in llm.prompts if n == "brief")
    assert "untrusted web content" in brief_system and '<source n="1"' in brief_user
    calls = len(llm.prompts)
    again = await research.run("uae ev market ")
    assert again["cached"] and len(llm.prompts) == calls


async def test_openai_llm_sends_photos_as_low_detail_image_parts_to_the_vision_model(tmp_path):
    from types import SimpleNamespace as NS

    from messenger_agents.config import Prices
    from messenger_agents.research import IMAGE_TOKENS, OpenAILLM
    from messenger_agents.spend import Budget

    sent = {}

    class Completions:
        async def create(self, **kw):
            sent.update(kw)
            return NS(usage=NS(prompt_tokens=10, completion_tokens=5), choices=[NS(message=NS(content='{"ok": true}'))])

    budget = Budget(MemoryStore(), Prices(), 1.0, tmp_path / "spend.json")
    llm = OpenAILLM(NS(chat=NS(completions=Completions())), "text-model", budget, vision_model="vision-model")
    assert await llm.json("sys", "look", {"type": "object"}, "t", ["https://x.test/a.jpg"]) == {"ok": True}
    parts = sent["messages"][1]["content"]
    assert sent["model"] == "vision-model" and parts[0] == {"type": "text", "text": "look"}
    assert parts[1] == {"type": "image_url", "image_url": {"url": "https://x.test/a.jpg", "detail": "low"}}
    await llm.json("sys", "plain", {"type": "object"}, "t")
    assert sent["model"] == "text-model" and sent["messages"][1]["content"] == "plain"
    assert IMAGE_TOKENS >= 1000  # photos are priced into the pre-call estimate

async def test_openai_llm_caps_output_tokens_so_vision_calls_do_not_400(tmp_path):
    from types import SimpleNamespace as NS

    from messenger_agents.config import Prices
    from messenger_agents.research import OpenAILLM
    from messenger_agents.spend import Budget

    sent = {}

    class Completions:
        async def create(self, **kw):
            sent.clear()
            sent.update(kw)
            return NS(usage=NS(prompt_tokens=10, completion_tokens=5), choices=[NS(message=NS(content='{}'))])

    budget = Budget(MemoryStore(), Prices(), 1.0, tmp_path / 'spend.json')
    luna = OpenAILLM(NS(chat=NS(completions=Completions())), 'gpt-6-luna', budget)
    await luna.json('sys', 'look', {'type': 'object'}, 't', ['https://x.test/a.jpg'])
    assert sent.get('max_completion_tokens', 0) >= 2000 and 'max_tokens' not in sent
    assert sent.get('reasoning_effort') == 'none'
    plain = OpenAILLM(NS(chat=NS(completions=Completions())), 'text-model', budget)
    await plain.json('sys', 'plain', {'type': 'object'}, 't')
    assert sent.get('max_tokens', 0) >= 2000 and 'max_completion_tokens' not in sent

