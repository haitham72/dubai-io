"""Extract + index + forget, with a fake local model (no LM Studio needed)."""
import hashlib
import re
from pathlib import Path

import pytest

from app.lab import extract, index, llm
from app.lab.parse import parse_chat
from app.lab.store import Lab

FIX = Path(__file__).parent / "fixtures" / "lab"
NOW = "2026-11-16T00:00:00+00:00"


def fake_vec(text: str) -> list[float]:
    """Deterministic bag-of-words vector so similar labels land close together."""
    v = [0.0] * 64
    for w in re.findall(r"\w+", text.lower()):
        v[int(hashlib.md5(w.encode()).hexdigest(), 16) % 64] += 1.0
    return v


@pytest.fixture
def lab(tmp_path, monkeypatch):
    lab = Lab(tmp_path, "lab-test")
    parsed = parse_chat((FIX / "chat_ios_sample.txt").read_text(encoding="utf-8"), "ios_sample")
    lab.ingest_messages("whatsapp", "ios_sample", parsed.messages, NOW)
    monkeypatch.setattr(llm, "loaded_context", lambda model=None: 13891)
    monkeypatch.setattr(llm, "embed", lambda texts, kind="document": [fake_vec(t) for t in texts])
    return lab


def ids_in(user: str) -> list[int]:
    return [int(i) for i in re.findall(r"^#(\d+) ", user, re.M)]


def canned(system, user, schema, **kw):
    ids = ids_in(user)
    text = user
    out = {"summary": "They discuss work.", "tone": "neutral", "sensitive_touched": False, "topics": [],
           "projects": [], "people": [], "facts": [], "open_loops": []}
    if "Orbit" in text:
        i = next(i for i in ids if "Orbit" in re.search(rf"^#{i} .*$", user, re.M).group(0))
        mine = next((int(n) for n in re.findall(r"^#(\d+) \[[^\]]*\] Sam: .*Orbit", user, re.M)), i)
        out["topics"] = [{"label": "Video editing", "evidence": [i]}]
        out["projects"] = [{"name": "Orbit promo", "evidence": [i]}]
        out["people"] = [{"name": "Lina", "role": "client contact", "evidence": [i]}]
        out["open_loops"] = [{"text": "send the new Orbit promo draft", "who": "me", "evidence": [i]}]
        out["facts"] = [
            {"statement": "Sam is a freelance video editor", "subject": "self", "category": "work", "confidence": 0.9, "evidence": [mine]},
            {"statement": "Lina is the client contact", "subject": "Lina", "category": "work", "confidence": 0.8, "evidence": [i]},
            {"statement": "Sam has a kidney problem", "subject": "self", "category": "other", "confidence": 0.9, "evidence": [i]},
            {"statement": "Lina is going through a divorce", "subject": "Lina", "category": "relationship", "confidence": 0.9, "evidence": [i]},
            {"statement": "Sam likes tea", "subject": "self", "category": "preference", "confidence": 0.9, "evidence": [9999]},
        ]
    return out


def test_windows_never_exceed_budget(lab):
    msgs = lab.load_messages("whatsapp", "ios_sample")
    for budget in (60, 150, 3000):
        wins = extract.make_windows(msgs, budget)
        assert sum(len(w) for w in wins) == sum(m.kind == "message" for m in msgs)
        for w in wins:
            cost = sum(llm.est_tokens(extract._line(m)) + 1 for m in w)
            assert len(w) == 1 or cost <= budget


def test_extract_happy_path_rules_enforced(lab, monkeypatch):
    monkeypatch.setattr(llm, "chat_json", canned)
    stats = extract.process(lab, "ios_sample", "Sam")
    assert stats["windows_stored"] >= 1 and stats.get("facts_user_supplied", 0) + stats.get("facts_inferred", 0) >= 1
    facts = lab.annotations("fact")
    texts = [f["label"] for f in facts]
    assert any("freelance video editor" in t for t in texts)
    assert not any("kidney" in t or "divorce" in t or "tea" in t for t in texts)  # sensitive, third-party private, unsourced
    assert extract.leak_check(lab) == 0 and extract.unsourced_facts(lab) == 0
    for f in facts:
        assert f["evidence"] and f["valid_from"]
        # user_supplied only when the owner spoke every evidence message
        assert f["provenance"] in {"user_supplied", "inferred"}
    own = next(f for f in facts if "freelance video editor" in f["label"])
    assert own["provenance"] == "user_supplied" and own["confidence"] == 1.0
    third = next(f for f in facts if "client contact" in f["label"])
    assert third["provenance"] == "inferred" and third["confidence"] <= 0.9
    assert stats["dropped_by_category"].get("health") and stats["dropped_by_category"].get("third_party_private")
    assert stats["dropped_by_category"].get("no_source")


