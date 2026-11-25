"""Transactional graph applier with per-owner advisory lock and generation fence (WP-A)."""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from typing import Any

from temporal_memory.core.validator import _gate_fact
from temporal_memory.db.db import Database, fold_text, get_database
from temporal_memory.models import (
    Attempt,
    Entity,
    Job,
    JobBundle,
    OutEntity,
    OutFact,
    Verdict,
)
from temporal_memory.privacy.policy import may_promote as _may_promote
from temporal_memory.core.subject_aliases import aliases_for_text, write_subject_aliases
from temporal_memory.privacy.policy import provenance_for_statement
from temporal_memory.privacy.sensitive import pre_write

_FAMILY_WORD = re.compile(
    r"\b(?:family|mother|mom|mum|father|dad|sister|brother|wife|husband|aunt|uncle|cousin|relative)\b",
    re.I,
)
_CLOSENESS_SKIP_ROOTS = {"family", "health", "faith", "religion", "wellbeing"}
_CLOSENESS_SKIP_CATS = {"health", "religion", "family_third_party"}


_LATE_MONTH = r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
_LATE_SCHEDULE = re.compile(
    rf"\b(?:\d{{1,2}}(?::\d{{2}})?\s*[ap]\.?m\.?|{_LATE_MONTH}\.?\s+\d{{1,2}}|\d{{1,2}}\s+{_LATE_MONTH}|\d{{4}}-\d{{2}}-\d{{2}})\b",
    re.I,
)
_LATE_AMOUNT = r"\d+(?:,\d{3})*(?:\.\d+)?"
_LATE_MONEY = re.compile(
    rf"(?<!\w)(?:(?:aed|usd|dhs|\$)\s*{_LATE_AMOUNT}|{_LATE_AMOUNT}\s*(?:aed|usd|dhs|k))\b", re.I,
)
_LATE_CHANGE_TARGET = r"(?:\s+from\s+(?P<prior>[^;!?]+?))?\s+to\b"
_LATE_SCHEDULE_CHANGE = re.compile(
    r"\b(?:moved|rescheduled|pushed|shifted|postponed|changed)" + _LATE_CHANGE_TARGET
)
_LATE_RENT_EFFECTIVE = re.compile(r"\bwill be\b(?=.*\b(?:starts?|starting|effective|adjustment)\b)")
_LATE_MONEY_CHANGE = re.compile(
    r"\b(?:rais(?:ed|es)|rose|rises|increas(?:ed|es)|drop(?:ped|s)|reduc(?:ed|es)|"
    r"adjust(?:ed|s)|lower(?:ed|s)|chang(?:ed|es))" + _LATE_CHANGE_TARGET
)
_LATE_UNIT = re.compile(r"aed|usd|dhs|k|\$", re.I)
_LATE_PRICE_DESCRIPTION = re.compile(r"\b(?:price|costs?|listed|listing|priced|offered|asking)\b")
_LATE_INTERVIEW_STAGE = re.compile(r"\b(first|second|third|final) (?:\w+ )?interview\b")
_LATE_LABELED_INTERVIEW = re.compile(
    r"\b(first|second|third|final) (?:(\w+) interview|interview with (\w+))\b"
)
_LATE_EVENT = re.compile(r"\b(?:appointment|booking|class|cohort|flight|interview|meeting|reservation|trip)\b")
_LATE_SLOT_NOISE = frozenset(
    "a an the my of for to s is was were got has had been his her their our paid payment original confirmation".split()
)


def _late_value(pattern: re.Pattern[str], raw: str) -> str:
    value = raw.lower().replace(",", "").strip()
    if pattern is _LATE_MONEY:
        unit = _LATE_UNIT.search(value)[0]
        amount = _LATE_UNIT.sub("", value).strip()
        whole, _, decimals = amount.partition(".")
        unit = {"dhs": "aed", "$": "usd"}.get(unit, unit)
        return f"{unit} {int(whole)}.{decimals.rstrip('0')}"

    clock = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?\s*([ap])\.?m\.?", value)
    if clock:
        return f"{int(clock[1])}:{clock[2] or '00'}{clock[3]}m"
    iso_date = re.fullmatch(r"\d{4}-(\d{2})-(\d{2})", value)
    if iso_date:
        return f"{int(iso_date[1])}:{int(iso_date[2])}"
    month = re.search(_LATE_MONTH, value)
    day = re.search(r"\d+", value)
    months = "jan feb mar apr may jun jul aug sep oct nov dec".split()
    return f"{months.index(month[0][:3]) + 1}:{int(day[0])}"


