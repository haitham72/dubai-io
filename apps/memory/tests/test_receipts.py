"""E7: deterministic receipt / order / booking pre-pass. Synthetic fixtures only (no real people or orders)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from temporal_memory.core.extract import build_system_prompt, format_user_prompt
from temporal_memory.core.validator import validate
from temporal_memory.ingest.receipts import (
    HELD_BACK_KEY,
    PREFILLED_KEY,
    conflicts_with_prefilled,
    merge_prefilled,
    prefilled_from_context,
    prefilled_to_context,
    prepass,
)
from temporal_memory.models import Attempt, ExtractionOutput, FactEntity, Job, JobBundle, OutFact, Record


def _rec(rid: str, author: str, text: str, at: str = "2026-11-12T10:00:00", source: str = "gmail") -> Record:
    return Record(id=rid, owner="karim", source=source, at=at, author=author, text=text)


IPHONE = _rec(
    "g-iphone", "Apple Store UAE <noreply@applestore.example>",
    "Your receipt from Apple Store\nOrder number: W7351902846\nDate: 12 Nov 2026\n"
    "1 x iPhone 15 Pro 256GB Natural Titanium (Brand New) - AED 4,599.00\nTotal: AED 4,599.00\nThank you for your order.",
)
AMAZON = _rec(
    "g-amz", "Amazon.ae <auto-confirm@amazon.example>",
    "Order Confirmation\nOrder #171-3829104-5520716\nOrdered on November 10, 2026\n"
    "Items: Anker 65W USB-C Charger AED 129.00\nOrder Total: AED 129.00\nArriving soon.",
    at="2026-11-10T09:00:00",
)
TALABAT = _rec(
    "g-tlb", "Talabat <orders@talabat.example>",
    "Your order from Zaatar w Zeit\nOrder ID: TLB48210937\nItems: 2 x Chicken Shawarma Wrap\n"
    "Total: AED 54.50\nPayment received. Thank you for your order.",
    at="2026-11-13T20:15:00",
)
CLINIC = _rec(
    "g-clinic", "Barsha Smile Clinic <hello@barshasmile.example>",
    "Appointment confirmation\nBooking ref: BK203948\nDental cleaning appointment at Barsha Smile Clinic on 12 Dec 2026 at 6pm.",
)
PHARMACY = _rec(
    "g-pharm", "Aster Pharmacy <orders@aster.example>",
    "Order receipt\nOrder no: PH772811\nItems: Vitamin D3 tablets\nTotal: AED 45.00",
)
NEWSLETTER = _rec(
    "g-news", "Weekly Deals <news@deals.example>",
    "Weekly deals: iPhone 15 from AED 3,499! 20% off headphones this weekend only. Unsubscribe anytime.",
)
ARABIC = _rec(
    "g-ar", "نون <noreply@noon.example>",
    "إيصال الشراء\nرقم الطلب: N5521098\nالأصناف: سماعة بلوتوث\nالإجمالي: ١٢٠٫٥٠ درهم\n2026-11-15",
    at="2026-11-15T12:00:00",
)
RESTAURANT = _rec(
    "g-table", "Zuma Dubai <reservations@zuma.example>",
    "Reservation confirmed: table for 4 reservation at Zuma on 20 Nov 2026 at 8pm.",
)


def _purchase(res, rid):
    return next(p for p in res.prefilled if p.record_id == rid and p.kind == "purchase")


def test_iphone_receipt_verbatim_slots_and_provenance():
    res = prepass([IPHONE])
    p = _purchase(res, "g-iphone")
    f = p.fact
    assert p.slots["amount"] == "AED 4,599.00" and p.slots["currency"] == "AED"
    assert p.slots["order_id"] == "W7351902846"
    assert f.predicate == "buys" and f.event_at == "2026-11-12" and f.stated is False
    assert "iPhone 15 Pro 256GB" in f.object_text
    assert "AED 4599.00" in f.text.replace(",", "") and "W7351902846" in f.text
    span = IPHONE.text[f.span_start:f.span_end]
    assert "AED 4,599.00" in span and "W7351902846" in span and f.span_record_id == "g-iphone"
    device = next(x for x in res.prefilled if x.kind == "device")
    assert device.slots["brand"] == "Apple" and device.slots["capacity"] == "256GB"
    assert device.slots["condition"].lower() == "brand new"
    assert not res.held_back


def test_amazon_ae_order():
    p = _purchase(prepass([AMAZON]), "g-amz")
    assert p.slots["order_id"] == "171-3829104-5520716"
    assert p.slots["amount"] == "AED 129.00" and p.fact.event_at == "2026-11-10"
    assert p.fact.object_text.startswith("Anker 65W USB-C Charger")
    assert p.slots["merchant"] == "Amazon.ae"


def test_talabat_order_uses_record_date_when_text_has_none():
    p = _purchase(prepass([TALABAT]), "g-tlb")
    assert p.slots["merchant"] == "Zaatar w Zeit"
    assert p.slots["order_id"] == "TLB48210937" and p.slots["amount"] == "AED 54.50"
    assert p.fact.object_text == "2 x Chicken Shawarma Wrap"
    assert p.fact.event_at == "2026-11-13"


def test_arabic_receipt_keeps_original_span_and_ascii_amount():
    p = _purchase(prepass([ARABIC]), "g-ar")
    assert p.slots["order_id"] == "N5521098"
    assert p.slots["amount"] == "١٢٠٫٥٠ درهم"  # verbatim, original digits
    assert "AED 120.50" in p.fact.text  # deterministic digit/currency normalisation
    assert p.fact.text_orig and "١٢٠٫٥٠ درهم" in p.fact.text_orig
    assert p.fact.object_text == "سماعة بلوتوث" and p.fact.event_at == "2026-11-15"


def test_restaurant_booking_is_emitted_as_planned_visit():
    res = prepass([RESTAURANT])
    b = next(p for p in res.prefilled if p.kind == "booking")
    assert b.fact.predicate == "visits" and b.fact.modality == "planned"
    assert b.fact.event_at == "2026-11-20T20:00" and "Zuma" in b.fact.object_text


@pytest.mark.parametrize("rec,cat", [(CLINIC, "health"), (PHARMACY, "health")])
def test_health_records_are_held_back_never_emitted(rec, cat):
    res = prepass([rec])
    assert res.prefilled == []
    assert res.held_back == [(rec.id, cat)]
    ctx = prefilled_to_context(res)
    assert ctx[PREFILLED_KEY] == [] and ctx[HELD_BACK_KEY] == [{"record_id": rec.id, "category": cat}]
    assert "Vitamin" not in repr(ctx) and "Dental" not in repr(ctx)  # never the text


def test_non_receipt_newsletter_and_chitchat_emit_nothing():
    chat = _rec("n-1", "Mona <mona@example.test>", "Lunch at 1? Also AED 50 for the gift.", source="notes")
    res = prepass([NEWSLETTER, chat, _rec("wa-1", "Karim", "I paid AED 30 order 12345", source="whatsapp:best")])
    assert res.prefilled == [] and res.held_back == []


def test_empty_and_garbage_input_is_safe():
    assert prepass([]).prefilled == []
    assert prepass([_rec("x", "", "Receipt")]).prefilled == []  # keyword but no amount / id


# ---------------------------------------------------------------- prompt + validator
def _bundle(records):
    ctx = {"entities": [], "facts": [], "subjects": []}
    ctx.update(prefilled_to_context(prepass(records)))
    now = datetime(2026, 11, 13, 12, 0, tzinfo=timezone.utc)
    job = Job(
        id="job-1", owner="karim", kind="extract.day", priority=1, pool="internal",
        input_ref=[r.id for r in records], input_version=0, context_hash="c", prompt_version="extract@4",
        state="leased", attempt_no=1, fence_token="f", worker_id="w",
        lease_expires_at=(now + timedelta(minutes=5)).isoformat(),
    )
    return now, job, JobBundle(job=job, records=records, context=ctx, system_prompt="x", output_schema={})


def _llm_fact(text, evidence, **kw):
    return OutFact(
        text=text, text_orig=None, subject_path="home-money/purchases", entities=[], op="new", target=None,
        valid_from="2026-11-12", evidence=evidence, sensitive=None, **kw,
    )


def _attempt(facts):
    return Attempt(
        job_id="job-1", attempt_no=1, fence_token="f", worker_id="w", worker_kind="internal-cloud",
        model="claude-haiku-5-5", prompt_version="extract@4",
        output=ExtractionOutput(entities=[], facts=facts, links=[]),
    )


def test_prompt_tells_llm_slots_are_prefilled():
    _, _, bundle = _bundle([IPHONE, NEWSLETTER])
    prompt = format_user_prompt(bundle)
    assert "PRE-FILLED SLOTS" in prompt and "order_id=W7351902846" in prompt and "amount=AED 4,599.00" in prompt
    assert "do not restate" in prompt.lower()
    assert "PRE-FILLED" not in build_system_prompt(None)  # system prompt unchanged: no extra input tokens
    _, _, plain = _bundle([NEWSLETTER])
    assert "PRE-FILLED SLOTS" not in format_user_prompt(plain)  # nothing pre-filled -> prompt unchanged


def test_validator_rejects_llm_change_to_prefilled_slot():
    now, job, bundle = _bundle([IPHONE])
    changed = _llm_fact("Karim bought an iPhone 15 Pro for AED 3,999", ["g-iphone"], predicate="buys",
                        object_text="iPhone 15 Pro")
    wrong_id = _llm_fact("Order W7351900000 placed with Apple Store", ["g-iphone"])
    restated = _llm_fact("Karim bought an iPhone 15 Pro 256GB", ["g-iphone"], predicate="buys",
                         object_text="iPhone 15 Pro 256GB")
    other = _llm_fact("Apple Store sent the receipt to Karim by email", ["g-iphone"])
    attempt = _attempt([changed, wrong_id, restated, other])
    merge_prefilled(attempt.output, prefilled_from_context(bundle.context))
    verdict = validate(job, bundle, attempt, current_generation=0, now=now)
    assert verdict.ok is True
    assert verdict.reasons.count("prefilled_slot_changed") == 1  # reasons are de-duplicated
    kept = [f.text for f in attempt.output.facts]
    assert not any(t in kept for t in (changed.text, wrong_id.text, restated.text))
    assert other.text in kept  # the rest of the packet is still the LLM's job
    pre = [f for f in attempt.output.facts if f.span_record_id == "g-iphone" and f.predicate == "buys"]
    assert len(pre) == 1 and "AED 4599.00" in pre[0].text.replace(",", "")  # verbatim amount survived


def test_validator_keeps_prefilled_and_unrelated_llm_facts():
    now, job, bundle = _bundle([TALABAT])
    attempt = _attempt([_llm_fact("Karim likes Zaatar w Zeit", ["g-tlb"], predicate="likes", object_text="Zaatar w Zeit")])
    merge_prefilled(attempt.output, prefilled_from_context(bundle.context))
    verdict = validate(job, bundle, attempt, current_generation=0, now=now)
    assert verdict.ok and verdict.reasons == []
    assert len(attempt.output.facts) == 2 and attempt.output.facts[0].stated is False
    assert attempt.output.facts[0].entities[0].role == "merchant"


def test_conflict_helper_ignores_facts_about_other_records():
    prefilled = prepass([IPHONE]).prefilled
    unrelated = _llm_fact("Rent AED 5,000 received", ["g-other"])
    assert conflicts_with_prefilled(unrelated, prefilled) is False


# ---------------------------------------------------------------- Postgres: typed fields survive the applier
def test_applier_persists_typed_fields_and_inferred_provenance():
    from temporal_memory.core.applier import apply
    from temporal_memory.core.graph_store import PostgresGraphStore
    from temporal_memory.db.db import create_test_schema, drop_test_schema
    from temporal_memory.models import Owner

    db, schema = create_test_schema()
    try:
        store = PostgresGraphStore(db)
        store.create_owner(Owner(id="karim", label="Karim", kind="demo", display_name="Karim Haddad", self_aliases=["Karim"]))
        store.upsert_records("karim", [AMAZON])
        out = ExtractionOutput(entities=[], facts=[], links=[])
        merge_prefilled(out, prepass([AMAZON]).prefilled)
        job = Job(id="j-1", owner="karim", kind="extract.day", priority=1, pool="internal", input_ref=["g-amz"],
                  input_version=0, context_hash="c", prompt_version="extract@4", state="leased", attempt_no=1,
                  fence_token="t", worker_id="w")
        att = Attempt(job_id="j-1", attempt_no=1, fence_token="t", worker_id="w", worker_kind="internal-cloud",
                      model="claude-haiku-5-5", prompt_version="extract@4", output=out)
        verdict = apply("karim", job, att, db=db)
        assert verdict.ok and len(verdict.applied_fact_ids) == 1
        with db.connection() as conn:
            row = conn.execute(
                "SELECT provenance, predicate, object_text, event_at, span_record_id, span_start, span_end, text "
                "FROM facts WHERE owner=%s", ("karim",)).fetchone()
        assert row["provenance"] == "inferred"  # a merchant email is never "You told me"
        assert (row["predicate"], row["event_at"], row["span_record_id"]) == ("buys", "2026-11-10", "g-amz")
        assert AMAZON.text[row["span_start"]:row["span_end"]].count("171-3829104-5520716") == 1
        assert "171-3829104-5520716" in row["text"] and "AED 129.00" in row["text"]
    finally:
        drop_test_schema(db, schema)


def test_amount_only_receipts_and_user_notes_stay_with_the_llm():
    rent = _rec("g-rent", "Landlord <l@example.test>", "October rent receipt\nReceipt: October rent AED 5,000 received, thank you.")
    note = _rec("n-1", "Karim", "Consulate appointment booked Dec 2, need 4 photos + 600 AED.", source="notes")
    assert prepass([rent, note]).prefilled == []