def test_extract_is_resumable(lab, monkeypatch):
    monkeypatch.setattr(llm, "chat_json", canned)
    first = extract.process(lab, "ios_sample", "Sam")
    again = extract.process(lab, "ios_sample", "Sam")
    assert again["windows_skipped_done"] == first["windows_planned"] and again.get("llm_calls", 0) == 0


def test_context_overflow_splits_and_still_covers_every_message(lab, monkeypatch):
    calls = []

    def flaky(system, user, schema, **kw):
        calls.append(len(ids_in(user)))
        if len(ids_in(user)) > 4:
            raise llm.ContextOverflow("too long")
        return canned(system, user, schema)

    monkeypatch.setattr(llm, "chat_json", flaky)
    stats = extract.process(lab, "ios_sample", "Sam")
    assert stats["overflow_splits"] >= 1
    covered = sum(w["n_msgs"] for w in lab.windows())
    assert covered == sum(m.kind == "message" for m in lab.load_messages("whatsapp", "ios_sample"))
    assert extract.process(lab, "ios_sample", "Sam")["windows_skipped_done"] == stats["windows_planned"]  # resume key survives a split


def test_model_down_fails_loudly_and_stores_nothing(lab, monkeypatch):
    def down(*a, **k):
        raise llm.LabLLMError("LM Studio not reachable")

    monkeypatch.setattr(llm, "chat_json", down)
    with pytest.raises(llm.LabLLMError):
        extract.process(lab, "ios_sample", "Sam")
    assert lab.windows() == [] and lab.annotations() == []


def test_sensitive_filter_blocks_credentials_and_arabic():
    from app.lab.sensitive import filter_statement

    assert filter_statement("the password for the studio gmail is x") == "credential"
    assert filter_statement("عنده مرض") == "health"
    assert filter_statement("Sam edits video for Orbit") is None


def test_index_queries_and_forget(lab, monkeypatch):
    monkeypatch.setattr(llm, "chat_json", canned)
    extract.process(lab, "ios_sample", "Sam")
    built = index.build(lab)
    assert built["windows"] >= 1 and built["labels"] >= 1
    assert index.build(lab) == {"windows": 0, "labels": 0}  # idempotent
    topics = index.recurring_topics(lab, min_weeks=1)
    assert topics and topics[0]["topic"] == "video editing"
    proj = index.projects(lab)
    assert proj[0]["project"] == "Orbit promo" and "Lina" in proj[0]["people"] and proj[0]["open_loops"]
    assert index.person(lab, "lina")["windows"] >= 1
    assert index.open_loops(lab)[0]["loop"].startswith("send the new Orbit")
    hits = index.search(lab, "Orbit promo draft")
    assert hits and all(h["evidence"] for h in hits)
    removed = lab.forget_chat("ios_sample")
    assert removed["annotations"] > 0
    assert lab.windows() == [] and lab.annotations() == [] and lab.vectors("window") == {}
    assert lab.load_messages("whatsapp", "ios_sample") == []
    assert lab.db.execute("SELECT COUNT(*) FROM mem_patterns").fetchone()[0] == 0
    assert lab.db.execute("SELECT COUNT(*) FROM mem_events").fetchone()[0] == 0


def test_call_lines_count_as_media_not_text():
    from app.lab.parse import parse_chat

    raw = "[08/02/2025, 2:21:27 PM] Haitham: ‎Video call, ‎20 sec\n[09/02/2025, 12:02:49 PM] mamty♥️: hello\n"
    p = parse_chat(raw, "x")
    assert [m.kind for m in p.messages] == ["media", "message"] and p.messages[1].sender == "mamty♥️"


