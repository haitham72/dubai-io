"""v2 memory rows: segmentation, circle-aware names, fail-closed rows, packing, follow-up agent."""
import re
from datetime import datetime
from pathlib import Path

import pytest

from app.lab import circle as circle_mod
from app.lab import extract, followups, llm, rows, scoring
from app.lab.parse import parse_chat
from app.lab.store import Lab

FIX = Path(__file__).parent / "fixtures" / "lab"
NOW = "2026-11-16T00:00:00+00:00"
CIRCLE = circle_mod.Circle(
    owner="Sam", profile_summary="Sam writes in English.",
    people={"ios_sample": {"name": "Lina", "relation": "colleague", "nicknames": ["Linaa"], "summary": "client contact"}},
)


class FakeScorer:
    """Stands in for the two classifiers: 'angry' texts score negative + anger, everything else mildly positive."""
    available = True

    def __init__(self):
        self.calls = []

    def score(self, texts):
        self.calls.append(list(texts))
        return [{"polarity": {}, "sentiment": -0.6 if "angry" in t else 0.4,
                 "emotions": {"anger": 0.8} if "angry" in t else {"joy": 0.5}} for t in texts]

    def info(self):
        return {"status": "ok", "sentiment_model": "fake-sentiment", "emotion_model": "fake-emotion"}


@pytest.fixture(autouse=True)
def fake_scorer():
    scorer = FakeScorer()
    scoring.set_scorer(scorer)
    yield scorer
    scoring.set_scorer(None)


@pytest.fixture
def lab(tmp_path, monkeypatch):
    lab = Lab(tmp_path, "lab-test")
    parsed = parse_chat((FIX / "chat_ios_sample.txt").read_text(encoding="utf-8"), "ios_sample")
    lab.ingest_messages("whatsapp", "ios_sample", parsed.messages, NOW)
    monkeypatch.setattr(llm, "loaded_context", lambda model=None: 13891)
    monkeypatch.setattr(llm, "embed", lambda texts, kind="document": [[1.0, 0.0] for _ in texts])
    return lab


def model(*, sensitive_rows=(), skip_rows=(), followup_for_orbit=True, answer=None):
    """Fake local model for every prompt the row design uses."""

    def fn(system, user, schema, **kw):
        if "privacy screen" in system:
            lines = re.findall(r"^(\d+)\. (.+)$", user, re.M)
            return {"items": [{"n": int(n), "category": "health" if "BAD" in t else "none"} for n, t in lines]}
        if "follow-up question" in system:
            return answer or {"status": "unknown", "answer": "", "evidence": []}
        blocks = re.split(r"^ROW (\d+)$", user, flags=re.M)[1:]
        items = []
        for n, body in zip(blocks[0::2], blocks[1::2]):
            n = int(n)
            if n in skip_rows:
                continue
            orbit = "Orbit" in body
            items.append({
                "row": n, "topics": ["video editing"] if orbit else ["small talk"], "names": ["Linaaa", "Sam"],
                "user": "Sam talked about the Orbit promo." if orbit else "Sam chatted.",
                "memory": "Sam and Lina work on the Orbit promo." if orbit else "They chat.",
                "emotions": [{"label": "calm", "score": 0.4}], "sentiment": 0.3,
                "salience": [{"topic": "video editing" if orbit else "small talk", "score": 0.8}],
                "followups": ["Which cut is due?"] if (orbit and followup_for_orbit) else [],
                "sensitive": n in sensitive_rows,
            })
        return {"items": items}

    return fn


def msgs(lab):
    return lab.load_messages("whatsapp", "ios_sample")


def test_segment_covers_every_text_message_once_in_5_to_10_rows():
    parsed = parse_chat((FIX / "chat_ios_sample.txt").read_text(encoding="utf-8"), "x")
    segs = rows.segment(parsed.messages)
    text_ids = [m.idx for s in segs for m in s if m.kind == "message"]
    assert text_ids == [m.idx for m in parsed.messages if m.kind == "message"]
    assert all(sum(m.kind == "message" for m in s) <= rows.ROW_MAX for s in segs)
    # a 2-day silence always closes a row
    for a, b in zip(segs, segs[1:]):
        assert a[-1].idx < b[0].idx


