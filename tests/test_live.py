"""Tests for live L1 context pack (WP-B)."""
from __future__ import annotations

import statistics
import time

from temporal_memory.live.context import context_pack, extract_aed, extract_date, fold, invalidate_alias_cache
from temporal_memory.models import Fact, FactEntity
from tests.fixtures.fake_store import FakeGraphStore


def test_arabizi_and_whole_word_matching_and_cache_invalidation():
    invalidate_alias_cache()
    st = FakeGraphStore.from_karim_slice()

    # Happy path: Arabizi "3omar" resolves to Omar Farouk
    res = context_pack("karim", "What did 3omar say about Zabeel Hall?", store=st)
    names = [e["name"] for e in res["entities"]]
    assert "Omar Farouk" in names
    assert "Omar El-Sayed" not in names  # co-occurring place/subject disambiguates to wedding Omar
    assert res["entities"][0]["roles_per_subject"][0]["role"] == "groom"

    # Failure-prevention: substring "omar" inside an unrelated word like "Khomari" must NOT fire;
    # and "ali" inside "alias" must NOT match!
    st.add_alias("karim", "p02", "Ali")
    sub_res = context_pack("karim", "Check the alias khomari settings", store=st)
    assert sub_res["entities"] == []

    # Cache invalidation on new alias addition
    miss = context_pack("karim", "Send specs to Omary", store=st)
    assert miss["entities"] == []
    st.add_alias("karim", "p02", "Omary")
    hit = context_pack("karim", "Send specs to Omary", store=st)
    assert [e["name"] for e in hit["entities"]] == ["Omar Farouk"]


def test_two_omars_collision_resolution():
    invalidate_alias_cache()
    st = FakeGraphStore.from_karim_slice()

    # Work context ("QamarTech" + billing) resolves to colleague Omar El-Sayed
    work_res = context_pack("karim", "What is Omar doing at QamarTech with billing?", store=st)
    assert [e["name"] for e in work_res["entities"] if "Omar" in e["name"]] == ["Omar El-Sayed"]

    # Wedding context ("Rana") resolves to friend Omar Farouk
    wed_res = context_pack("karim", "Did Omar update Rana on the venue?", store=st)
    assert [e["name"] for e in wed_res["entities"] if "Omar" in e["name"]] == ["Omar Farouk"]

    # Bare "Omar" with zero disambiguating context keeps both marked ambiguous + low confidence
    bare = context_pack("karim", "Where is Omar?", store=st)
    omars = [e for e in bare["entities"] if "Omar" in e["name"]]
    assert len(omars) == 2
    assert all(o["ambiguous"] is True and o["confidence"] == "low" for o in omars)


def test_arabic_query_with_no_latin_entity_hits_text_orig():
    invalidate_alias_cache()
    st = FakeGraphStore.from_karim_slice()

    res = context_pack("karim", "متى يبدأ كورس الوكلاء الذكية؟", store=st)
    assert res["facts"], "Arabic query must retrieve fact via text_orig even with zero Latin entity hits"
    assert res["facts"][0]["id"] == "f040"


def test_dates_aed_candidates_and_open_changes_within_budget():
    invalidate_alias_cache()
    st = FakeGraphStore.from_karim_slice()

    res = context_pack("karim", "Did DarProperty raise Al Barsha rent to AED 5,400 on Nov 1? Ask Talal.", max_tokens=1500, store=st)
    assert res["tokens_est"] <= 1500
    assert any(a["amount_aed"] == 5400.0 for a in res["aed_amounts"])
    assert any(d["iso"].endswith("-11-01") for d in res["dates"])
    assert "Talal" in res["candidate_names"]
    assert any(c["fact_id"] == "f003" and "was until 2026-11-01" in c["summary"] for c in res["open_changes"])
    assert res["provenance"] and res["as_of"]


def test_forgotten_fact_absent_from_context_pack():
    invalidate_alias_cache()
    st = FakeGraphStore.from_karim_slice()

    before = context_pack("karim", "Al Barsha rent AED 5,400", store=st)
    assert any(f["id"] == "f004" for f in before["facts"])

    st.forget_source("karim", ["g081"])
    after = context_pack("karim", "Al Barsha rent AED 5,400", store=st)
    assert not any(f["id"] == "f004" for f in after["facts"])


def test_latency_p95_under_150ms_on_5k_synthetic_facts():
    invalidate_alias_cache()
    st = FakeGraphStore.from_karim_slice()
    # Seed up to 5,000 synthetic facts
    base_len = len(st.facts["karim"])
    for idx in range(base_len, 5000):
        st.facts["karim"].append(
            Fact(
                id=f"syn-{idx}",
                owner="karim",
                text=f"Synthetic note number {idx} about routine project sprint milestone topic{idx % 25}.",
                text_orig=f"ملاحظة تجريبية رقم {idx} في البرشاء" if idx % 10 == 0 else None,
                subject_id="s08",
                valid_from="2026-11-10",
                evidence=["n001"],
                entities=[FactEntity(entity_id="p03", role="teammate")] if idx % 20 == 0 else [],
            )
        )
    st._facts_ver["karim"] += 1

    # Warm index + measure 40 live queries
    context_pack("karim", "Warmup query for 3omar at QamarTech", store=st)
    queries = [
        "What did 3omar say about Zabeel Hall?",
        "Omar billing QamarTech sprint milestone topic5",
        "متى يبدأ كورس الوكلاء الذكية؟",
        "Al Barsha rent AED 5,400 topic12",
    ] * 10

    latencies_ms: list[float] = []
    for q in queries:
        t0 = time.perf_counter()
        out = context_pack("karim", q, store=st)
        latencies_ms.append((time.perf_counter() - t0) * 1000.0)
        assert out["facts"]

    p95 = statistics.quantiles(latencies_ms, n=20)[18]
    assert p95 < 150.0, f"L1 p95={p95:.2f}ms exceeded 150ms budget"
