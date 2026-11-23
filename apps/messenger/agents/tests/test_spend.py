import pytest

from mirsal_agents.config import Prices
from mirsal_agents.spend import Budget, BudgetExceeded, Usage
from mirsal_agents.store import MemoryStore


async def test_cap_refuses_the_call_that_would_cross_it(tmp_path):
    b = Budget(MemoryStore(), Prices(), cap_usd=0.01, ledger=tmp_path / "spend.json")
    await b.charge(Usage(stt_seconds=30), "stt")  # 0.5 min * $0.017
    assert round(await b.spent(), 4) == 0.0085
    with pytest.raises(BudgetExceeded):
        await b.ensure(Usage(stt_seconds=30))
    assert (await b.status())["stopped"] is False


async def test_ledger_survives_a_restart_without_redis(tmp_path):
    ledger = tmp_path / "spend.json"
    await Budget(MemoryStore(), Prices(), 1.0, ledger).charge(0.25, "x")
    assert await Budget(MemoryStore(), Prices(), 1.0, ledger).spent() == 0.25


def test_prices_match_the_approved_poc_rates():
    p = Prices()
    assert p.stt_per_minute == 0.017 and p.decision_in_per_m == 0.10
    assert round(Usage(decision_in=1_000_000).cost(p), 2) == 0.10