def test_long_run_without_silence_is_split_in_balanced_pieces_under_the_cap():
    raw = "\n".join(f"[01/01/2026, 10:{i:02d}:00] A: m{i}" for i in range(25))
    segs = rows.segment(parse_chat(raw, "x").messages)
    sizes = [sum(m.kind == "message" for m in s) for s in segs]
    assert sum(sizes) == 25 and max(sizes) <= 10 and min(sizes) >= 8  # 8, 9, 8 - not 10, 10, 5


def test_average_time_is_the_mean():
    raw = "[01/01/2026, 10:00:00] A: a\n[01/01/2026, 10:10:00] B: b\n[01/01/2026, 10:20:00] A: c"
    assert rows.avg_time(parse_chat(raw, "x").messages) == "2026-01-01T10:10:00"


def test_names_are_corrected_to_circle_spelling_and_suggested():
    names, sugg, members = circle_mod.normalize_names(["Linaaa", "Sam", "Zed"], "ios_sample", CIRCLE)
    assert names == ["Linaa", "Sam", "Zed"] and sugg == [("Linaaa", "Linaa")] and members == ["Lina", "Sam"]
    arabic = circle_mod.Circle(owner="هيثم", people={"m": {"name": "mamty", "nicknames": ["مامتي", "قطتي"]}})
    names, sugg, _ = circle_mod.normalize_names(["مامتب", "قطتي"], "m", arabic)
    assert names == ["مامتي", "قطتي"] and sugg == [("مامتب", "مامتي")]  # the founder's own example


def test_rows_stored_with_code_owned_fields(lab, monkeypatch):
    monkeypatch.setattr(llm, "chat_json", model())
    stats = rows.process(lab, "ios_sample", "Sam", CIRCLE)
    stored = lab.rows()
    assert stats["rows_stored"] == len(stored) >= 2 and "rows_missing_from_model" not in stats
    first = stored[0]
    assert first["names"] == ["Linaa", "Sam"] and first["t_avg"] >= first["t_start"] and first["t_avg"] <= first["t_end"]
    assert any(r["multimodal"] == ["1x media omitted (content not available)"] for r in stored)  # placeholder only, never described
    assert lab.alias_suggestions()[0]["alias"] == "Linaaa"
    assert {a["facet"] for a in lab.annotations()} == {"topic", "person"}
    assert len(lab.windows()) == len(stored)  # projection keeps index / tree / search working
    assert all(r["recurring"] is None for r in stored)
    line = rows.format_row(stored[0])
    assert re.match(r"^\d{1,2}:\d{2}(am|pm)_\d{2}-\d{2}-2026: ", line) and "| Linaa, Sam |" in line


def test_sensitive_row_keeps_no_memory_user_text_or_followups(lab, monkeypatch):
    monkeypatch.setattr(llm, "chat_json", model(sensitive_rows={1}))
    rows.process(lab, "ios_sample", "Sam", CIRCLE)
    r = lab.rows()[0]
    assert r["sensitive"] == 1 and r["memory"] == "" and r["user_text"] == "" and r["sentiment"] is None
    assert not [f for f in lab.followups() if f["row_id"] == r["id"]]
    assert lab.windows()[0]["summary"].startswith("[summary withheld")


def test_regex_hit_in_model_text_also_fails_closed(lab, monkeypatch):
    base = model()

    def leaky(system, user, schema, **kw):
        out = base(system, user, schema, **kw)
        for it in out.get("items", []):
            it["memory"] = "Sam talks about his doctor appointment."
        return out

    monkeypatch.setattr(llm, "chat_json", leaky)
    rows.process(lab, "ios_sample", "Sam", CIRCLE)
    assert all(r["memory"] == "" and r["sensitive"] == 1 for r in lab.rows())


