"""The labelled live extractor gate and provenance semantics."""
from __future__ import annotations

from collections import Counter
import json
import os
from pathlib import Path
from time import perf_counter_ns

import pytest

from temporal_memory.db.db import fold_text
from temporal_memory.live.triples import extract_triples, fact_from_triple, quarantine_category
from temporal_memory.models import Owner, Record


@pytest.fixture(scope="module")
def traps():
    candidates = [
        Path(__file__).parents[1] / "acceptance" / "traps_dataset.json",
        Path(os.environ.get("TM_U2_TRAPS", "G:/Haitham/lab-data/memory-bakeoff/acceptance/traps_dataset.json")),
    ]
    for path in candidates:
        if path.is_file():
            result = json.loads(path.read_text(encoding="utf-8"))["items"]
            assert len(result) == 84
            return result
    pytest.skip("The acceptance trap fixture is unavailable")


def test_all_traps_and_positive_recall(traps):
    scores = Counter()
    for case in traps:
        text = case["text"]
        action = case["expected_action"]
        result = extract_triples(text)
        if action != "emit_triple":
            assert not result, case["id"]
            assert bool(quarantine_category(text)) == (action == "quarantine"), case["id"]
            continue
        scores[case["lang"], "total"] += 1
        if not result:
            continue
        assert len(result) == 1
        triple, = result
        expected = case["expected_triple"]
        # U0c's predicate set has no 'books'. The captured span preserves the booking verb.
        mapped = "other" if expected["predicate"] == "books" else expected["predicate"]
        assert triple.predicate == mapped, case["id"]
        assert fold_text(triple.object_text) == fold_text(expected["object"]), case["id"]
        assert text[triple.span_start:triple.span_end].endswith(triple.object_text)
        scores[case["lang"], "correct"] += 1
    assert [scores[lang, "correct"] for lang in ("en", "ar", "arz")] == [11, 7, 8]
    print(dict(scores))


def test_parser_latency_p95_on_840_turns(traps):
    elapsed = []
    for case in traps * 10:
        start = perf_counter_ns()
        extract_triples(case["text"])
        elapsed.append((perf_counter_ns() - start) / 1_000_000)
    p95 = sorted(elapsed)[797]
    print(f"840 mixed turns: parser p95 {p95:.4f} ms")
    assert p95 < 50


@pytest.mark.parametrize("text, modality, status, provenance", [
    ("I bought an iPhone yesterday", "done", "active", "user_supplied"),
    ("I want to buy an iPhone", "wanted", "hypothesis", "inferred"),
    ("I will buy an iPhone", "planned", "hypothesis", "inferred"),
])
def test_live_fact_provenance(text, modality, status, provenance):
    triple, = extract_triples(text)
    owner = Owner("synthetic", "Synthetic")
    record = Record("turn", owner.id, "live", "2026-11-24T12:00:00+04:00", owner.id, text)
    fact = fact_from_triple(owner, record, triple, "events")
    assert (fact.modality, fact.status, fact.provenance, fact.polarity) == (modality, status, provenance, "affirmed")
    assert fact.span_record_id == record.id
    assert fact.evidence == [record.id]


@pytest.mark.parametrize("text", [
    "Sara bought an iPhone",
    "I bought an iPhone right",
    "I bought it",
    "I bought a phone, didn't I",
    "I got a message from Sara",
])
def test_ambiguous_turns_abstain(text):
    assert extract_triples(text) == []
