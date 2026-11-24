"""Both stores behave the same. The Redis case runs when a local Redis answers (docker compose up redis)."""
import pytest

from messenger_agents.store import MemoryStore, RedisStore, connect


@pytest.fixture(params=["memory", "redis"])
async def store(request):
    if request.param == "memory":
        yield MemoryStore()
        return
    s = await connect("redis://localhost:6379/15")
    if not isinstance(s, RedisStore):
        pytest.skip("no local Redis")
    yield s
    await s._r.flushdb()
    await s.close()


async def test_store_contract(store):
    await store.set("k", {"a": [1, 2]})
    assert await store.get("k") == {"a": [1, 2]} and await store.get("missing") is None
    for i in range(5):
        await store.push("list", {"i": i}, keep=3)
    assert [x["i"] for x in await store.recent("list")] == [4, 3, 2]
    assert await store.add_float("n", 0.25) == 0.25 and await store.add_float("n", 0.5) == 0.75
    await store.delete("k")
    assert await store.get("k") is None