def test_overflow_splits_packs_and_missing_rows_are_retried(lab, monkeypatch):
    inner = model()

    def flaky(system, user, schema, **kw):
        if len(re.findall(r"^ROW \d+$", user, re.M)) > 2:
            raise llm.ContextOverflow("too long")
        return inner(system, user, schema, **kw)

    monkeypatch.setattr(llm, "chat_json", flaky)
    stats = rows.process(lab, "ios_sample", "Sam", CIRCLE)
    assert stats["rows_stored"] == len(rows.segment(msgs(lab)))
    monkeypatch.setattr(llm, "chat_json", model(skip_rows={1}))
    lab2 = Lab(lab.dir.parent / "second", "lab-test")
    lab2.ingest_messages("whatsapp", "ios_sample", msgs(lab), NOW)
    s2 = rows.process(lab2, "ios_sample", "Sam", CIRCLE)
    assert s2["rows_missing_from_model"] >= 1
    monkeypatch.setattr(llm, "chat_json", model())
    s3 = rows.process(lab2, "ios_sample", "Sam", CIRCLE)
    assert s3["rows_stored"] == s2["rows_missing_from_model"]  # only the missed rows ran again


def test_pack_respects_budget_and_row_cap():
    parsed = parse_chat((FIX / "chat_ios_sample.txt").read_text(encoding="utf-8"), "x")
    segs = rows.segment(parsed.messages)
    for budget in (50, 400, 5000):
        packs = rows.pack(segs, budget)
        assert sum(len(p) for p in packs) == len(segs) and all(len(p) <= rows.PACK_ROWS for p in packs)


def test_model_down_stores_nothing(lab, monkeypatch):
    def down(*a, **k):
        raise llm.LabLLMError("down")

    monkeypatch.setattr(llm, "chat_json", down)
    with pytest.raises(llm.LabLLMError):
        rows.process(lab, "ios_sample", "Sam", CIRCLE)
    assert lab.rows() == []


def _orbit_rows(lab):
    return [r for r in lab.rows() if "video editing" in r["topics"]]


def test_followup_resolved_only_with_cited_notes_and_memory_updated(lab, monkeypatch):
    monkeypatch.setattr(llm, "chat_json", model())
    rows.process(lab, "ios_sample", "Sam", CIRCLE)
    rec = followups.recurring(lab)
    assert rec["rows"] == len(lab.rows())
    scored = _orbit_rows(lab)[0]["recurring"]["video editing"]
    assert 0 < scored["score"] <= 1 and scored["rows"] >= 2
    open_before = len(lab.followups("open"))
    assert open_before >= 2

    # unsourced "resolved" is rejected, the follow-up stays open
    monkeypatch.setattr(llm, "chat_json", model(answer={"status": "resolved", "answer": "Friday.", "evidence": []}))
    out = followups.resolve(lab, limit=1)
    assert out["resolved"] == 0 and out["rejected_unsourced"] == 1 and len(lab.followups("open")) == open_before

    monkeypatch.setattr(llm, "chat_json", model(answer={"status": "resolved", "answer": "The cut is due Friday.", "evidence": [1]}))
    out = followups.resolve(lab)
    assert out["resolved"] >= 1 and len(lab.followups("open")) < open_before
    done = [f for f in lab.followups("resolved")][0]
    row = next(r for r in lab.rows() if r["id"] == done["row_id"])
    assert row["memory"].endswith("Clarified: The cut is due Friday.") and row["memory_original"] == "Sam and Lina work on the Orbit promo."
    assert done["evidence_rows"] and all(e in {r["id"] for r in lab.rows()} for e in done["evidence_rows"])
    assert next(w for w in lab.windows() if w["id"] == row["id"])["summary"] == row["memory"]
    assert followups.open_by_row(lab).get(row["id"]) is None


def test_followup_with_no_related_rows_stays_open(lab, monkeypatch):
    monkeypatch.setattr(llm, "chat_json", model(followup_for_orbit=False))
    rows.process(lab, "ios_sample", "Sam", CIRCLE)
    only = lab.rows()[0]
    lab.add_followup(only["id"], "Something nobody else mentions?", NOW)
    lab.db.execute("UPDATE lab_rows SET topics='[\"lonely topic\"]' WHERE id=?", (only["id"],))
    lab.db.execute("UPDATE lab_annotations SET norm='lonely topic', label='lonely topic' WHERE window_id=? AND facet='topic'", (only["id"],))
    monkeypatch.setattr(llm, "embed", lambda t, kind="document": (_ for _ in ()).throw(llm.LabLLMError("no embeddings")))
    out = followups.resolve(lab)
    mine = [f for f in lab.followups("open") if f["question"].startswith("Something nobody")]
    assert out["no_related_rows"] >= 1 and out["resolved"] == 0 and len(mine) == 1


