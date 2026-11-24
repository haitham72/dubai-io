"""CR-TM-1..4 HTTP bridge. Auth matches vault.require_owner_access."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from temporal_memory.api.vault import AuthContext, get_store, require_owner_access
from temporal_memory.core.daytime import local_day
from temporal_memory.core.extract import PROMPT_VERSION
from temporal_memory.live.context import context_pack, invalidate_alias_cache
from temporal_memory.models import Fact, GraphStore, Job, Record
from temporal_memory.privacy.sensitive import pre_write

EnqueueKind = Literal["extract.live", "extract.day", "none"]
ResolveAction = Literal["confirm", "edit", "reject", "supersede"]


class RecordMeta(BaseModel):
    session_id: str | None = Field(default=None, min_length=1, max_length=128)


class RecordIn(BaseModel):
    id: str
    source: str
    at: str
    author: str
    text: str
    meta: RecordMeta = Field(default_factory=RecordMeta)


class DirectFactIn(BaseModel):
    text: str
    subject_id: str = ""
    subject_path: str = ""
    valid_from: str = ""
    evidence: list[str] = Field(default_factory=list)
    provenance: str = "user_supplied"
    status: str = "active"
    text_orig: str | None = None

    def resolved_subject(self) -> str:
        return self.subject_id or self.subject_path or "general/interests"


class RecordsIn(BaseModel):
    records: list[RecordIn] = Field(default_factory=list)
    enqueue: EnqueueKind = "extract.live"
    direct_fact: DirectFactIn | None = None
    session_id: str | None = Field(default=None, min_length=1, max_length=128)
    close_session: bool = False


class ForgetIn(BaseModel):
    record_ids: list[str] = Field(default_factory=list)
    fact_id: str | None = None
    idempotency_key: str | None = None


class ResolveIn(BaseModel):
    action: ResolveAction
    new_text: str | None = None
    valid_from: str | None = None
    evidence_record_id: str | None = None


class ContextIn(BaseModel):
    text: str
    max_tokens: int = 1500


router = APIRouter(prefix="/v1/owners/{owner}", tags=["bridge"])
_FORGET_IDEMPOTENCY: dict[tuple[str, str], dict[str, Any]] = {}


def _hash(source: str, at: str, text: str) -> str:
    return hashlib.sha256(f"{source}|{at}|{text}".encode()).hexdigest()


def _hashes(store: Any) -> dict[str, dict[str, str]]:
    found = getattr(store, "content_hashes", None)
    if found is None:
        found = defaultdict(dict)
        store.content_hashes = found
    return found


def _rules(store: Any) -> dict[str, set[str]]:
    found = getattr(store, "forget_rule_values", None)
    if found is None:
        found = defaultdict(set)
        store.forget_rule_values = found
    return found


def _bump_facts(store: Any, owner: str) -> int:
    versions = getattr(store, "_facts_ver", None)
    if isinstance(versions, dict):
        versions[owner] = int(versions.get(owner, 0)) + 1
        return versions[owner]
    current = int(store.facts_version(owner)) + 1
    return current


@router.post("/records")
def upsert_records(
    owner: str,
    body: RecordsIn,
    auth: AuthContext = Depends(require_owner_access),
    store: GraphStore = Depends(get_store),
) -> dict[str, Any]:
    from temporal_memory.core.bridge_store import _postgres, ingest_records
    from temporal_memory.queue.session import ingest_fake_live, ingest_live, live_source

    owner_chat = auth.role == "owner-device" and auth.owner == owner
    session_request = body.close_session or any(live_source(record.source) for record in body.records)
    if owner_chat and body.enqueue == "extract.live" and session_request:
        if _postgres(store):
            return ingest_live(store, owner, body)
        return ingest_fake_live(store, owner, body, _ingest_fake_records)
    if _postgres(store):
        return ingest_records(store, owner, body)
    return _ingest_fake_records(owner, body, store)


def _ingest_fake_records(owner: str, body: RecordsIn, store: GraphStore) -> dict[str, Any]:
    rules = _rules(store).get(owner, set())
    hashes = _hashes(store)
    record_ids: list[str] = []
    for record in body.records:
        digest = _hash(record.source, record.at, record.text)
        if record.id in rules or digest in rules:
            raise HTTPException(status_code=409, detail="forget_rule")
        if pre_write(record.text) == "credential":
            raise HTTPException(status_code=400, detail="credential")
        store.records.setdefault(owner, {})[record.id] = Record(  # type: ignore[attr-defined]
            id=record.id, owner=owner, source=record.source, at=record.at,
            author=record.author, text=record.text,
        )
        hashes[owner][record.id] = digest
        record_ids.append(record.id)

    quarantined = 0
    fact_ids: list[str] = []
    if body.direct_fact is not None:
        fact = body.direct_fact
        if not fact.evidence:
            raise HTTPException(status_code=422, detail="direct_fact.evidence must be non-empty")
        known = set(record_ids) | set(getattr(store, "records", {}).get(owner, {}))
        if any(rid not in known for rid in fact.evidence):
            raise HTTPException(status_code=422, detail="direct_fact.evidence references an unknown record")
        gate = pre_write(fact.text)
        if gate == "credential":
            raise HTTPException(status_code=400, detail="credential")
        if gate:
            quarantine = getattr(store, "quarantine", None)
            if quarantine is not None:
                bucket = quarantine.setdefault(owner, {})
                bucket[gate] = int(bucket.get(gate, 0)) + 1
            quarantined = 1
        else:
            provenance = fact.provenance or "user_supplied"
            if provenance not in ("user_supplied", "inferred", "provider_confirmed", "demo_fixture"):
                raise HTTPException(status_code=422, detail="provenance is not allowlisted")
            fid = f"df-{uuid.uuid4().hex[:8]}"
            store.facts.setdefault(owner, []).append(Fact(  # type: ignore[attr-defined]
                id=fid, owner=owner, text=fact.text, subject_id=fact.resolved_subject(),
                valid_from=fact.valid_from, evidence=list(fact.evidence),
                status="active", provenance=provenance,  # type: ignore[arg-type]
            ))
            fact_ids.append(fid)
            _bump_facts(store, owner)

    job_id = None
    if body.enqueue != "none" and record_ids:
        job_id = f"job-{uuid.uuid4().hex[:8]}"
        jobs = getattr(store, "jobs", None)
        if jobs is not None:
            owner_obj = store.get_owner(owner) if hasattr(store, "get_owner") else None
            owner_tz = getattr(owner_obj, "timezone", None) or "Asia/Dubai"
            jobs.append(Job(
                id=job_id, owner=owner, kind=body.enqueue, priority=0 if body.enqueue == "extract.live" else 1,
                pool="internal", input_ref=list(record_ids), input_version=int(getattr(store, "generations", {}).get(owner, 0)),
                context_hash=_hash("job", job_id, ",".join(record_ids)), prompt_version=PROMPT_VERSION,
                day=local_day(body.records[0].at, owner_tz), state="queued",
            ))
    return {"ok": True, "record_ids": record_ids, "job_id": job_id, "fact_ids": fact_ids, "quarantined": quarantined}


@router.post("/forget")
def forget_owner(
    owner: str,
    body: ForgetIn,
    _: AuthContext = Depends(require_owner_access),
    store: GraphStore = Depends(get_store),
) -> dict[str, Any]:
    from temporal_memory.core.bridge_store import _postgres, forget as pg_forget

    if _postgres(store):
        return pg_forget(store, owner, body.record_ids, body.fact_id, body.idempotency_key)
    if body.idempotency_key:
        cached = _FORGET_IDEMPOTENCY.get((owner, body.idempotency_key))
        if cached is not None:
            return cached
    result = {"ok": True, "generation": int(getattr(store, "generations", {}).get(owner, 0)),
              "records": 0, "facts_erased": 0, "facts_trimmed": 0,
              "entity_subjects_recomputed": 0, "jobs_requeued": 0, "jobs_enqueued": 0}
    if body.record_ids and hasattr(store, "forget_source"):
        raw = store.forget_source(owner, body.record_ids)
        result.update({
            "generation": raw.get("generation") or result["generation"],
            "records": raw.get("records", raw.get("records_forgotten", 0)),
            "facts_erased": raw.get("facts_erased", 0),
            "facts_trimmed": raw.get("facts_trimmed", 0),
            "entity_subjects_recomputed": raw.get("entity_subjects_recomputed", 0),
            "jobs_requeued": raw.get("jobs_requeued", 0),
            "jobs_enqueued": raw.get("jobs_enqueued", 0),
        })
    if body.fact_id and hasattr(store, "forget_fact"):
        store.forget_fact(owner, body.fact_id)
        result["facts_erased"] = int(result["facts_erased"]) + 1
        result["generation"] = int(getattr(store, "generations", {}).get(owner, result["generation"]))
    invalidate_alias_cache(owner)
    if body.idempotency_key:
        _FORGET_IDEMPOTENCY[(owner, body.idempotency_key)] = result
    return result


def _find_fact(store: Any, owner: str, fact_id: str) -> Fact | None:
    for fact in store.facts.get(owner, []):
        if fact.id == fact_id:
            return fact
    return None


@router.post("/facts/{fact_id}/resolve")
def resolve_fact(
    owner: str,
    fact_id: str,
    body: ResolveIn,
    _: AuthContext = Depends(require_owner_access),
    store: GraphStore = Depends(get_store),
) -> dict[str, Any]:
    from temporal_memory.core.bridge_store import _postgres, resolve_fact as pg_resolve

    if _postgres(store):
        return pg_resolve(store, owner, fact_id, body)
    fact = _find_fact(store, owner, fact_id)
    if fact is None or fact.id in getattr(store, "forgotten_fact_ids", {}).get(owner, set()):
        raise HTTPException(status_code=404, detail="Fact not found or forgotten")
    new_id: str | None = None
    status = fact.status
    if body.action == "confirm":
        fact.status = "active"
        fact.provenance = "user_supplied"
        status = "active"
    elif body.action in ("edit", "supersede"):
        if not (body.new_text or "").strip():
            raise HTTPException(status_code=422, detail="new_text is required")
        gate = pre_write(body.new_text or "")
        if gate == "credential":
            raise HTTPException(status_code=400, detail="credential")
        if gate:
            raise HTTPException(status_code=400, detail="sensitive")
        evidence = list(fact.evidence)
        if body.evidence_record_id:
            known = getattr(store, "records", {}).get(owner, {})
            if body.evidence_record_id not in known:
                raise HTTPException(status_code=422, detail="evidence_record_id is unknown")
            if body.evidence_record_id not in evidence:
                evidence.append(body.evidence_record_id)
        new_id = f"rf-{uuid.uuid4().hex[:8]}"
        fact.valid_to = body.valid_from or datetime.now(timezone.utc).isoformat()
        fact.status = "superseded"
        fact.superseded_by = new_id
        store.facts.setdefault(owner, []).append(Fact(  # type: ignore[attr-defined]
            id=new_id, owner=owner, text=body.new_text or "", subject_id=fact.subject_id,
            valid_from=body.valid_from or fact.valid_from, evidence=evidence,
            status="active", provenance="user_supplied",
        ))
        status = "active"
    elif body.action == "reject":
        fact.evidence = []
        forgotten = getattr(store, "forgotten_fact_ids", None)
        if forgotten is not None:
            forgotten[owner].add(fact.id)
        status = "rejected"
    version = _bump_facts(store, owner)
    invalidate_alias_cache(owner)
    old_status = "superseded" if new_id else status
    return {
        "ok": True,
        "fact_id": fact_id,
        "new_fact_id": new_id,
        "status": status,  # legacy: status of the NEW fact for edit/supersede (kept for old clients)
        "old_fact": {"id": fact_id, "status": old_status},
        "new_fact": {"id": new_id, "status": "active"} if new_id else None,
        "facts_version": version,
    }


@router.post("/context")
def owner_context(
    owner: str,
    body: ContextIn,
    _: AuthContext = Depends(require_owner_access),
    store: GraphStore = Depends(get_store),
) -> dict[str, Any]:
    return context_pack(owner, body.text, max_tokens=body.max_tokens, store=store)


@router.get("/search")
def search_facts(
    owner: str,
    q: str = Query(...),
    limit: int = Query(default=20, ge=1, le=500),
    source_prefix: str | None = Query(default=None),
    _: AuthContext = Depends(require_owner_access),
    store: GraphStore = Depends(get_store),
) -> dict[str, Any]:
    from temporal_memory.core.bridge_store import _postgres, search_facts as pg_search

    if _postgres(store):
        return pg_search(store, owner, q, limit, source_prefix)
    needle = q.casefold()
    records = getattr(store, "records", {}).get(owner, {})
    hits = []
    for fact in store.visible_facts(owner, limit=10_000):
        if needle not in fact.text.casefold():
            continue
        if source_prefix is not None:
            if not fact.evidence:
                continue
            sources = []
            for rid in fact.evidence:
                record = records.get(rid)
                if record is None:
                    sources.append("")
                else:
                    sources.append(record.source)
            if not sources or not all(source.startswith(source_prefix) for source in sources):
                continue
        hits.append({
            "id": fact.id, "text": fact.text, "subject_id": fact.subject_id,
            "status": fact.status, "evidence": list(fact.evidence),
            "provenance": fact.provenance, "as_of": fact.valid_from,
        })
        if len(hits) >= limit:
            break
    return {"ok": True, "facts": hits}