def _late_event_labels(text: str) -> set[tuple[str, tuple[str, ...], tuple[str, ...]]]:
    labels = set()
    for event in _LATE_EVENT.finditer(text):
        prefix = re.sub(rf"\b{_LATE_MONTH}\s+\d{{1,2}}\b", "", text[:event.start()])
        words = [word for word in prefix.split() if word not in _LATE_SLOT_NOISE]
        suffix = text[event.end():].split()
        qualifiers = tuple(word for word in suffix if word not in {"at", "on", "is", "was", "got", "were"})
        labels.add((event[0], tuple(words[-2:]), qualifiers))
    return labels


def _late_rent_label(text: str) -> str:
    prefix = text.split(" rent", 1)[0] if not text.startswith("rent ") and text != "rent" else ""
    prefix = re.split(r"\b(?:paid|receipt of)\s+", prefix)[-1]
    # Strip billing months and owner possessives before comparing a property label.
    prefix = re.sub(rf"\b{_LATE_MONTH}(?: (?:19|20)\d{{2}})?\b", "", prefix)
    prefix = prefix.rsplit(" s ", 1)[-1]
    if prefix.endswith(" s"):
        return ""
    words = [
        word for word in prefix.split()
        if word not in _LATE_SLOT_NOISE and word not in {"one", "two", "three", "bedroom", "flat", "apartment"}
    ]
    return words[-1] if words else ""


def _late_same_slot(
    older: str, newer: str, change: re.Match[str], pattern: re.Pattern[str], same_source: bool,
) -> bool:
    old_values = list(pattern.finditer(older))
    target = newer[change.end():].lstrip()
    if pattern is _LATE_SCHEDULE:
        target = re.sub(r"^(?:start(?:ing)? |(?:mon|tues|wednes|thurs|fri|satur|sun)day,? )+", "", target)
    new_value = pattern.match(target)
    if not old_values or new_value is None:
        return False
    new_normalized = _late_value(pattern, new_value[0])
    old_normalized = {_late_value(pattern, value[0]) for value in old_values}
    if new_normalized in old_normalized:
        return False
    prior = change.groupdict().get("prior")
    if prior is not None and not any(
        _late_value(pattern, value[0]) in old_normalized for value in pattern.finditer(prior)
    ):
        return False

    new_prefix = fold_text(newer[:change.start()])
    if set(new_prefix.split()) & {"not", "never", "might", "could", "would", "may"}:
        return False

    old_prefix = fold_text(older[:old_values[0].start()])
    if pattern is _LATE_SCHEDULE:
        # The event noun and its modifiers must agree, including any booking identifier.
        if _late_event_labels(old_prefix) & _late_event_labels(new_prefix):
            return True
        # Named interview stages can be worded as "first Acme interview" or
        # "first interview with Acme". Require corroborating sender and stage.
        interview = _LATE_LABELED_INTERVIEW.search(new_prefix)
        if not (interview and same_source):
            return False
        party = interview[2] or interview[3]
        old_stage = _LATE_INTERVIEW_STAGE.search(old_prefix)
        return bool(
            old_stage and old_stage[1] == interview[1] and re.search(rf"\b{re.escape(party)}\b", old_prefix)
        )

    old_rent, new_rent = "rent" in old_prefix.split(), "rent" in new_prefix.split()
    if old_rent or new_rent:
        if not (old_rent and new_rent):
            return False
        # Month qualifiers describe the billing period, not a different rental.
        old_label, new_label = _late_rent_label(old_prefix), _late_rent_label(new_prefix)
        if old_label and new_label:
            return old_label == new_label
        return same_source
    if change.re is _LATE_RENT_EFFECTIVE:
        return False

    if not _LATE_PRICE_DESCRIPTION.search(old_prefix):
        return False
    # A displayed price is distinct from another expense involving the same item.
    new_prefix = re.sub(r" s (?=(?:price|cost)$)", " ", new_prefix)
    item = re.search(r"\b([a-z0-9]+(?: [a-z0-9]+)?) (?:price|cost)$", new_prefix)
    if item:
        label = [word for word in item[1].split() if word not in {"a", "an", "the", "my", "its", "asking", "s"}]
        if label and re.search(rf"\b{re.escape(' '.join(label))}\b", old_prefix):
            return True

    old_models, new_models = _late_model_labels(old_prefix), _late_model_labels(new_prefix)
    return len(new_models) == 1 and old_models == new_models


