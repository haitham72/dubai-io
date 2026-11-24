"""Durable live session grouping on record metadata and the existing job outbox."""
from __future__ import annotations

from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
import json
from types import SimpleNamespace

from fastapi import HTTPException

from temporal_memory.config import get_settings
from temporal_memory.core.bridge_store import ingest_records
from temporal_memory.db.db import fold_text
from temporal_memory.live.context import invalidate_alias_cache
from temporal_memory.live.topics import PostgresTopicMentions, match_topics, topic_fact
from temporal_memory.live.triples import (
    extract_triples, fact_from_triple, feature_id, quarantine_category, save_postgres_triple,
)
from temporal_memory.models import Entity, Job, Owner, Record
from temporal_memory.queue.jobs import PostgresJobs


def live_source(source: str) -> bool:
    return source.split(":", 1)[0] in {"live", "chat"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _stamp(at: datetime) -> str:
    return at.isoformat(timespec="microseconds")


def _owner_lock(conn, owner: str) -> None:
    conn.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (owner,))


def _implicit(conn, owner: str, now: datetime, *, closing: bool = False) -> str:
    cutoff = _stamp(now - timedelta(minutes=get_settings().session_idle_minutes))
    row = conn.execute(
        """SELECT meta->>'u2_session' AS session_id FROM records
           WHERE owner=%s AND erased_at IS NULL AND meta->>'u2_implicit'='true'
             AND (%s OR (NOT meta ? 'u2_job' AND meta->>'u2_received_at'>%s))
           ORDER BY meta->>'u2_received_at' DESC LIMIT 1""",
        (owner, closing, cutoff),
    ).fetchone()
    return row["session_id"] if row else feature_id("session", owner, _stamp(now))


def _flush(conn, jobs, owner: str, key: str, cutoff: str | None = None) -> str | None:
    rows = conn.execute(
        """SELECT id,at,erased_at,meta->>'u2_received_at' AS received_at,meta->>'u2_job' AS job
           FROM records WHERE owner=%s AND meta->>'u2_session'=%s ORDER BY id FOR UPDATE""",
        (owner, key),
    ).fetchall()
    existing = next((row["job"] for row in rows if row["job"]), None)
    if existing:
        return existing if cutoff is None else None
    surviving = [row for row in rows if row["erased_at"] is None]
    if not surviving or (cutoff is not None and any(row["received_at"] > cutoff for row in surviving)):
        return None
    day = min(row["at"] for row in surviving)[:10] or None
    job = jobs._enqueue(conn, owner, "extract.session", [row["id"] for row in surviving],
                        1, "owner-device", day, False)
    conn.execute(
        """UPDATE records SET meta=meta || jsonb_build_object('u2_job',%s::text)
           WHERE owner=%s AND meta->>'u2_session'=%s""",
        (job.id, owner, key),
    )
    return job.id


def flush_idle_sessions(db, *, now: datetime | None = None) -> int:
    """Close due sessions on the existing reconcile beat; recheck inside the owner lock."""
    cutoff = _stamp((now or _now()) - timedelta(minutes=get_settings().session_idle_minutes))
    with db.connection() as conn:
        due = conn.execute(
            """SELECT owner,meta->>'u2_session' AS session_id FROM records
               WHERE erased_at IS NULL AND meta ? 'u2_session' AND NOT meta ? 'u2_job'
               GROUP BY owner,meta->>'u2_session'
               HAVING MAX(meta->>'u2_received_at')<=%s
               ORDER BY MAX(meta->>'u2_received_at'),owner,meta->>'u2_session' LIMIT 100""",
            (cutoff,),
        ).fetchall()
    jobs = PostgresJobs(db)
    count = 0
    for row in due:
        with db.transaction() as conn:
            _owner_lock(conn, row["owner"])
            if _flush(conn, jobs, row["owner"], row["session_id"], cutoff):
                count += 1
    return count


def _split_records(body):
    safe = []
    held = []
    for record in body.records:
        category = quarantine_category(record.text) if live_source(record.source) else None
        if category:
            held.append((record.id, category))
        else:
            safe.append(record)
    return safe, held


def _client_key(record, request_key: str | None) -> str | None:
    return record.meta.session_id or request_key


