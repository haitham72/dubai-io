"""The eval harness and the retrieval building blocks (fake models, no LM Studio)."""
import hashlib
import re
from pathlib import Path

import pytest

from app.lab import circle as circle_mod
from app.lab import evaluate, index, llm, rows, scoring, searchlib
from app.lab.parse import parse_chat
from app.lab.store import Lab

FIX = Path(__file__).parent / "fixtures" / "lab"
NOW = "2026-11-16T00:00:00+00:00"
CIRCLE = circle_mod.Circle(owner="Sam", people={"ios_sample": {"name": "Lina", "relation": "colleague", "nicknames": ["Linaa"]}})


def vec(text):
    v = [0.0] * 48
    for w in searchlib.tokens(text):
        v[int(hashlib.md5(w.encode()).hexdigest(), 16) % 48] += 1.0
    return v


class NoScorer:
    available = False
    reason = "test"

    def score(self, texts):
        return [None] * len(texts)

    def info(self):
        return {"status": "unavailable", "reason": "test"}


def model(system, user, schema, **kw):
    if "privacy screen" in system:
        return {"items": [{"n": int(n), "category": "none"} for n in re.findall(r"^(\d+)\. ", user, re.M)]}
    items = []
    for n, body in zip(*[iter(re.split(r"^ROW (\d+)$", user, flags=re.M)[1:])] * 2):
        orbit = "Orbit" in body
        items.append({"row": int(n), "topics": ["video editing"] if orbit else ["small talk"], "names": ["Lina", "Zed"],
                      "user": "Sam talked.", "memory": "Sam and Lina discuss the Orbit promo draft." if orbit else "They chat about the gym.",
                      "followups": ["Which cut is due?"] if orbit else [], "sensitive": False})
    return {"items": items}


@pytest.fixture
def lab(tmp_path, monkeypatch):
    scoring.set_scorer(NoScorer())
    lab = Lab(tmp_path, "lab-test")
    lab.ingest_messages("whatsapp", "ios_sample", parse_chat((FIX / "chat_ios_sample.txt").read_text(encoding="utf-8"), "ios_sample").messages, NOW)
    monkeypatch.setattr(llm, "loaded_context", lambda model=None: 13891)
    monkeypatch.setattr(llm, "embed", lambda texts, kind="document": [vec(t) for t in texts])
    monkeypatch.setattr(llm, "chat_json", model)
    rows.process(lab, "ios_sample", "Sam", CIRCLE)
    yield lab
    scoring.set_scorer(None)


def test_bm25_rrf_and_language_detection():
    docs = {"a": "Lina sends the Orbit draft", "b": "gym on Thursday", "c": "Orbit logo files"}
    assert searchlib.bm25_rank(docs, "orbit draft")[0] == "a" and searchlib.bm25_rank(docs, "zzz") == []
    assert searchlib.rrf([["a", "b"], ["b", "c"]])[0] == "b"  # the item both lists like wins
    assert searchlib.is_foreign("ليه ماترميه") and not searchlib.is_foreign("why not throw it away")


def test_translate_only_foreign_queries_and_never_fails(monkeypatch):
    calls = []

    def fake(system, user, schema, **kw):
        calls.append(user)
        return {"english": "why keep the old phone"}

    monkeypatch.setattr(llm, "chat_json", fake)
    searchlib._translations.clear()
    assert searchlib.translate("english stays") == "english stays" and calls == []
    assert searchlib.translate("ليه محتفظة بالتليفون") == "why keep the old phone"
    searchlib.translate("ليه محتفظة بالتليفون")
    assert len(calls) == 1  # cached

    def down(*a, **k):
        raise llm.LabLLMError("down")

    monkeypatch.setattr(llm, "chat_json", down)
    searchlib._translations.clear()
    assert searchlib.translate("سؤال") == "سؤال"  # falls back to the original query


def test_search_hybrid_finds_the_row_and_falls_back_to_lexical(lab, monkeypatch):
    index.build_windows(lab)
    hits = index.search(lab, "Orbit promo draft", k=3)
    assert hits and hits[0]["via"] == "hybrid" and "Orbit" in hits[0]["text"] and hits[0]["evidence"][0] <= hits[0]["evidence"][1]

    def down(texts, kind="document"):
        raise llm.LabLLMError("no embeddings")

    monkeypatch.setattr(llm, "embed", down)
    lexical = index.search(lab, "gym", k=3)
    assert lexical and lexical[0]["via"] == "lexical" and "gym" in lexical[0]["text"]


def test_search_date_filter_and_timeline_hide_nothing_they_should_not(lab):
    index.build_windows(lab)
    first_day = index.timeline(lab)[0]["when"][:10]
    assert all(h["when"] == first_day for h in index.search(lab, "chat", k=20, since=first_day, until=first_day))
    assert all(t["when"].startswith(first_day) for t in index.timeline(lab, since=first_day, until=first_day))
    assert index.timeline(lab, since="2030-01-01") == []


def test_open_loops_are_the_open_followups(lab):
    loops = index.open_loops(lab)
    assert loops and len(loops) == len([f for f in lab.followups("open")])
    assert all(l["row_id"] and l["evidence"] for l in loops if "row_id" in l)


def test_structural_metrics_flag_invented_names(lab):
    s = evaluate.structural(lab, CIRCLE)
    assert s["usable"] == s["rows"] > 0 and s["withheld_rate"] == 0
    assert s["rows_with_ungrounded_name"] == s["rows"]  # "Zed" is in no message and not in the circle
    assert 0 < s["names_ungrounded_rate"] < 1 and s["memory_english_rate"] == 1.0 and s["scored_rate"] == 0


def test_query_checks_all_pass_on_a_healthy_database(lab):
    index.build_windows(lab)
    res = evaluate.query_checks(lab)
    failed = [c for c in res["checks"] if not c["ok"]]
    assert not failed, failed


def test_search_eval_scores_variants(lab):
    index.build_windows(lab)
    target = next(r for r in lab.rows() if "Orbit" in r["memory"])
    queries = [{"id": target["id"], "en": "Orbit promo draft", "ar": "مسودة اوربت", "kw": "orbit draft"}]
    report = evaluate.search_eval(lab, queries, evaluate.VARIANTS[:4])
    assert report["queries"] == 1 and report["corpus_rows"] == len(lab.rows())
    assert report["variants"]["S3 hybrid dense+BM25"]["en"]["r@5"] == 1.0
    assert set(report["variants"]["S0 dense, memory+topics (what was built)"]) == {"en", "ar", "kw"}


def test_answer_in_reasoning_content_is_still_read(monkeypatch):
    """LM Studio sometimes returns the JSON in reasoning_content with an empty content field."""
    def fake_http(path, payload=None, timeout=600):
        return {"choices": [{"message": {"content": "", "reasoning_content": '{"ok": true}'}, "finish_reason": "stop"}], "usage": {}}

    monkeypatch.setattr(llm, "_http", fake_http)
    assert llm.chat_json("s", "u", {"type": "object"}) == {"ok": True}
    monkeypatch.setattr(llm, "_http", lambda *a, **k: {"choices": [{"message": {"content": '{"a": 1}', "reasoning_content": "ignored"},
                                                                    "finish_reason": "stop"}], "usage": {}})
    assert llm.chat_json("s", "u", {"type": "object"}) == {"a": 1}  # content wins when present