def _late_model_labels(text: str) -> set[tuple[str, str]]:
    year = r"(?:19|20)\d{2}"
    model = r"[a-z][a-z0-9-]*"
    year_first = set(re.findall(rf"\b({year}) ({model})\b", text))
    if year_first:
        return year_first
    return {
        (year_value, model_value)
        for model_value, year_value in re.findall(rf"\b({model}) ({year})\b", text)
        if model_value not in _LATE_SLOT_NOISE
    }


def _late_superseder(conn: Any, owner: str, subject_id: str, fact: OutFact) -> dict | None:
    """Find a newer active fact that explicitly changes the same scheduled or priced slot."""
    if not fact.valid_from or not fact.evidence or not (
        _LATE_SCHEDULE.search(fact.text) or _LATE_MONEY.search(fact.text)
    ):
        return None
    ats = conn.execute(
        "SELECT max(substr(at, 1, 10)) AS d FROM records WHERE owner = %s AND id = ANY(%s)",
        (owner, list(fact.evidence)),
    ).fetchone()
    rec_day = (ats or {}).get("d")
    if not rec_day:
        return None
    rows = conn.execute(
        """
        SELECT f.id, f.valid_from, f.text, EXISTS (
            SELECT 1 FROM fact_evidence AS e
            JOIN records AS newer ON newer.owner = e.owner AND newer.id = e.record_id
            JOIN records AS older ON older.owner = e.owner
                AND older.source = newer.source AND older.author = newer.author
            WHERE e.owner = f.owner AND e.fact_id = f.id AND older.id = ANY(%s)
                AND newer.author <> '' AND newer.erased_at IS NULL AND older.erased_at IS NULL
        ) AS same_source
        FROM facts AS f
        WHERE f.owner = %s AND f.subject_id = %s AND f.status = 'active'
            AND f.erased_at IS NULL AND f.valid_from > %s AND f.valid_from > %s
        ORDER BY f.valid_from DESC
        """,
        (list(fact.evidence), owner, subject_id, fact.valid_from, rec_day),
    ).fetchall()
    for row in rows:
        newer = row["text"].lower()
        for change_pattern, value_pattern in (
            (_LATE_SCHEDULE_CHANGE, _LATE_SCHEDULE),
            (_LATE_MONEY_CHANGE, _LATE_MONEY),
            (_LATE_RENT_EFFECTIVE, _LATE_MONEY),
        ):
            change = change_pattern.search(newer)
            if change and _late_same_slot(fact.text, newer, change, value_pattern, row["same_source"]):
                return {"id": row["id"], "valid_from": row["valid_from"]}
    return None


def _strip_new(ref: str) -> str:
    s = ref.strip()
    return s[4:].strip() if s.startswith("new:") else s


def _matches_forget_rule(
    fact: OutFact,
    rules: list[dict[str, Any]],
    resolved_names_by_ref: dict[str, str],
) -> bool:
    text_l = fact.text.lower()
    orig_l = (fact.text_orig or "").lower()
    subj_l = fact.subject_path.lower()
    for r in rules:
        kind = r["kind"]
        val = str(r["value"])
        val_l = val.lower()
        if kind == "text" and (val_l in text_l or (orig_l and val_l in orig_l)):
            return True
        if kind == "item" and fact.target == val:
            return True
        if kind == "subject" and val_l in subj_l:
            return True
        if kind == "entity":
            for fe in fact.entities:
                if fe.entity_id == val or resolved_names_by_ref.get(fe.entity_id, "").lower() == val_l:
                    return True
    return False


def _family_supported(fact: OutFact) -> bool:
    blob = " ".join([fact.text, fact.text_orig or "", *(fe.role or "" for fe in fact.entities)])
    return bool(_FAMILY_WORD.search(blob))


def _closeness_tier(days: int, facts: int) -> str | None:
    """T1/T2/T3 from frequency across at least two separate days. None below that."""
    if days < 2:
        return None
    if facts >= 5:
        return "T1"
    if facts >= 3:
        return "T2"
    return "T3"