def ingest_live(store, owner_id: str, body, *, now: datetime | None = None):
    """Insert records, checked hot facts, topic evidence and close receipts atomically."""
    now = now or _now()
    safe, held = _split_records(body)
    jobs = PostgresJobs(store.db, store=store)
    with store.db.transaction() as conn:
        _owner_lock(conn, owner_id)
        owner_row = conn.execute(
            "SELECT id,label,kind,display_name FROM owners WHERE id=%s", (owner_id,),
        ).fetchone()
        if owner_row is None:
            raise HTTPException(status_code=404, detail="owner not found")
        owner = Owner(**owner_row)
        needs_implicit = body.close_session and not body.session_id or any(
            live_source(record.source) and not _client_key(record, body.session_id) for record in safe
        )
        implicit = _implicit(conn, owner_id, now, closing=body.close_session and not body.records) if needs_implicit else None
        records_body = body.model_copy(update={"records": safe, "enqueue": "none"})
        # Reuse the existing bridge upsert, with all U2 derived writes on its transaction.
        bound_store = SimpleNamespace(db=SimpleNamespace(transaction=lambda: nullcontext(conn)))
        _check_record_revisions(conn, owner_id, safe)
        result = ingest_records(bound_store, owner_id, records_body)
        result["quarantined"] += _quarantine(conn, owner_id, held)

        legacy_ids = []
        keys = set()
        topics = PostgresTopicMentions(conn)
        for incoming, record_id in zip(safe, result["record_ids"], strict=True):
            if not live_source(incoming.source):
                legacy_ids.append(record_id)
                continue
            if incoming.author != owner_id:
                continue
            client_key = _client_key(incoming, body.session_id)
            session_id = f"client:{client_key}" if client_key else implicit
            record_row = conn.execute(
                """SELECT id,owner,source,at,author,text,generation,meta FROM records
                   WHERE owner=%s AND id=%s AND erased_at IS NULL AND author=%s FOR UPDATE""",
                (owner_id, record_id, owner_id),
            ).fetchone()
            if not record_row or not live_source(record_row["source"]):
                continue
            meta = record_row.pop("meta")
            existing_key = meta.get("u2_session")
            if existing_key:
                if client_key and existing_key != session_id:
                    raise HTTPException(status_code=409, detail="record belongs to a different session")
                keys.add(existing_key)
                continue
            if not session_id:
                raise RuntimeError("No session was selected for this record")
            saved = conn.execute(
                """UPDATE records r SET meta=r.meta || jsonb_build_object(
                       'u2_session',%(session)s::text,'u2_received_at',%(received)s::text,
                       'u2_implicit',%(implicit)s::boolean)
                   WHERE r.owner=%(owner)s AND r.id=%(id)s AND NOT EXISTS (
                     SELECT 1 FROM records closed WHERE closed.owner=r.owner
                       AND closed.meta->>'u2_session'=%(session)s AND closed.meta ? 'u2_job')
                   RETURNING id""",
                {"session": session_id, "received": _stamp(now), "implicit": not client_key,
                 "owner": owner_id, "id": record_id},
            ).fetchone()
            if saved is None:
                raise HTTPException(status_code=409, detail="session closed")
            keys.add(session_id)
            record = Record(**record_row)
            for triple in extract_triples(record.text):
                fact_id = save_postgres_triple(conn, owner, record, triple)
                if fact_id:
                    result["fact_ids"].append(fact_id)
            result["fact_ids"].extend(topics.observe(owner_id, record_id, session_id, record.text))

        if legacy_ids:
            result["job_id"] = jobs._enqueue(conn, owner_id, "extract.live", list(dict.fromkeys(legacy_ids)),
                                             0, "internal", safe[0].at[:10], False).id
        if body.close_session:
            if body.session_id:
                keys = {f"client:{body.session_id}"}
            for key in sorted(keys or ({implicit} if implicit else set())):
                result["job_id"] = _flush(conn, jobs, owner_id, key) or result["job_id"]
        if result["fact_ids"]:
            conn.execute("UPDATE owners SET facts_version=facts_version+1,alias_version=alias_version+1 WHERE id=%s",
                         (owner_id,))
    if result["fact_ids"]:
        invalidate_alias_cache(owner_id)
    return result


