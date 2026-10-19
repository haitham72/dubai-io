"""Research tools: answers only from retrieved sources, fixed-template quotes, civic questions refused."""
from types import SimpleNamespace

from app.luna import research

HITS = [{"title": "Mall hours", "url": "https://example.com/hours", "snippet": "Open 10:00 to 24:00", "via": "Tavily"},
        {"title": "Other", "url": "https://example.com/other", "snippet": "Unrelated", "via": "Tavily"}]


def fake_client(text):
    return SimpleNamespace(responses=SimpleNamespace(create=lambda **kw: SimpleNamespace(output_text=text)))


def test_civic_questions_get_a_portal_pointer_not_an_answer(monkeypatch):
    monkeypatch.setattr(research, "web_search", lambda q: (_ for _ in ()).throw(AssertionError("must not search")))
    out = research.research({"intent": "info_question", "query": "salik fine amount"}, "how much is a salik fine", fake_client("x"))
    assert out["tool"] == "civic_guard" and out["sources"] == []


def test_answer_keeps_only_cited_sources(monkeypatch):
    monkeypatch.setattr(research, "web_search", lambda q: HITS)
    out = research.research({"intent": "info_question", "query": "mall hours"}, "when does the mall open", fake_client("It opens at 10:00 [1]. See https://evil.example"))
    assert "https://" not in out["answer"]
    assert [s["url"] for s in out["sources"]] == ["https://example.com/hours"]


def test_uncited_or_out_of_range_answers_fall_back_to_sources(monkeypatch):
    monkeypatch.setattr(research, "web_search", lambda q: HITS)
    for text in ("It opens at 10:00.", "It opens at 10:00 [9]."):
        out = research.research({"intent": "info_question", "query": "q"}, "q", fake_client(text))
        assert out["answer"].startswith("I found sources but couldn't")


def test_no_results_says_so(monkeypatch):
    monkeypatch.setattr(research, "web_search", lambda q: [])
    out = research.research({"intent": "info_question", "query": "q"}, "q", fake_client("x"))
    assert out["sources"] == [] and "couldn't find" in out["answer"]


def test_quote_is_a_template_from_provider_data(monkeypatch):
    monkeypatch.setattr(research, "finnhub_quote", lambda s: {"symbol": s, "price": 101.5, "change_pct": -1.25, "as_of": "2026-10-16T20:00+00:00"})
    out = research.research({"intent": "market_quote", "symbol": "aapl"}, "apple price", fake_client("never used"))
    assert out["answer"].startswith("AAPL last traded at 101.5, -1.25% today") and out["sources"][0]["via"] == "Finnhub"


def test_bad_symbols_never_reach_the_provider():
    assert research.finnhub_quote("AAPL; DROP TABLE") is None