def _eligible_for_closeness(text: str, subject_path: str, relation: str | None) -> bool:
    if relation == "family" or _FAMILY_WORD.search(text or ""):
        return False
    root = (subject_path or "").split("/", 1)[0].lower()
    if root in _CLOSENESS_SKIP_ROOTS:
        return False
    return pre_write(text or "") not in _CLOSENESS_SKIP_CATS


def apply(
    owner: str,
    job: Job,
    attempt: Attempt,
    *,
    db: Database | None = None,
    bundle: JobBundle | None = None,
) -> Verdict:
    """Apply validated extraction output atomically under a per-owner advisory lock."""
    del bundle  # unused; kept to match optional caller kwargs cleanly
    if attempt.output is None:
        return Verdict(ok=False, reasons=["schema_invalid"])

    database = db or get_database()
    out = attempt.output
    applied_fact_ids: list[str] = []
    quarantined: dict[str, int] = {}

    with database.transaction() as conn:
        conn.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (owner,))

        # 1) Generation & erasure fence
        rec_gen: dict[str, int] = {}
        rec_by_id: dict[str, dict[str, Any]] = {}
        if job.input_ref:
            unique_refs = list(dict.fromkeys(job.input_ref))
            rec_rows = conn.execute(
                """
                SELECT id, generation, erased_at, author, text
                FROM records WHERE owner = %s AND id = ANY(%s)
                """,
                (owner, unique_refs),
            ).fetchall()
            if len(rec_rows) != len(unique_refs):
                return Verdict(ok=False, reasons=["fence_stale"])
            for r in rec_rows:
                if r["erased_at"] is not None or int(r["generation"]) > job.input_version:
                    return Verdict(ok=False, reasons=["fence_stale"])
                rec_gen[r["id"]] = int(r["generation"])
                rec_by_id[r["id"]] = dict(r)

        owner_row = conn.execute(
            "SELECT label, display_name, self_aliases FROM owners WHERE id = %s",
            (owner,),
        ).fetchone()
        owner_names = {fold_text(owner), "me", "owner", "self"}
        if owner_row:
            for raw in (owner_row["label"], owner_row["display_name"]):
                folded = fold_text(raw or "")
                if folded:
                    owner_names.add(folded)
            aliases = owner_row["self_aliases"] or []
            if isinstance(aliases, str):
                aliases = json.loads(aliases)
            for raw in aliases:
                folded = fold_text(str(raw))
                if folded:
                    owner_names.add(folded)

        def _author_is_owner(author: str) -> bool:
            return fold_text(author or "") in owner_names

        def _stated(fact: OutFact) -> bool:
            if not fact.evidence:
                return False
            for rid in fact.evidence:
                rec = rec_by_id.get(rid)
                if rec is None or not _author_is_owner(str(rec.get("author") or "")):
                    return False
            return True

        # 2) Active forget rules
        forget_rules = conn.execute(
            "SELECT kind, value FROM forget_rules WHERE owner = %s",
            (owner,),
        ).fetchall()

        # 3) Load existing entities & aliases for resolution
        ent_rows = conn.execute(
            """
            SELECT id, kind, name, status, relation_to_user, provenance, first_seen, last_seen, merged_into
            FROM entities
            WHERE owner = %s AND erased_at IS NULL
            """,
            (owner,),
        ).fetchall()
        entities_by_id: dict[str, dict[str, Any]] = {}
        merged_map: dict[str, str] = {}
        alias_to_eid: dict[str, str] = {}
        for er in ent_rows:
            if er["status"] == "merged" and er["merged_into"]:
                merged_map[er["id"]] = er["merged_into"]
                continue
            entities_by_id[er["id"]] = dict(er)
            nf = fold_text(er["name"])
            if nf:
                alias_to_eid.setdefault(nf, er["id"])

        alias_rows = conn.execute(
            "SELECT entity_id, alias_folded FROM entity_aliases WHERE owner = %s",
            (owner,),
        ).fetchall()
        for ar in alias_rows:
            if ar["alias_folded"] and ar["entity_id"] in entities_by_id:
                alias_to_eid.setdefault(ar["alias_folded"], ar["entity_id"])

        hints: dict[str, OutEntity] = {e.ref.strip(): e for e in out.entities if e.ref}
        ref_to_eid: dict[str, str] = {}

        def _follow_merged(eid: str) -> str:
            seen: set[str] = set()
            cur = eid
            while cur in merged_map and cur not in seen:
                seen.add(cur)
                cur = merged_map[cur]
            return cur

        def _add_alias(eid: str, alias: str) -> None:
            af = fold_text(alias)
            if not af:
                return
            alias_to_eid.setdefault(af, eid)
            conn.execute(
                """
                INSERT INTO entity_aliases (owner, entity_id, alias, alias_folded, source)
                VALUES (%s, %s, %s, %s, 'extractor')
                ON CONFLICT (owner, alias_folded, entity_id) DO NOTHING
                """,
                (owner, eid, alias.strip(), af),
            )

        def _resolve(ref: str, hint: OutEntity | None = None, *, provenance: str = "inferred", create: bool = True) -> str | None:
            raw = (ref or "").strip()
            if not raw:
                return None
            if raw in ref_to_eid:
                return ref_to_eid[raw]
            canon = _follow_merged(raw)
            if canon in entities_by_id:
                ref_to_eid[raw] = canon
                return canon

            name = _strip_new(raw)
            folded = fold_text(name)
            if folded and folded in alias_to_eid:
                eid = alias_to_eid[folded]
                ref_to_eid[raw] = eid
                return eid
            if not create:
                return None

            eid = f"e_{uuid.uuid4().hex[:12]}"
            kind = hint.kind if hint else "person"
            ent_obj = Entity(id=eid, owner=owner, kind=kind, name=name, relation_to_user=None)
            status = "active" if _may_promote(ent_obj, distinct_days=1, user_confirmed=False) else "candidate"
            place_type = hint.place_type if hint and hint.kind == "place" else None
            conn.execute(
                """
                INSERT INTO entities (id, owner, kind, name, status, relation_to_user, provenance, place_type)
                VALUES (%s, %s, %s, %s, %s, NULL, %s, %s)
                """,
                (eid, owner, kind, name, status, provenance, place_type),
            )
            entities_by_id[eid] = {
                "id": eid,
                "kind": kind,
                "name": name,
                "status": status,
                "relation_to_user": None,
                "provenance": provenance,
                "first_seen": None,
                "last_seen": None,
            }
            _add_alias(eid, name)
            if hint:
                for al in hint.aliases:
                    _add_alias(eid, al)
            ref_to_eid[raw] = eid
            return eid

        def _note_relation(eid: str, hint: OutEntity | None, fact: OutFact) -> None:
            if hint is None or not hint.relation_to_user:
                return
            if entities_by_id[eid].get("relation_to_user"):
                return
            if hint.relation_to_user == "family" and not _family_supported(fact):
                return
            conn.execute(
                "UPDATE entities SET relation_to_user = %s WHERE owner = %s AND id = %s",
                (hint.relation_to_user, owner, eid),
            )
            entities_by_id[eid]["relation_to_user"] = hint.relation_to_user

        def _note_provenance(eid: str, provenance: str) -> None:
            if provenance != "user_supplied" or entities_by_id[eid].get("provenance") == "user_supplied":
                return
            conn.execute(
                "UPDATE entities SET provenance = 'user_supplied' WHERE owner = %s AND id = %s",
                (owner, eid),
            )
            entities_by_id[eid]["provenance"] = "user_supplied"

        # 4) Load subjects map & helper to ensure hierarchy exists
        subj_rows = conn.execute(
            "SELECT id, path, status FROM subjects WHERE owner = %s",
            (owner,),
        ).fetchall()
        subj_by_path: dict[str, str] = {r["path"]: r["id"] for r in subj_rows}

        def _ensure_subject(subject_path: str, provenance: str) -> str:
            parts = [p.strip() for p in subject_path.strip("/").split("/") if p.strip()]
            if not parts:
                parts = ["general"]
            parent_id: str | None = None
            cur_id = ""
            for idx, part in enumerate(parts):
                seg_path = "/".join(parts[: idx + 1])
                if seg_path in subj_by_path:
                    cur_id = subj_by_path[seg_path]
                else:
                    cur_id = f"s_{uuid.uuid4().hex[:12]}"
                    kind = "theme" if idx == 0 else "topic"
                    conn.execute(
                        """
                        INSERT INTO subjects (id, owner, parent_id, path, label, kind, status, provenance)
                        VALUES (%s, %s, %s, %s, %s, %s, 'candidate', %s)
                        ON CONFLICT (owner, path) DO NOTHING
                        """,
                        (cur_id, owner, parent_id, seg_path, part, kind, provenance),
                    )
                    row = conn.execute(
                        "SELECT id FROM subjects WHERE owner = %s AND path = %s",
                        (owner, seg_path),
                    ).fetchone()
                    cur_id = row["id"]
                    subj_by_path[seg_path] = cur_id
                parent_id = cur_id
            return cur_id

        # 5) Apply facts (privacy quarantine + forget rules + temporal update/end)
        resolved_names_by_ref = {ref: _strip_new(hint.ref) for ref, hint in hints.items()}
        applied_details: list[tuple[str, OutFact, set[str]]] = []
        touched_eids: set[str] = set()

        for fact in out.facts:
            if _matches_forget_rule(fact, forget_rules, resolved_names_by_ref):
                continue

            sens_cat = fact.sensitive or _gate_fact(fact, attempt.worker_kind)
            if sens_cat:
                if sens_cat == "credential":
                    continue
                conn.execute(
                    """
                    INSERT INTO quarantine (owner, category, record_ids, status)
                    VALUES (%s, %s, %s::jsonb, 'held')
                    """,
                    (owner, sens_cat, json.dumps(list(fact.evidence))),
                )
                quarantined[sens_cat] = quarantined.get(sens_cat, 0) + 1
                continue

            fact_provenance = provenance_for_statement(
                author_is_owner=_stated(fact), stated=bool(fact.stated)
            )
            subject_id = _ensure_subject(fact.subject_path, fact_provenance)
            write_subject_aliases(
                conn, owner, subject_id, aliases_for_text(fact.subject_path, fact.text)
            )
            new_fact_id = f"f_{uuid.uuid4().hex[:12]}"
            text_folded = fold_text(fact.text)
            content_hash = hashlib.sha256(
                f"{subject_id}|{text_folded}".encode("utf-8")
            ).hexdigest()

            status = "active"
            valid_to: str | None = None
            superseded_by: str | None = None

            if fact.op in ("update", "end") and fact.target:
                tgt = conn.execute(
                    """
                    SELECT id, status, valid_from
                    FROM facts
                    WHERE owner = %s AND id = %s AND erased_at IS NULL
                    """,
                    (owner, fact.target),
                ).fetchone()
                if tgt and tgt["status"] in ("active", "superseded", "ended"):
                    older = bool(fact.valid_from and tgt["valid_from"] and fact.valid_from < tgt["valid_from"])
                    if older or tgt["status"] != "active":
                        # Older evidence never overwrites newer. A late arrival
                        # against an already superseded or ended target is history.
                        status = "history"
                        superseded_by = tgt["id"]
                        valid_to = tgt["valid_from"] if older else fact.valid_from
                    else:
                        new_tgt_status = "superseded" if fact.op == "update" else "ended"
                        conn.execute(
                            """
                            UPDATE facts
                            SET status = %s, superseded_by = %s, valid_to = %s
                            WHERE owner = %s AND id = %s
                            """,
                            (new_tgt_status, new_fact_id, fact.valid_from, owner, tgt["id"]),
                        )

            if fact.op == "new" and status == "active":
                late = _late_superseder(conn, owner, subject_id, fact)
                if late:
                    # Older evidence never overwrites newer: a late restatement is history, back-dated.
                    status = "history"
                    superseded_by = late["id"]
                    valid_to = late["valid_from"]

            if fact.op == "end" and status == "active":
                # E9b: the fact that reports a cancellation/stop is itself an ended state (valid_to = the end date).
                status = "ended"
                valid_to = valid_to or fact.valid_from

            conn.execute(
                """
                INSERT INTO facts (
                    id, owner, text, text_orig, text_folded, subject_id,
                    valid_from, valid_to, status, superseded_by, provenance,
                    job_id, attempt_id, worker_id, model, prompt_version, content_hash,
                    reason_text, reason_record_id, reason_start, reason_end,
                    predicate, object_text, polarity, modality, event_at,
                    span_record_id, span_start, span_end
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    new_fact_id,
                    owner,
                    fact.text,
                    fact.text_orig,
                    text_folded,
                    subject_id,
                    fact.valid_from,
                    valid_to,
                    status,
                    superseded_by,
                    fact_provenance,
                    job.id,
                    f"{job.id}:{attempt.attempt_no}",
                    attempt.worker_id,
                    attempt.model,
                    attempt.prompt_version,
                    content_hash,
                    fact.reason_text,
                    fact.reason_record_id,
                    fact.reason_start,
                    fact.reason_end,
                    fact.predicate,
                    fact.object_text,
                    fact.polarity,
                    fact.modality,
                    fact.event_at,
                    fact.span_record_id,
                    fact.span_start,
                    fact.span_end,
                ),
            )
            applied_fact_ids.append(new_fact_id)
            resolved_eids: set[str] = set()

            for fe in fact.entities:
                hint = hints.get(fe.entity_id) or hints.get(fe.entity_id.strip())
                eid = _resolve(fe.entity_id, hint, provenance=fact_provenance)
                if not eid:
                    continue
                resolved_eids.add(eid)
                touched_eids.add(eid)
                if hint and hint.place_type:
                    conn.execute(
                        """
                        UPDATE entities
                        SET place_type = COALESCE(place_type, %s)
                        WHERE owner = %s AND id = %s
                        """,
                        (hint.place_type, owner, eid),
                    )
                _note_relation(eid, hint, fact)
                _note_provenance(eid, fact_provenance)
                for al in (hint.aliases if hint else []):
                    _add_alias(eid, al)
                conn.execute(
                    """
                    INSERT INTO fact_entities (owner, fact_id, entity_id, role)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (owner, fact_id, entity_id)
                    DO UPDATE SET role = COALESCE(EXCLUDED.role, fact_entities.role)
                    """,
                    (owner, new_fact_id, eid, fe.role),
                )
                if fact.valid_from:
                    ent_row = entities_by_id[eid]
                    first_s = ent_row["first_seen"]
                    last_s = ent_row["last_seen"]
                    new_first = fact.valid_from if not first_s or fact.valid_from < first_s else first_s
                    new_last = fact.valid_from if not last_s or fact.valid_from > last_s else last_s
                    days_rows = conn.execute(
                        """
                        SELECT COUNT(DISTINCT substr(f.valid_from, 1, 10))::int AS dcnt
                        FROM facts f
                        JOIN fact_entities fe ON fe.owner = f.owner AND fe.fact_id = f.id
                        WHERE f.owner = %s AND fe.entity_id = %s AND f.erased_at IS NULL AND f.valid_from <> ''
                        """,
                        (owner, eid),
                    ).fetchone()
                    dcnt = int(days_rows["dcnt"]) if days_rows else 1
                    cur_status = ent_row["status"]
                    if cur_status == "candidate":
                        ent_obj = Entity(
                            id=eid,
                            owner=owner,
                            kind=ent_row["kind"],
                            name=ent_row["name"],
                            relation_to_user=ent_row["relation_to_user"],
                        )
                        if _may_promote(ent_obj, distinct_days=dcnt, user_confirmed=False):
                            cur_status = "active"
                    if new_first != first_s or new_last != last_s or cur_status != ent_row["status"] or dcnt > 1:
                        conn.execute(
                            """
                            UPDATE entities
                            SET first_seen = %s, last_seen = %s, status = %s, distinct_days = GREATEST(distinct_days, %s)
                            WHERE owner = %s AND id = %s
                            """,
                            (new_first, new_last, cur_status, dcnt, owner, eid),
                        )
                        ent_row["first_seen"] = new_first
                        ent_row["last_seen"] = new_last
                        ent_row["status"] = cur_status

            for rid in dict.fromkeys(fact.evidence):
                conn.execute(
                    """
                    INSERT INTO fact_evidence (owner, fact_id, record_id, record_generation)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (owner, fact_id, record_id) DO NOTHING
                    """,
                    (owner, new_fact_id, rid, rec_gen.get(rid, job.input_version)),
                )
            applied_details.append((new_fact_id, fact, resolved_eids))

        # 6) Links cite their own approved facts. Never the day's first fact, never null.
        link_evidence_ids = {row[0] for row in applied_details}
        for lnk in out.links:
            src_id = _resolve(lnk.src, hints.get(lnk.src), create=False)
            dst_id = _resolve(lnk.dst, hints.get(lnk.dst), create=False)
            if not src_id or not dst_id or src_id == dst_id:
                continue
            if src_id not in touched_eids or dst_id not in touched_eids:
                continue
            link_records = set(lnk.evidence or [])
            by_overlap = [
                fact_id for fact_id, fact, _eids in applied_details
                if link_records and link_records & set(fact.evidence)
            ]
            by_mention = [
                fact_id for fact_id, _fact, eids in applied_details
                if src_id in eids and dst_id in eids
            ]
            support = [fid for fid in (by_overlap or by_mention) if fid in link_evidence_ids]
            if not support:
                continue
            link_id = f"l_{uuid.uuid4().hex[:12]}"
            conn.execute(
                """
                INSERT INTO links (id, owner, src, rel, dst, valid_from, evidence_fact_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (link_id, owner, src_id, lnk.rel, dst_id, lnk.valid_from, support[0]),
            )
            for fid in support:
                conn.execute(
                    """
                    INSERT INTO link_evidence (owner, link_id, fact_id)
                    VALUES (%s, %s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    (owner, link_id, fid),
                )

        for eid in touched_eids:
            ent_row = entities_by_id.get(eid)
            if ent_row is None or ent_row.get("relation_to_user") == "family":
                continue
            rows = conn.execute(
                """
                SELECT f.id, f.text, f.valid_from, COALESCE(s.path, '') AS path
                FROM facts f
                JOIN fact_entities fe ON fe.owner = f.owner AND fe.fact_id = f.id
                LEFT JOIN subjects s ON s.owner = f.owner AND s.id = f.subject_id
                WHERE f.owner = %s AND fe.entity_id = %s AND f.erased_at IS NULL
                  AND f.status <> 'history'
                """,
                (owner, eid),
            ).fetchall()
            kept = [
                row for row in rows
                if _eligible_for_closeness(row["text"], row["path"], ent_row.get("relation_to_user"))
            ]
            days = {str(row["valid_from"])[:10] for row in kept if row["valid_from"]}
            suggested = _closeness_tier(len(days), len(kept))
            if suggested is None:
                continue
            conn.execute(
                """
                UPDATE entities
                SET closeness_suggested = %s,
                    closeness_suggested_evidence = %s::jsonb
                WHERE owner = %s AND id = %s AND closeness_tier IS NULL
                """,
                (suggested, json.dumps([row["id"] for row in kept]), owner, eid),
            )

        # 7) Recompute derived entity_subjects & subject fact_count from visible_facts
        conn.execute("DELETE FROM entity_subjects WHERE owner = %s", (owner,))
        conn.execute(
            """
            INSERT INTO entity_subjects (
                owner, entity_id, subject_id, role, weight, fact_count, first_seen, last_seen
            )
            SELECT
                vf.owner,
                fe.entity_id,
                vf.subject_id,
                COALESCE(fe.role, '') AS role,
                SUM(CASE WHEN vf.status = 'active' THEN 1.0 ELSE 0.3 END) AS weight,
                COUNT(*)::int AS fact_count,
                MIN(vf.valid_from) AS first_seen,
                MAX(vf.valid_from) AS last_seen
            FROM visible_facts vf
            JOIN fact_entities fe ON fe.owner = vf.owner AND fe.fact_id = vf.id
            WHERE vf.owner = %s
            GROUP BY vf.owner, fe.entity_id, vf.subject_id, COALESCE(fe.role, '')
            """,
            (owner,),
        )
        conn.execute(
            """
            UPDATE subjects s
            SET fact_count = COALESCE((
                SELECT COUNT(*)::int
                FROM visible_facts vf
                WHERE vf.owner = s.owner AND vf.subject_id = s.id
            ), 0)
            WHERE s.owner = %s
            """,
            (owner,),
        )

        if getattr(out, "new_terms", None):
            from temporal_memory.vocab.proposals import apply_new_terms

            apply_new_terms(conn, owner, out.new_terms, set(job.input_ref or []))

        # 8) Bump facts_version
        conn.execute(
            "UPDATE owners SET facts_version = facts_version + 1 WHERE id = %s",
            (owner,),
        )

    if applied_fact_ids:
        # E9b: live facts need a vector for the semantic channel; best effort, never fails the apply.
        from temporal_memory.core.embed import ensure_embeddings

        ensure_embeddings(database, owner, once_per_version=False)

    return Verdict(
        ok=True,
        applied_fact_ids=applied_fact_ids,
        quarantined=quarantined,
    )