def smart_model(flag=()):
    """Fake local model for the label-only calls: privacy screen, group, theme. `flag` = labels the screen blocks."""

    def fn(system, user, schema, **kw):
        if "privacy screen" in system:
            lines = re.findall(r"^(\d+)\. (.+)$", user, re.M)
            return {"items": [{"n": int(n), "category": "religion" if label in flag else "none"} for n, label in lines]}
        labels = re.findall(r"^- (.+)$", user, re.M)
        if "life themes" in system:
            return {"items": [{"group": g, "theme": "Career"} for g in labels]}
        return {"items": [{"label": x, "group": "Video work"} for x in labels]}

    return fn


def prepared(lab, monkeypatch):
    monkeypatch.setattr(llm, "chat_json", canned)
    extract.process(lab, "ios_sample", "Sam")
    index.build(lab)


def test_topic_tree_and_graph_render(lab, monkeypatch):
    from app.lab import tree

    prepared(lab, monkeypatch)
    monkeypatch.setattr(llm, "chat_json", smart_model())
    built = tree.build(lab, me="Sam", min_edge=1)
    assert built["tree"]["Career"]["Video work"] and built["withheld"] == {}
    assert {"topic", "person", "project"} <= {n["kind"] for n in built["nodes"]} and built["edges"]
    assert all(n["label"] != "Sam" and "role" not in n for n in built["nodes"])  # owner is the centre; no guessed roles
    md = tree.render_tree(built)
    assert "## Career" in md and "```mermaid" in md and "video editing" in md
    assert "graph LR" in tree.render_graph(built)


def test_tree_withholds_what_only_the_model_can_recognise(lab, monkeypatch):
    from app.lab import tree

    prepared(lab, monkeypatch)
    monkeypatch.setattr(llm, "chat_json", smart_model(flag={"video editing"}))  # regex would pass this label
    built = tree.build(lab, me="Sam", min_edge=1)
    assert built["withheld"] == {"religion": 1}
    assert "video editing" not in tree.render_tree(built)


def test_tree_fails_closed_when_model_is_down(lab, monkeypatch):
    from app.lab import tree

    prepared(lab, monkeypatch)

    def down(*a, **k):
        raise llm.LabLLMError("down")

    monkeypatch.setattr(llm, "chat_json", down)
    with pytest.raises(llm.LabLLMError):  # no unscreened tree is ever produced
        tree.build(lab, me="Sam")


def test_screen_blocks_skipped_items_and_audit_purges_everywhere(lab, monkeypatch):
    from app.lab.sensitive import screen

    prepared(lab, monkeypatch)
    win = lab.windows()[0]
    aid = lab.add_annotation(win["id"], "ios_sample", "fact", "Sam keeps a quiet evening routine", "x", [1],
                             provenance="inferred", valid_from="2026-10-01T00:00:00", as_of=NOW)
    lab.memory.add_pattern(lab.owner, "Sam keeps a quiet evening routine", evidence=[{"chat": "ios_sample", "idx": 1}])
    lab.put_vector("annotation", aid, "m", [1.0, 0.0])
    monkeypatch.setattr(llm, "chat_json", smart_model(flag={"Sam keeps a quiet evening routine"}))
    result = extract.audit(lab)
    assert result["annotations_purged"] == 1 and result["by_category"] == {"religion": 1}
    assert all(a["id"] != aid for a in lab.annotations())
    assert aid not in lab.vectors("annotation")
    assert lab.db.execute("SELECT COUNT(*) FROM mem_patterns WHERE statement=?", ("Sam keeps a quiet evening routine",)).fetchone()[0] == 0

    monkeypatch.setattr(llm, "chat_json", lambda *a, **k: {"items": []})  # model skips every item
    assert set(screen(["anything"]).values()) == {"unscreened"}


def test_flagged_slice_withholds_summary_facts_and_loops(lab, monkeypatch):
    def flagged(system, user, schema, **kw):
        out = canned(system, user, schema)
        out["sensitive_touched"] = True
        return out

    monkeypatch.setattr(llm, "chat_json", flagged)
    stats = extract.process(lab, "ios_sample", "Sam")
    assert lab.annotations("fact") == [] and lab.annotations("loop") == []
    assert lab.windows()[0]["summary"].startswith("[summary withheld")
    assert lab.annotations("topic") and stats["dropped_by_category"]["flagged_slice_items"] >= 1