def test_audit_blanks_row_text_and_withdraws_followups(lab, monkeypatch):
    monkeypatch.setattr(llm, "chat_json", model())
    rows.process(lab, "ios_sample", "Sam", CIRCLE)
    victim = lab.rows()[0]
    lab.db.execute("UPDATE lab_rows SET user_text='BAD user line' WHERE id=?", (victim["id"],))
    lab.add_followup(victim["id"], "BAD question?", NOW)
    result = extract.audit(lab)
    assert result["by_category"].get("user_text:health") == 1 and result["by_category"].get("followup:health") == 1
    assert lab.rows()[0]["user_text"] == "" and not [f for f in lab.followups("open") if "BAD" in f["question"]]


def test_forget_chat_removes_rows_followups_and_aliases(lab, monkeypatch):
    monkeypatch.setattr(llm, "chat_json", model())
    rows.process(lab, "ios_sample", "Sam", CIRCLE)
    assert lab.rows() and lab.followups() and lab.alias_suggestions()
    lab.forget_chat("ios_sample")
    assert lab.rows() == [] and lab.followups() == [] and lab.alias_suggestions() == [] and lab.windows() == []


def test_circle_file_roundtrip(tmp_path):
    (tmp_path / "circle.json").write_text(
        '{"owner":{"name":"Haitham"},"profile_summary":"p","people":{"mamty":{"name":"mamty","relation":"mother","nicknames":["مامتي"]}}}',
        encoding="utf-8")
    c = circle_mod.load(tmp_path)
    assert c.owner == "Haitham" and "mother" in c.prompt_block("mamty") and "unknown" in c.prompt_block("nobody")
    assert circle_mod.load(tmp_path / "missing").owner == ""


def test_alias_scan_catches_the_founders_typo_without_the_model():
    c = circle_mod.Circle(owner="هيثم", people={"m": {"name": "mamty", "nicknames": ["مامتي", "قطتي"]}})
    found = circle_mod.scan_aliases(["مامتب الحميلة صحيتي اخيرا", "ايه صحاكي يا قطتي كدا بس", "مامتي"], "m", c)
    assert found == [("مامتب", "مامتي")]  # exact nicknames and unrelated words are left alone
    assert circle_mod.scan_aliases(["مامتب"], "nobody", c) == []


def test_row_gets_the_corrected_name_and_suggestion_from_raw_text(lab, monkeypatch):
    circle = circle_mod.Circle(owner="Sam", people={"ios_sample": {"name": "Lina", "nicknames": ["Linaa"]}})
    monkeypatch.setattr(llm, "chat_json", model())
    # 'Lina' is exact; inject a typo into one message and make the model not copy it
    lab.db.execute("UPDATE connector_records SET text='Linab did you send the Orbit cut' WHERE source_id='ios_sample:1'")
    rows.process(lab, "ios_sample", "Sam", circle)
    assert any(s["alias"] == "Linab" and s["canonical"] == "Lina" for s in lab.alias_suggestions())


def test_shared_media_opens_a_deterministic_followup_and_never_a_description(lab, monkeypatch):
    monkeypatch.setattr(llm, "chat_json", model(followup_for_orbit=False))
    stats = rows.process(lab, "ios_sample", "Sam", CIRCLE)
    assert stats["followups_media"] == 1
    fu = lab.followups("open")
    assert len(fu) == 1 and "shared item" in fu[0]["question"]


def test_flagged_row_keeps_no_topics_because_a_topic_can_name_the_subject(lab, monkeypatch):
    base = model(sensitive_rows={1})
    monkeypatch.setattr(llm, "chat_json", base)
    rows.process(lab, "ios_sample", "Sam", CIRCLE)
    flagged = lab.rows()[0]
    assert flagged["sensitive"] == 1 and flagged["topics"] == []
    assert not [a for a in lab.annotations("topic") if a["window_id"] == flagged["id"]]
