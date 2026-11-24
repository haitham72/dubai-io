"""Deterministic pre-pass for receipts, orders, devices and bookings (E7).

Prices, order ids, dates and model names are copied verbatim from the record by
regex and never re-written by an LLM (root rule 2). The pre-pass runs over
email / notes records *before* the LLM call and emits contract-v2 typed facts
(`predicate`, `object_text`, `event_at`, span offsets) with ``provenance=inferred``:
a merchant email is the merchant's statement, never "You told me", so
``stated`` is always False.

Rule 9: ``pre_write`` runs over the record and over every emitted fact. A hit
(health purchase, clinic booking, credential ...) means nothing is emitted for
that record; only ``(record_id, category)`` is kept, never the text.

The LLM is told which slots are pre-filled and must not change them; the
validator drops any LLM fact that contradicts a pre-filled slot
(``prefilled_slot_changed``) via :func:`conflicts_with_prefilled`.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
import re
from typing import Any, Iterable

from temporal_memory.db.db import fold_text
from temporal_memory.models import ExtractionOutput, FactEntity, OutEntity, OutFact, Record
from temporal_memory.privacy.sensitive import pre_write

PREFILLED_KEY = "prefilled"
HELD_BACK_KEY = "prefilled_held_back"
SOURCES = ("email", "gmail", "notes")

# ------------------------------------------------------------------ patterns
_AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩٫٬", "0123456789.,")
_NUM = r"[0-9٠-٩][0-9٠-٩,٬]*(?:[.٫][0-9٠-٩]{1,2})?"
_CUR = r"(?:AED|USD|Dhs?\.?|د\.إ|درهم|دولار|US\$|\$)"
_MONEY_PRE = re.compile(rf"(?P<cur>{_CUR})\s?(?P<num>{_NUM})", re.I)
_MONEY_POST = re.compile(rf"(?P<num>{_NUM})\s?(?P<cur>{_CUR})(?![A-Za-z])", re.I)
_TOTAL = re.compile(
    r"(?:grand\s+total|order\s+total|total(?:\s+paid)?|amount\s+paid|paid|charged|"
    r"الإجمالي|الاجمالي|المجموع|المبلغ(?:\s+المدفوع)?|تم\s+دفع)\s*[:：\-]?\s*",
    re.I,
)
_TOTAL_TAIL = re.compile(_TOTAL.pattern + r"$", re.I)
_ORDER_ID = re.compile(
    r"(?:order|invoice|receipt|reference|ref|booking|confirmation|reservation)"
    r"\s*(?:no\.?|number|num|id|#)?\s*[:#：]?\s*(?P<id>(?=[A-Z0-9-]*\d)[A-Z0-9][A-Z0-9-]{4,24})"
    r"|(?:رقم\s+(?:الطلب|الفاتورة|الحجز|المرجع))\s*[:#：]?\s*(?P<id_ar>(?=[A-Z0-9-]*\d)[A-Z0-9][A-Z0-9-]{3,24})"
    r"|(?P<amz>\b\d{3}-\d{7}-\d{7}\b)",
    re.I,
)
_RECEIPT_KW = re.compile(
    r"\b(?:order\s+(?:confirmation|confirmed|summary|receipt|placed)|your\s+order|receipt|invoice|"
    r"payment\s+(?:received|confirmation|successful)|thank\s+you\s+for\s+(?:your\s+)?(?:order|purchase)|"
    r"purchase\s+confirmation|tax\s+invoice)\b|"
    r"(?:تأكيد\s+(?:الطلب|الدفع)|إيصال|ايصال|فاتورة|طلبك|شكرا\s+لطلبك|تم\s+الدفع)",
    re.I,
)
_PROMO = re.compile(
    r"\b(?:unsubscribe|newsletter|\d+\s?%\s+off|flash\s+sale|limited\s+offer|deals?\s+of\s+the|"
    r"weekly\s+deals|promo\s+code|coupon)\b|اشترك\s+في\s+النشرة|خصم\s+\d+",
    re.I,
)
_ITEM_LINE = re.compile(
    r"^\s*(?:(?:item|items|product|description|الصنف|المنتج|الأصناف|الاصناف)\s*[:：\-]\s*|"
    r"(?:\d+\s*[x×]\s+))(?P<item>[^\n]{2,120}?)\s*(?:[-–—,]\s*|\s+)?"
    rf"(?:{_CUR}\s?{_NUM}|{_NUM}\s?{_CUR})?\s*$",
    re.I | re.M,
)
_MERCHANT_FROM = re.compile(
    r"(?:your\s+order\s+from|order\s+from|purchased\s+from|sold\s+by|from\s+merchant|"
    r"طلبك\s+من|الطلب\s+من|التاجر)\s*[:：]?\s*(?P<m>[^\n,.;:()]{2,50})",
    re.I,
)
_BOOK_KW = re.compile(
    r"\b(?:appointment|booking|reservation|reserved|booked|check-?in)\b|(?:موعد|حجز)", re.I
)
_BOOK_WHAT = re.compile(
    r"(?P<what>(?:[A-Za-z][A-Za-z ]{2,40})?(?:appointment|booking|reservation|table for \d+)|"
    r"(?:موعد|حجز)\s+[^\n.,،]{2,40})",
    re.I,
)
_BOOK_WHERE = re.compile(r"\b(?:at|in)\s+(?P<where>[A-Z][\w&' -]{2,40}?)(?=\s+(?:on|at|for)\b|[.,\n]|$)|(?:في|عند)\s+(?P<where_ar>[^\n.,،]{2,40})")
_TIME = re.compile(r"\b(?P<h>\d{1,2})(?::(?P<m>\d{2}))?\s?(?P<ap>am|pm)\b|\b(?P<h24>[01]?\d|2[0-3]):(?P<m24>[0-5]\d)\b", re.I)
_MONTHS = {m: i + 1 for i, m in enumerate("jan feb mar apr may jun jul aug sep oct nov dec".split())}
_DATE_ISO = re.compile(r"\b(?P<y>20\d{2})-(?P<m>\d{2})-(?P<d>\d{2})\b")
_DATE_DMY = re.compile(r"\b(?P<d>\d{1,2})(?:st|nd|rd|th)?\s+(?P<mon>jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?,?\s+(?P<y>20\d{2})\b", re.I)
_DATE_MDY = re.compile(r"\b(?P<mon>jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(?P<d>\d{1,2})(?:st|nd|rd|th)?,?\s+(?P<y>20\d{2})\b", re.I)
_DATE_SLASH = re.compile(r"\b(?P<d>\d{1,2})/(?P<m>\d{1,2})/(?P<y>20\d{2})\b")
_DATE_MD = re.compile(r"\b(?P<mon>jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(?P<d>\d{1,2})\b(?!:)", re.I)
_DEVICE = re.compile(
    r"\b(?P<brand>Apple|Samsung|Google|Huawei|Xiaomi|OnePlus|Sony|Dell|Lenovo|HP)?\s?"
    r"(?P<model>iPhone\s?\d{1,2}(?:\s?(?:Pro\s?Max|Pro|Plus|Mini|e))?|iPad(?:\s(?:Pro|Air|mini))?(?:\s?\d{1,2}(?:\.\d)?\"?)?|"
    r"MacBook\s(?:Air|Pro)(?:\s?\d{2}\"?)?|Galaxy\s(?:S|A|Z\s?Flip|Z\s?Fold)\s?\d{1,2}(?:\s?(?:Ultra|Plus|\+|FE))?|"
    r"Pixel\s\d{1,2}(?:\s?Pro)?|AirPods(?:\s(?:Pro|Max))?(?:\s?\d)?|Apple\sWatch(?:\s(?:Series|SE|Ultra)\s?\d*)?)"
    r"(?:\s+(?P<cap>\d{2,4}\s?(?:GB|TB)))?",
    re.I,
)
_CONDITION = re.compile(r"\b(?P<c>brand\s+new|like\s+new|refurbished|renewed|open[- ]box|used|new)\b|(?P<c_ar>مستعمل|مجدد|جديد)", re.I)


# ------------------------------------------------------------------ types
@dataclass
class Slot:
    """One verbatim value with its offsets in the record text."""
    value: str
    start: int
    end: int


@dataclass
class Prefilled:
    record_id: str
    kind: str                          # purchase | device | booking
    fact: OutFact
    slots: dict[str, str] = field(default_factory=dict)  # verbatim values (amount, order_id, ...)

    def to_dict(self) -> dict[str, Any]:
        return {"record_id": self.record_id, "kind": self.kind, "slots": dict(self.slots), "fact": asdict(self.fact)}


@dataclass
class PrepassResult:
    prefilled: list[Prefilled] = field(default_factory=list)
    held_back: list[tuple[str, str]] = field(default_factory=list)  # (record_id, category) - never text


# ------------------------------------------------------------------ helpers
def _ascii_num(s: str) -> str:
    return s.translate(_AR_DIGITS)


def _norm_amount(num: str) -> str:
    """Canonical comparable amount: ASCII digits, no thousands separators."""
    n = _ascii_num(num).replace(",", "")
    return n[:-3] if n.endswith(".00") else n


def _currency(cur: str) -> str:
    c = cur.lower().rstrip(".")
    if c in {"usd", "us$", "$", "دولار"}:
        return "USD"
    return "AED"


def _display_name(author: str) -> str:
    name = re.sub(r"<[^>]*>", "", author or "").strip().strip('"').strip()
    return name


def money_values(text: str) -> list[str]:
    """Normalised amounts ('AED 54.5' -> '54.5') mentioned in free text."""
    out: list[str] = []
    for rx in (_MONEY_PRE, _MONEY_POST):
        out.extend(_norm_amount(m.group("num")) for m in rx.finditer(text or ""))
    return out


def order_ids(text: str) -> list[str]:
    out = []
    for m in _ORDER_ID.finditer(text or ""):
        out.append((m.group("id") or m.group("id_ar") or m.group("amz")).upper())
    return out


def _find_amount(text: str) -> tuple[Slot, str] | None:
    """Prefer the amount right after a total keyword; else the last amount."""
    cands: list[tuple[int, int, str, str, bool]] = []
    for rx in (_MONEY_PRE, _MONEY_POST):
        for m in rx.finditer(text):
            near_total = bool(_TOTAL_TAIL.search(text[max(0, m.start() - 40):m.start()]))
            cands.append((m.start(), m.end(), m.group(0), m.group("cur"), near_total))
    if not cands:
        return None
    totals = [c for c in cands if c[4]]
    pick = totals[-1] if totals else sorted(cands)[-1]
    return Slot(pick[2], pick[0], pick[1]), _currency(pick[3])


def _find_date(text: str, fallback_at: str) -> tuple[str | None, Slot | None]:
    ref_year = int(fallback_at[:4]) if fallback_at[:4].isdigit() else date.today().year
    for rx, build in (
        (_DATE_ISO, lambda m: (int(m["y"]), int(m["m"]), int(m["d"]))),
        (_DATE_DMY, lambda m: (int(m["y"]), _MONTHS[m["mon"][:3].lower()], int(m["d"]))),
        (_DATE_MDY, lambda m: (int(m["y"]), _MONTHS[m["mon"][:3].lower()], int(m["d"]))),
        (_DATE_SLASH, lambda m: (int(m["y"]), int(m["m"]), int(m["d"]))),
        (_DATE_MD, lambda m: (ref_year, _MONTHS[m["mon"][:3].lower()], int(m["d"]))),
    ):
        m = rx.search(text)
        if not m:
            continue
        try:
            return date(*build(m)).isoformat(), Slot(m.group(0), m.start(), m.end())
        except ValueError:
            continue
    return None, None


def _find_time(text: str) -> str | None:
    m = _TIME.search(text)
    if not m:
        return None
    if m["ap"]:
        h = int(m["h"]) % 12 + (12 if m["ap"].lower() == "pm" else 0)
        return f"{h:02d}:{int(m['m'] or 0):02d}"
    return f"{int(m['h24']):02d}:{m['m24']}"


def _find_items(text: str) -> list[Slot]:
    items: list[Slot] = []
    for m in _ITEM_LINE.finditer(text):
        v = m.group("item").strip().rstrip("-–—,: ")
        if len(v) >= 2 and not _MONEY_PRE.fullmatch(v):
            items.append(Slot(v, m.start("item"), m.start("item") + len(v)))
    return items


def _find_device(text: str) -> dict[str, str] | None:
    m = _DEVICE.search(text)
    if not m:
        return None
    model = m.group("model").strip()
    brand = (m.group("brand") or ("Apple" if re.match(r"(?i)iphone|ipad|macbook|airpods|apple", model) else "")).strip()
    # condition only when stated in the same line / neighbourhood
    around = text[max(0, m.start() - 60):m.end() + 80]
    cm = _CONDITION.search(around)
    out = {"brand": brand, "model": model, "span_start": str(m.start()), "span_end": str(m.end())}
    full = text[m.start():m.end()].strip()
    out["verbatim"] = full
    if m.group("cap"):
        out["capacity"] = m.group("cap")
    if cm:
        out["condition"] = cm.group("c") or cm.group("c_ar")
    return out


def _entity_for(merchant: str) -> tuple[OutEntity, FactEntity]:
    ref = f"new:{merchant}"
    return OutEntity(ref=ref, kind="org", aliases=[merchant], relation_to_user=None), FactEntity(entity_id=ref, role="merchant")


def _is_arabic(s: str) -> bool:
    return bool(re.search(r"[؀-ۿ]", s or ""))


# ------------------------------------------------------------------ extraction
def _purchase(rec: Record, text: str) -> Prefilled | None:
    if not _RECEIPT_KW.search(text):
        return None
    oid = _ORDER_ID.search(text)
    amount = _find_amount(text)
    if oid is None and amount is None:
        return None
    if _PROMO.search(text) and oid is None:
        return None
    if oid is None and not _find_items(text) and _find_device(text) is None:
        return None  # amount only (rent, bill, transfer): no purchase slot to copy; the LLM handles it
    mm = _MERCHANT_FROM.search(text)
    merchant = (mm.group("m").strip() if mm else _display_name(rec.author)).strip()
    if not merchant or "@" in merchant:
        return None
    items = _find_items(text)
    dev = _find_device(text)
    item_slot = items[0] if items else None
    if item_slot is None and dev is not None:
        item_slot = Slot(dev["verbatim"], int(dev["span_start"]), int(dev["span_end"]))
    iso, _ = _find_date(text, rec.at)
    event_at = iso or (rec.at[:10] if rec.at else None)
    parts: list[Slot] = []
    slots: dict[str, str] = {"merchant": merchant}
    if item_slot:
        parts.append(item_slot)
        slots["item"] = item_slot.value
    amt_text = ""
    if amount:
        parts.append(amount[0])
        slots["amount"] = amount[0].value
        slots["currency"] = amount[1]
        amt_text = f" for {amount[1]} {_ascii_num(re.sub(_CUR, '', amount[0].value, flags=re.I)).strip()}"
    oid_val = None
    if oid:
        oid_val = oid.group("id") or oid.group("id_ar") or oid.group("amz")
        key = "id" if oid.group("id") else ("id_ar" if oid.group("id_ar") else "amz")
        parts.append(Slot(oid_val, oid.start(key), oid.end(key)))
        slots["order_id"] = oid_val
    if event_at:
        slots["event_at"] = event_at
    start = min(p.start for p in parts) if parts else 0
    end = max(p.end for p in parts) if parts else len(text)
    obj = item_slot.value if item_slot else f"order {oid_val}" if oid_val else f"purchase from {merchant}"
    ids = f" (order {oid_val})" if oid_val else ""
    fact_text = f"Bought {obj} from {merchant}{amt_text}{ids}" + (f" on {event_at}" if event_at else "")
    orig = text[start:end] if _is_arabic(text[start:end]) or _is_arabic(obj) else None
    ent_out, ent_fact = _entity_for(merchant)
    fact = OutFact(
        text=fact_text, text_orig=orig, subject_path="home-money/purchases", entities=[ent_fact],
        op="new", target=None, valid_from=event_at or "", evidence=[rec.id], sensitive=None,
        predicate="buys", object_text=obj, polarity="affirmed", modality="done", event_at=event_at,
        span_record_id=rec.id, span_start=start, span_end=end, stated=False,
    )
    return Prefilled(rec.id, "purchase", fact, slots)


def _device(rec: Record, text: str, purchase: Prefilled | None) -> Prefilled | None:
    if purchase is None:
        return None
    dev = _find_device(text)
    if dev is None:
        return None
    start, end = int(dev["span_start"]), int(dev["span_end"])
    cond = f", condition: {dev['condition']}" if dev.get("condition") else ""
    fact = OutFact(
        text=f"Device: {dev['verbatim']}{cond} (from order {purchase.slots.get('order_id', 'receipt')})",
        text_orig=None, subject_path="home-money/devices", entities=list(purchase.fact.entities),
        op="new", target=None, valid_from=purchase.fact.valid_from, evidence=[rec.id], sensitive=None,
        predicate="other", object_text=dev["verbatim"], polarity="affirmed", modality="done",
        event_at=purchase.fact.event_at, span_record_id=rec.id, span_start=start, span_end=end, stated=False,
    )
    slots = {k: v for k, v in dev.items() if k in {"brand", "model", "capacity", "condition"}}
    return Prefilled(rec.id, "device", fact, slots)


def _booking(rec: Record, text: str) -> Prefilled | None:
    if not _BOOK_KW.search(text) or _PROMO.search(text):
        return None
    iso, dslot = _find_date(text, rec.at)
    if iso is None or dslot is None:
        return None
    wm = _BOOK_WHAT.search(text)
    if wm is None:
        return None
    what = wm.group("what").strip()
    where_m = _BOOK_WHERE.search(text)
    where = ((where_m.group("where") or where_m.group("where_ar")) if where_m else "") or _display_name(rec.author)
    where = where.strip()
    if not where:
        return None
    tm = _find_time(text[dslot.end:dslot.end + 40]) or _find_time(text[max(0, dslot.start - 30):dslot.start])
    when = f"{iso}T{tm}" if tm else iso
    start = min(wm.start("what"), dslot.start)
    end = max(wm.end("what"), dslot.end)
    obj = f"{what} at {where}" if where else what
    ent_out, ent_fact = _entity_for(where) if where and "@" not in where else (None, None)
    fact = OutFact(
        text=f"Booked {obj} on {when}",
        text_orig=text[start:end] if _is_arabic(text[start:end]) else None,
        subject_path="events/bookings", entities=[ent_fact] if ent_fact else [],
        op="new", target=None, valid_from=iso, evidence=[rec.id], sensitive=None,
        predicate="visits", object_text=obj, polarity="affirmed", modality="planned", event_at=when,
        span_record_id=rec.id, span_start=start, span_end=end, stated=False,
    )
    return Prefilled(rec.id, "booking", fact, {"what": what, "where": where, "when": when})


def _passes_rule9(rec: Record, text: str, items: Iterable[Prefilled]) -> str | None:
    cat = pre_write(text) or pre_write(rec.author or "")
    if cat:
        return cat
    for p in items:
        for t in (p.fact.text, p.fact.text_orig, p.fact.object_text):
            if t and (c := pre_write(t)):
                return c
    return None


def prepass(records: Iterable[Record]) -> PrepassResult:
    """Run the deterministic pre-pass; pure function, no I/O."""
    result = PrepassResult()
    for rec in records:
        src = (rec.source or "").lower()
        if not src.startswith(SOURCES) or not rec.text:
            continue
        text = rec.text
        purchase = _purchase(rec, text)
        # Bookings come from the provider's own email only; a user's note stays with the LLM.
        booking = None if purchase or not src.startswith(("email", "gmail")) else _booking(rec, text)
        found = [p for p in (purchase, _device(rec, text, purchase), booking) if p is not None]
        if not found:
            continue
        cat = _passes_rule9(rec, text, found)
        if cat:
            result.held_back.append((rec.id, cat))
            continue
        result.prefilled.extend(found)
    return result


# ------------------------------------------------------------------ hooks
def prefilled_to_context(result: PrepassResult) -> dict[str, Any]:
    return {
        PREFILLED_KEY: [p.to_dict() for p in result.prefilled],
        HELD_BACK_KEY: [{"record_id": r, "category": c} for r, c in result.held_back],
    }


def _fact_from_dict(d: dict[str, Any]) -> OutFact:
    d = dict(d)
    d["entities"] = [FactEntity(**e) for e in d.get("entities") or []]
    return OutFact(**d)


def prefilled_from_context(ctx: dict[str, Any] | None) -> list[Prefilled]:
    out: list[Prefilled] = []
    for d in (ctx or {}).get(PREFILLED_KEY) or []:
        out.append(Prefilled(d["record_id"], d["kind"], _fact_from_dict(d["fact"]), dict(d.get("slots") or {})))
    return out


def prompt_note(prefilled: list[Prefilled]) -> str:
    """User-prompt section listing the slots the LLM must treat as final."""
    if not prefilled:
        return ""
    lines = []
    for p in prefilled:
        slots = "; ".join(f"{k}={v}" for k, v in p.slots.items())
        lines.append(f"[{p.record_id}] {p.kind}: {slots}")
    return (
        "PRE-FILLED SLOTS (copied verbatim by code; final):\n"
        "These purchases / devices / bookings are ALREADY stored exactly as listed. Do NOT output facts for them, "
        "and do not restate, change or contradict any amount, order id, date, item or place. Still extract everything "
        "else in those records (people, links, plans).\n"
        + "\n".join(lines)
        + "\n\n"
    )


def _same_fact(a: OutFact, b: OutFact) -> bool:
    return (a.text, a.predicate, a.object_text, a.event_at, a.span_start, a.span_end, a.span_record_id) == (
        b.text, b.predicate, b.object_text, b.event_at, b.span_start, b.span_end, b.span_record_id)


def is_prefilled_fact(fact: OutFact, prefilled: list[Prefilled]) -> bool:
    return any(_same_fact(fact, p.fact) for p in prefilled)


def conflicts_with_prefilled(fact: OutFact, prefilled: list[Prefilled]) -> bool:
    """True when an LLM fact touches a pre-filled record and changes or repeats a slot."""
    mine = [p for p in prefilled if p.record_id in set(fact.evidence or [])]
    if not mine or is_prefilled_fact(fact, prefilled):
        return False
    texts = " ".join(t for t in (fact.text, fact.text_orig, fact.object_text) if t)
    allowed_money = {_norm_amount(re.sub(_CUR, "", p.slots["amount"], flags=re.I).strip()) for p in mine if p.slots.get("amount")}
    for amt in money_values(texts):
        if amt not in allowed_money:
            return True
    allowed_ids = {p.slots["order_id"].upper() for p in mine if p.slots.get("order_id")}
    for oid in order_ids(texts):
        if allowed_ids and oid not in allowed_ids:
            return True
    for p in mine:
        if fact.predicate and fact.predicate == p.fact.predicate and p.kind in ("purchase", "booking"):
            return True  # same slot restated (equal or different): code owns it
    return False


def merge_prefilled(output: ExtractionOutput, prefilled: list[Prefilled]) -> None:
    """Put the pre-filled facts (and their merchant entities) first in the attempt output."""
    if not prefilled or output is None:
        return
    have_refs = {e.ref for e in output.entities}
    facts: list[OutFact] = []
    for p in prefilled:
        if any(_same_fact(p.fact, f) for f in output.facts):
            continue
        facts.append(p.fact)
        for fe in p.fact.entities:
            if fe.entity_id not in have_refs:
                have_refs.add(fe.entity_id)
                name = fe.entity_id[4:] if fe.entity_id.startswith("new:") else fe.entity_id
                output.entities.append(OutEntity(ref=fe.entity_id, kind="org", aliases=[name], relation_to_user=None))
    output.facts[:0] = facts


def fold_key(s: str) -> str:  # exported for tests
    return fold_text(s)