def _check_record_revisions(conn, owner: str, records) -> None:
    """Never change an already attributed record underneath its cited offsets."""
    rows = {
        row["id"]: row for row in conn.execute(
            """SELECT id,source,at,author,text FROM records WHERE owner=%s
               AND id=ANY(%s) AND meta ? 'u2_session' FOR UPDATE""",
            (owner, [record.id for record in records]),
        ).fetchall()
    }
    for record in records:
        existing = rows.get(record.id)
        if existing and any(existing[field] != getattr(record, field) for field in ("source", "at", "author", "text")):
            raise HTTPException(status_code=409, detail="live evidence is immutable")


def _quarantine(conn, owner: str, held) -> int:
    count = 0
    for record_id, category in held:
        ids = json.dumps([record_id])
        result = conn.execute(
            """INSERT INTO quarantine (owner,category,record_ids)
               SELECT %s,%s,%s::jsonb WHERE NOT EXISTS (
                  SELECT 1 FROM quarantine WHERE owner=%s AND category=%s AND record_ids @> %s::jsonb)""",
            (owner, category, ids, owner, category, ids),
        )
        count += result.rowcount
    return count


def ingest_fake_live(store, owner: str, body, legacy_ingest, *, now: datetime | None = None):
    """Mirrors the live bridge behavior for its existing in-memory test adapter."""
    now = now or _now()
    safe, held = _split_records(body)
    state = store.__dict__.setdefault("_u2_sessions", {}).setdefault(owner, {})
    accepted = store.__dict__.setdefault("_u2_records", {}).setdefault(owner, {})
    seen_held = store.__dict__.setdefault("_u2_quarantine", set())
    implicit = next((key for key, entry in reversed(list(state.items())) if not key.startswith("client:")
                                          and ((body.close_session and not body.records)
                          or (not entry["job"] and now-entry["at"] < timedelta(minutes=get_settings().session_idle_minutes)))),
                    feature_id("session", owner, _stamp(now)))
    for record in safe:
        if live_source(record.source) and record.author == owner:
            client_key = _client_key(record, body.session_id)
            key = f"client:{client_key}" if client_key else implicit
            if record.id in accepted:
                old = store.records[owner][record.id]
                if any(getattr(record, field) != getattr(old, field) for field in ("source", "at", "author", "text")):
                    raise HTTPException(status_code=409, detail="live evidence is immutable")
                if client_key and accepted[record.id] != key:
                    raise HTTPException(status_code=409, detail="record belongs to a different session")
            elif state.get(key, {}).get("job"):
                raise HTTPException(status_code=409, detail="session closed")
    result = legacy_ingest(owner, body.model_copy(update={"records": safe, "enqueue": "none"}), store)
    for rid, category in held:
        marker = (owner, rid, category)
        if marker not in seen_held:
            seen_held.add(marker)
            bucket = store.quarantine.setdefault(owner, {})
            bucket[category] = bucket.get(category, 0) + 1
            result["quarantined"] += 1

    keys = set()
    mentions = store.__dict__.setdefault("_u2_mentions", {}).setdefault(owner, {})
    for record in safe:
        if not live_source(record.source) or record.author != owner:
            continue
        client_key = _client_key(record, body.session_id)
        key = accepted.get(record.id) or (f"client:{client_key}" if client_key else implicit)
        keys.add(key)
        if record.id in accepted:
            continue
        accepted[record.id] = key
        entry = state.setdefault(key, {"records": [], "at": now, "job": None})
        entry["at"] = now
        entry["records"].append(record.id)
        owner_obj = store.get_owner(owner) or Owner(owner, owner)
        for triple in extract_triples(record.text):
            fact = fact_from_triple(owner_obj, store.records[owner][record.id], triple, "events")
            fact.actor_entity_id = feature_id("self", owner)
            if triple.place_type and fact.status == "active":
                fact.object_entity_id = feature_id("place", owner, fold_text(triple.object_text))
                if all(e.id != fact.object_entity_id for e in store.list_entities(owner)):
                    store.entities[owner].append(Entity(fact.object_entity_id, owner, "place", triple.object_text,
                                                        status="active", provenance="user_supplied", place_type=triple.place_type))
            store.facts[owner].append(fact)
            result["fact_ids"].append(fact.id)
        subjects = store.list_subjects(owner)
        aliases = [(entity.id, alias) for entity in store.list_entities(owner) if entity.kind != "person"
                   and entity.status == "active" for alias in (entity.name, *entity.aliases)]
        matched = match_topics(record.text, [vars(subject) for subject in subjects], aliases,
                               [(es.entity_id, es.subject_id) for es in store.list_entity_subjects(owner)])
        for subject in subjects:
            if subject.id not in matched:
                continue
            bucket = mentions.setdefault(subject.id, {})
            bucket.setdefault(key, []).append(record.id)
            store.record_topic_mention(owner, subject.id, key)
            evidence = [min(r.id for r in records) for ids in bucket.values()
                        if (records := store.get_records(owner, ids))]
            if len(evidence) >= 2:
                fact = topic_fact(owner, subject.id, subject.label, evidence[:2], record.at)
                if all(prior.id != fact.id for prior in store.facts[owner]):
                    store.facts[owner].append(fact)
                    result["fact_ids"].append(fact.id)
    legacy_ids = [record.id for record in safe if not live_source(record.source)]
    if legacy_ids:
        result["job_id"] = _fake_job(store, owner, "extract.live", legacy_ids)
    if body.close_session:
        if body.session_id:
            keys = {f"client:{body.session_id}"}
        for key in sorted(keys or {implicit}):
            entry = state.get(key)
            if entry and not entry["job"]:
                entry["job"] = _fake_job(store, owner, "extract.session", entry["records"])
            if entry:
                result["job_id"] = entry["job"]
    if result["fact_ids"]:
        store._facts_ver[owner] += 1
        invalidate_alias_cache(owner)
    return result


def _fake_job(store, owner, kind, ids):
    job_id = feature_id("job", owner, kind, *sorted(ids))
    if all(job.id != job_id for job in store.jobs):
        store.jobs.append(Job(job_id, owner, kind, 1 if kind == "extract.session" else 0,
                              "owner-device" if kind == "extract.session" else "internal",
                              ids.copy(), store.generations[owner], "", "extract@3"))
    return job_id


def remove_duplicate_triples(db, bundle, attempt) -> None:
    """Keep follow-up facts; drop new assertions already captured from the same record."""
    if not attempt.output or not attempt.output.facts:
        return
    with db.connection() as conn:
        triples = conn.execute(
            """SELECT span_record_id,predicate,object_text,text FROM facts
               WHERE owner=%s AND span_record_id=ANY(%s) AND predicate IS NOT NULL""",
            (bundle.job.owner, bundle.job.input_ref),
        ).fetchall()
    if not triples:
        return

    def duplicate(fact) -> bool:
        if fact.op != "new":
            return False
        for triple in triples:
            if triple["span_record_id"] not in fact.evidence:
                continue
            if fact.predicate and fact.object_text:
                if fact.predicate == triple["predicate"] and fold_text(fact.object_text) == fold_text(triple["object_text"]):
                    return True
            for text in (fact.text, fact.text_orig):
                if not text:
                    continue
                if fold_text(text) == fold_text(triple["text"]):
                    return True
                # The legacy extractor emits third-person English without triple fields.
                if fact.predicate is None and _repeats_plain_assertion(text, triple):
                    return True
        return False

    attempt.output.facts[:] = [fact for fact in attempt.output.facts if not duplicate(fact)]


def _repeats_plain_assertion(text, triple) -> bool:
    import re

    folded = fold_text(text)
    action = {
        "buys": r"bought|purchased|ordered|picked up",
        "visits": r"visited|went to|had dinner at|had lunch at|ate at",
        "likes": r"likes?|loves?|prefers?",
        "dislikes": r"dislikes?|hates?",
        "wants": r"wants?(?: to (?:buy|order))?",
        "moves_to": r"moved to|relocated to",
        "works_at": r"works? at|started working at",
        "joins": r"joined",
        "other": r"booked|reserved",
    }.get(triple["predicate"])
    if not action:
        return False
    value = re.escape(fold_text(triple["object_text"]))
    return bool(re.fullmatch(
        rf"(?:[\w]+(?: [\w]+){{0,4}} )?(?:{action}) (?:an? |the )?{value}"
        r"(?: yesterday| today| last week| on [\w]+| for [\w]+)?",
        folded,
    ))
