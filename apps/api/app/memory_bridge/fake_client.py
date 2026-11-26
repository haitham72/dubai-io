"""In-memory FakeTemporalMemoryClient mirroring temporal_memory semantics."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import io
import secrets
import threading
from typing import Any, Literal
import uuid
import zipfile

from .models import (
    ConsentDeniedError,
    FactResolutionAction,
    FactStatus,
    MemoryBridgeError,
    Provenance,
    SensitiveContentError,
)
from .sensitive import pre_write


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _fold(text: str) -> str:
    return " ".join((text or "").lower().split())


@dataclass
class _FakeRecord:
    id: str
    owner: str
    source: str
    at: str
    author: str
    text: str
    generation: int = 1
    erased_at: str | None = None


@dataclass
class _FakeFact:
    id: str
    owner: str
    text: str
    subject_id: str
    subject_path: str
    valid_from: str
    valid_to: str | None = None
    status: FactStatus = "active"
    superseded_by: str | None = None
    provenance: Provenance = "user_supplied"
    evidence: list[str] = field(default_factory=list)
    entities: list[dict[str, Any]] = field(default_factory=list)
    text_orig: str | None = None
    sensitive_cat: str | None = None
    demo_data: bool = False
    erased_at: str | None = None
    weight_steps: int = 0
    refreshed_weight: float | None = None
    recall_override: bool = False


class _ScopedFakeClient:
    """Token-enforcing proxy around FakeTemporalMemoryClient for role/owner isolation tests."""

    def __init__(self, store: "FakeTemporalMemoryClient", raw_token: str) -> None:
        self._store = store
        self._raw_token = raw_token

    def ensure_owner(
        self,
        owner_id: str,
        *,
        label: str,
        display_name: str = "",
        kind: Literal["real", "simulated", "demo"] = "real",
        timezone: str = "Asia/Dubai",
    ) -> dict[str, Any]:
        self._store.authorize(self._raw_token, require_admin=True)
        return self._store.ensure_owner(
            owner_id, label=label, display_name=display_name, kind=kind, timezone=timezone
        )

    def mint_owner_device_token(
        self, owner_id: str, *, label: str = "cs-bridge"
    ) -> dict[str, Any]:
        self._store.authorize(self._raw_token, require_admin=True)
        return self._store.mint_owner_device_token(owner_id, label=label)

    def revoke_token(self, token_id: str) -> dict[str, Any]:
        self._store.authorize(self._raw_token, require_admin=True)
        return self._store.revoke_token(token_id)

    def upsert_record_and_enqueue(
        self,
        owner_id: str,
        *,
        record_id: str,
        source: str,
        at: str,
        author: str,
        text: str,
        enqueue: Literal["extract.live", "extract.day", "none"] = "extract.live",
        direct_fact: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._store.authorize(self._raw_token, owner_id=owner_id, vault_access=True)
        return self._store.upsert_record_and_enqueue(
            owner_id,
            record_id=record_id,
            source=source,
            at=at,
            author=author,
            text=text,
            enqueue=enqueue,
            direct_fact=direct_fact,
        )

    def context_pack(
        self, owner_id: str, text: str, *, max_tokens: int = 1500
    ) -> dict[str, Any]:
        self._store.authorize(self._raw_token, owner_id=owner_id, vault_access=True)
        return self._store.context_pack(owner_id, text, max_tokens=max_tokens)

    def reinforce_recall(self, owner_id: str, fact_ids: list[str]) -> dict[str, float]:
        self._store.authorize(self._raw_token, owner_id=owner_id, vault_access=True)
        return self._store.reinforce_recall(owner_id, fact_ids)

    def search_facts(
        self,
        owner_id: str,
        query: str,
        *,
        limit: int = 20,
        source_prefix: str | None = None,
        include_lowered: bool = False,
    ) -> list[dict[str, Any]]:
        self._store.authorize(self._raw_token, owner_id=owner_id, vault_access=True)
        return self._store.search_facts(
            owner_id, query, limit=limit, source_prefix=source_prefix, include_lowered=include_lowered
        )

    def get_vault_subjects(self, owner_id: str) -> dict[str, Any]:
        self._store.authorize(self._raw_token, owner_id=owner_id, vault_access=True)
        return self._store.get_vault_subjects(owner_id)

    def get_vault_people(self, owner_id: str) -> dict[str, Any]:
        self._store.authorize(self._raw_token, owner_id=owner_id, vault_access=True)
        return self._store.get_vault_people(owner_id)

    def get_hypotheses(self, owner_id: str) -> dict[str, Any]:
        self._store.authorize(self._raw_token, owner_id=owner_id, vault_access=True)
        return self._store.get_hypotheses(owner_id)

    def get_timeline(
        self,
        owner_id: str,
        *,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 200,
    ) -> dict[str, Any]:
        self._store.authorize(self._raw_token, owner_id=owner_id, vault_access=True)
        return self._store.get_timeline(
            owner_id, date_from=date_from, date_to=date_to, limit=limit
        )

    def get_why_fact(self, owner_id: str, fact_id: str) -> dict[str, Any]:
        self._store.authorize(self._raw_token, owner_id=owner_id, vault_access=True)
        return self._store.get_why_fact(owner_id, fact_id)

    def resolve_fact(
        self,
        owner_id: str,
        fact_id: str,
        *,
        action: FactResolutionAction,
        new_text: str | None = None,
        valid_from: str | None = None,
        evidence_record_id: str | None = None,
    ) -> dict[str, Any]:
        self._store.authorize(self._raw_token, owner_id=owner_id, vault_access=True)
        return self._store.resolve_fact(
            owner_id,
            fact_id,
            action=action,
            new_text=new_text,
            valid_from=valid_from,
            evidence_record_id=evidence_record_id,
        )

    def set_memory_lowered(self, owner_id: str, *, lower: bool = True, **target: Any) -> dict[str, Any]:
        self._store.authorize(self._raw_token, owner_id)
        return self._store.set_memory_lowered(owner_id, lower=lower, **target)

    def forget_source(self, owner_id: str, record_ids: list[str]) -> dict[str, Any]:
        self._store.authorize(self._raw_token, owner_id=owner_id, vault_access=True)
        return self._store.forget_source(owner_id, record_ids)

    def forget_fact(self, owner_id: str, fact_id: str) -> dict[str, Any]:
        self._store.authorize(self._raw_token, owner_id=owner_id, vault_access=True)
        return self._store.forget_fact(owner_id, fact_id)

    def export_markdown_zip(self, owner_id: str) -> bytes:
        self._store.authorize(self._raw_token, owner_id=owner_id, vault_access=True)
        return self._store.export_markdown_zip(owner_id)


class FakeTemporalMemoryClient:
    """Thread-safe in-memory fake implementing TemporalMemoryClient."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._lowered = defaultdict(set)
        self.owners: dict[str, dict[str, Any]] = {}
        self.records: dict[str, dict[str, _FakeRecord]] = defaultdict(dict)
        self.facts: dict[str, list[_FakeFact]] = defaultdict(list)
        self.subjects: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
        self.entities: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self.links: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self.forget_rules: dict[str, set[str]] = defaultdict(set)
        self.forgotten_fact_ids: dict[str, set[str]] = defaultdict(set)
        self.quarantine: dict[str, dict[str, int]] = defaultdict(dict)
        self.jobs: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
        self.generations: dict[str, int] = defaultdict(int)
        self.facts_version: dict[str, int] = defaultdict(int)
        self.tokens: dict[str, dict[str, Any]] = {}
        self._token_by_hash: dict[str, str] = {}

    # ------------------------------------------------------------ token auth
    def register_token(
        self,
        role: Literal["admin", "worker", "owner-device"],
        *,
        owner: str | None = None,
        label: str = "",
        raw_token: str | None = None,
    ) -> dict[str, Any]:
        if role == "owner-device" and not owner:
            raise MemoryBridgeError("owner-device token requires owner", status_code=400)
        with self._lock:
            token_id = f"tok_{uuid.uuid4().hex[:12]}"
            secret = raw_token or secrets.token_urlsafe(24)
            tok_hash = _hash_token(secret)
            row = {
                "id": token_id,
                "token_hash": tok_hash,
                "role": role,
                "owner": owner,
                "label": label,
                "revoked_at": None,
            }
            self.tokens[token_id] = row
            self._token_by_hash[tok_hash] = token_id
            return {
                "id": token_id,
                "token": secret,
                "role": role,
                "owner": owner,
                "label": label,
            }

    def authorize(
        self,
        raw_token: str,
        *,
        owner_id: str | None = None,
        require_admin: bool = False,
        vault_access: bool = False,
    ) -> dict[str, Any]:
        with self._lock:
            token_id = self._token_by_hash.get(_hash_token(raw_token or ""))
            row = self.tokens.get(token_id) if token_id else None
            if row is None or row["revoked_at"] is not None:
                raise ConsentDeniedError(
                    "invalid or revoked bearer token",
                    code="invalid_token",
                    status_code=401,
                )
            role = row["role"]
            if require_admin and role != "admin":
                raise ConsentDeniedError(
                    "admin token required",
                    code="admin_required",
                    status_code=403,
                )
            if vault_access or owner_id is not None:
                if role == "worker":
                    raise ConsentDeniedError(
                        "worker token cannot access owner vault or memory endpoints",
                        code="worker_forbidden",
                        status_code=403,
                    )
                if role == "owner-device" and row["owner"] != owner_id:
                    raise ConsentDeniedError(
                        "owner-device token scoped to a different owner",
                        code="cross_owner_forbidden",
                        status_code=403,
                    )
            return {
                "id": row["id"],
                "role": role,
                "owner": row["owner"],
                "label": row["label"],
            }

    def as_scoped(self, raw_token: str) -> _ScopedFakeClient:
        """Return a TemporalMemoryClient proxy enforcing bearer token role & owner scope."""
        return _ScopedFakeClient(self, raw_token)

    def mint_owner_device_token(
        self,
        owner_id: str,
        *,
        label: str = "cs-bridge",
    ) -> dict[str, Any]:
        return self.register_token("owner-device", owner=owner_id, label=label)

    def revoke_token(self, token_id: str) -> dict[str, Any]:
        with self._lock:
            row = self.tokens.get(token_id)
            if row is None:
                raise MemoryBridgeError(f"token not found: {token_id}", code="not_found", status_code=404)
            if row["revoked_at"] is None:
                row["revoked_at"] = _now_iso()
            return {"ok": True, "id": token_id}

    # ------------------------------------------------------------ owner / seed
    def ensure_owner(
        self,
        owner_id: str,
        *,
        label: str,
        display_name: str = "",
        kind: Literal["real", "simulated", "demo"] = "real",
        timezone: str = "Asia/Dubai",
    ) -> dict[str, Any]:
        with self._lock:
            existing = self.owners.get(owner_id)
            aliases = list(existing.get("self_aliases", [])) if existing else []
            owner_row = {
                "id": owner_id,
                "label": label,
                "kind": kind,
                "display_name": display_name,
                "self_aliases": aliases,
                "timezone": timezone,
            }
            self.owners[owner_id] = owner_row
            return dict(owner_row)

    def _ensure_owner_internal(self, owner_id: str) -> dict[str, Any]:
        if owner_id not in self.owners:
            self.ensure_owner(owner_id, label=owner_id)
        return self.owners[owner_id]

    def _ensure_subject(self, owner_id: str, subject_path: str) -> str:
        path = (subject_path or "general").strip("/") or "general"
        for sid, subj in self.subjects[owner_id].items():
            if subj["path"] == path or sid == path:
                return sid
        sid = f"subj_{len(self.subjects[owner_id]) + 1}_{path.replace('/', '_')}"
        label = path.split("/")[-1].replace("-", " ").title()
        self.subjects[owner_id][sid] = {
            "id": sid,
            "path": path,
            "label": label,
            "kind": "topic",
            "parent_id": None,
            "status": "active",
            "salience": 0.8,
        }
        return sid

    def _visible_facts(self, owner_id: str) -> list[_FakeFact]:
        forgotten_rids = self.forget_rules.get(owner_id, set())
        forgotten_fids = self.forgotten_fact_ids.get(owner_id, set())
        recs = self.records.get(owner_id, {})
        out: list[_FakeFact] = []
        for f in self.facts.get(owner_id, []):
            if f.erased_at is not None or f.id in forgotten_fids:
                continue
            if f.evidence:
                surviving = [
                    rid
                    for rid in f.evidence
                    if rid not in forgotten_rids
                    and (rid not in recs or recs[rid].erased_at is None)
                ]
                if not surviving:
                    continue
            out.append(f)
        return out

    def _fact_lowered(self, owner_id: str, fact: _FakeFact) -> bool:
        return not fact.recall_override and self._matches_lowering(owner_id, fact, self._lowered[owner_id])

    def _matches_lowering(self, owner_id: str, fact: _FakeFact, denied: set[tuple[str, str]]) -> bool:
        return bool(
            ("fact_id", fact.id) in denied or ("subject_id", fact.subject_id) in denied
            or any(("record_ids", rid) in denied for rid in fact.evidence)
            or any(src == val or src.startswith(val + ":")
                   for typ, val in denied if typ == "source" for src in self._fact_sources(owner_id, fact))
        )

    def set_memory_lowered(self, owner_id: str, *, lower: bool = True, **target: Any) -> dict[str, Any]:
        with self._lock:
            self._ensure_owner_internal(owner_id)
            selected = [(k, v) for k, v in target.items() if v]
            if len(selected) != 1:
                raise MemoryBridgeError("Choose one memory target", status_code=422)
            kind, val = selected[0]
            allowed = {
                "record_ids": self.records[owner_id],
                "fact_id": {f.id for f in self.facts[owner_id]},
                "subject_id": self.subjects[owner_id],
            }
            ids = list(dict.fromkeys(val)) if kind == "record_ids" else [val]
            if kind in allowed and any(i not in allowed[kind] for i in ids):
                raise MemoryBridgeError("Memory target not found", status_code=404)
            for ident in ids:
                if lower:
                    self._lowered[owner_id].add((kind, ident))
                    for fact in self.facts[owner_id]:
                        if fact.recall_override and self._matches_lowering(owner_id, fact, {(kind, ident)}):
                            fact.recall_override = False
                else:
                    self._lowered[owner_id].discard((kind, ident))
            self.facts_version[owner_id] += 1
            return {"ok": True, "lowered": lower, "weight": 0.01 if lower else None,
                    "records": len(ids) if kind == "record_ids" else 0, "affected": len(ids), "facts_erased": 0}

    def lowered_record_ids(self, owner_id: str) -> set[str]:
        with self._lock:
            return {value for kind, value in self._lowered[owner_id] if kind == "record_ids"}

    def _fact_weight(self, owner_id: str, fact: _FakeFact) -> float:
        return 0.01 if self._fact_lowered(owner_id, fact) else max(0.01, (fact.refreshed_weight or 1.0) * 0.5 ** fact.weight_steps)

    def _fact_sources(self, owner_id: str, fact: _FakeFact) -> list[str]:
        recs = self.records.get(owner_id, {})
        sources: list[str] = []
        for rid in fact.evidence:
            rec = recs.get(rid)
            if rec is not None and rec.erased_at is None and rec.source not in sources:
                sources.append(rec.source)
        return sources

    def _fact_to_dict(self, owner_id: str, fact: _FakeFact) -> dict[str, Any]:
        is_demo = self.owners.get(owner_id, {}).get("kind") == "demo" or fact.demo_data
        return {
            "id": fact.id,
            "owner": owner_id,
            "text": fact.text,
            "text_orig": fact.text_orig,
            "subject_id": fact.subject_id,
            "subject_path": fact.subject_path,
            "valid_from": fact.valid_from,
            "valid_to": fact.valid_to,
            "status": fact.status,
            "superseded_by": fact.superseded_by,
            "provenance": fact.provenance,
            "evidence": list(fact.evidence),
            "sources": self._fact_sources(owner_id, fact),
            "lowered": self._fact_lowered(owner_id, fact),
            "weight": self._fact_weight(owner_id, fact),
            "sensitive_cat": fact.sensitive_cat,
            "demo_data": is_demo,
        }

    # --------------------------------------------------------------- write/job
    def upsert_record_and_enqueue(
        self,
        owner_id: str,
        *,
        record_id: str,
        source: str,
        at: str,
        author: str,
        text: str,
        enqueue: Literal["extract.live", "extract.day", "none"] = "extract.live",
        direct_fact: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            owner_row = self._ensure_owner_internal(owner_id)
            if record_id in self.forget_rules[owner_id]:
                raise ConsentDeniedError(
                    f"record {record_id} is blocked by forget_rules",
                    code="forget_rule_blocked",
                    status_code=409,
                )

            existing = self.records[owner_id].get(record_id)
            gen = (existing.generation + 1) if existing is not None else 1
            rec = _FakeRecord(
                id=record_id,
                owner=owner_id,
                source=source,
                at=at,
                author=author,
                text=text,
                generation=gen,
                erased_at=None,
            )

            fact_ids: list[str] = []
            if direct_fact is not None:
                evidence = [str(e) for e in (direct_fact.get("evidence") or []) if e]
                if not evidence:
                    raise MemoryBridgeError(
                        "direct_fact requires non-empty evidence",
                        code="missing_evidence",
                        status_code=422,
                    )
                fact_text = str(direct_fact.get("text") or "")
                hit = pre_write(fact_text)
                if hit == "credential":
                    self.quarantine[owner_id]["credential"] = (
                        self.quarantine[owner_id].get("credential", 0) + 1
                    )
                    raise SensitiveContentError("credential")
                explicit_sensitive_cat = direct_fact.get("sensitive_cat")
                if hit is not None and not explicit_sensitive_cat:
                    self.quarantine[owner_id][hit] = (
                        self.quarantine[owner_id].get(hit, 0) + 1
                    )
                    self.records[owner_id][record_id] = rec
                    return {
                        "ok": True,
                        "record_ids": [record_id],
                        "job_id": None,
                        "fact_ids": [],
                        "quarantined": 1,
                        "quarantine_category": hit,
                    }

                subj_path = str(
                    direct_fact.get("subject_path")
                    or direct_fact.get("subject_id")
                    or "general"
                )
                subj_id = self._ensure_subject(owner_id, subj_path)
                fid = str(direct_fact.get("id") or f"f_{uuid.uuid4().hex[:10]}")
                prov: Provenance = direct_fact.get("provenance") or (
                    "demo_fixture" if owner_row.get("kind") == "demo" else "user_supplied"
                )
                status_val: FactStatus = direct_fact.get("status") or "active"
                fact = _FakeFact(
                    id=fid,
                    owner=owner_id,
                    text=fact_text,
                    text_orig=direct_fact.get("text_orig"),
                    subject_id=subj_id,
                    subject_path=subj_path,
                    valid_from=str(direct_fact.get("valid_from") or at),
                    status=status_val,
                    provenance=prov,
                    evidence=evidence,
                    entities=list(direct_fact.get("entities") or []),
                    sensitive_cat=explicit_sensitive_cat,
                    demo_data=bool(
                        direct_fact.get("demo_data") or prov == "demo_fixture"
                    ),
                )
                self.records[owner_id][record_id] = rec
                self.facts[owner_id].append(fact)
                self.facts_version[owner_id] += 1
                fact_ids.append(fid)
            else:
                self.records[owner_id][record_id] = rec

            job_id: str | None = None
            if enqueue != "none":
                job_id = f"job_{uuid.uuid4().hex[:10]}"
                self.jobs[owner_id][job_id] = {
                    "id": job_id,
                    "owner": owner_id,
                    "kind": enqueue,
                    "input_ref": [record_id],
                    "input_version": rec.generation,
                    "state": "queued",
                }

            return {
                "ok": True,
                "record_ids": [record_id],
                "job_id": job_id,
                "fact_ids": fact_ids,
                "quarantined": 0,
            }

    def simulate_worker_submit(
        self,
        owner_id: str,
        record_id: str,
        input_version: int,
        fact_text: str,
        *,
        subject_path: str = "general",
        valid_from: str | None = None,
        provenance: Provenance = "inferred",
        status: FactStatus = "hypothesis",
        text_orig: str | None = None,
        entities: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Test helper enforcing the generation fence on asynchronous worker submissions."""
        with self._lock:
            rec = self.records[owner_id].get(record_id)
            if (
                rec is None
                or rec.erased_at is not None
                or record_id in self.forget_rules[owner_id]
                or rec.generation > input_version
            ):
                return {
                    "ok": False,
                    "verdict": "fence_stale",
                    "reason": "generation_stale",
                }

            hit = pre_write(fact_text) or (pre_write(text_orig) if text_orig else None)
            if hit is not None:
                self.quarantine[owner_id][hit] = (
                    self.quarantine[owner_id].get(hit, 0) + 1
                )
                return {
                    "ok": False,
                    "verdict": "quarantined",
                    "category": hit,
                }

            subj_id = self._ensure_subject(owner_id, subject_path)
            fid = f"f_{uuid.uuid4().hex[:10]}"
            fact = _FakeFact(
                id=fid,
                owner=owner_id,
                text=fact_text,
                text_orig=text_orig,
                subject_id=subj_id,
                subject_path=subject_path,
                valid_from=valid_from or rec.at,
                status=status,
                provenance=provenance,
                evidence=[record_id],
                entities=list(entities or []),
            )
            self.facts[owner_id].append(fact)
            for job in self.jobs[owner_id].values():
                if record_id in job["input_ref"] and job["state"] in ("queued", "leased"):
                    job["state"] = "applied"
            self.facts_version[owner_id] += 1
            return {"ok": True, "verdict": "applied", "fact_id": fid}

    # ------------------------------------------------------------------ reads
    def context_pack(
        self,
        owner_id: str,
        text: str,
        *,
        max_tokens: int = 1500,
    ) -> dict[str, Any]:
        with self._lock:
            owner_row = self.owners.get(owner_id, {})
            is_demo = owner_row.get("kind") == "demo"
            now_iso = _now_iso()
            tokens = [t for t in _fold(text).split() if len(t) >= 2]
            visible = [
                f for f in self._visible_facts(owner_id) if f.status != "history" and self._fact_weight(owner_id, f) >= 0.10
            ]
            scored: list[tuple[int, _FakeFact]] = []
            for f in visible:
                hay = _fold(f"{f.text} {f.text_orig or ''} {f.subject_path}")
                score = sum(1 for tok in tokens if tok in hay)
                if not tokens or score > 0:
                    scored.append((score, f))
            scored.sort(key=lambda pair: (pair[0], pair[1].valid_from, pair[1].id), reverse=True)

            char_budget = max(200, int(max_tokens) * 4)
            used_chars = 0
            packed_facts: list[dict[str, Any]] = []
            open_changes: list[dict[str, Any]] = []
            for _, f in scored:
                if f.status in ("superseded", "ended"):
                    open_changes.append(
                        {
                            "fact_id": f.id,
                            "status": f.status,
                            "summary": f"{f.text} (was until {f.valid_to or '?'})",
                            "valid_from": f.valid_from,
                            "valid_to": f.valid_to,
                            "superseded_by": f.superseded_by,
                            "provenance": f.provenance,
                            "as_of": now_iso,
                        }
                    )
                est = len(f.text) + len(f.text_orig or "") + 64
                if packed_facts and used_chars + est > char_budget:
                    break
                packed_facts.append(
                    {
                        "id": f.id,
                        "text": f.text,
                        "text_orig": f.text_orig,
                        "subject_id": f.subject_id,
                        "subject_path": f.subject_path,
                        "valid_from": f.valid_from,
                        "valid_to": f.valid_to,
                        "status": f.status,
                        "provenance": f.provenance,
                        "as_of": f.valid_from or now_iso,
                        "demo_data": is_demo or f.demo_data,
                    }
                )
                used_chars += est

            return {
                "owner": owner_id,
                "entities": list(self.entities.get(owner_id, [])),
                "facts": packed_facts,
                "open_changes": open_changes[:8],
                "tokens_est": max(1, used_chars // 4),
                "provenance": "user_supplied",
                "as_of": now_iso,
                "demo_data": is_demo,
            }

    def reinforce_recall(self, owner_id: str, fact_ids: list[str]) -> dict[str, float]:
        with self._lock:
            weights = {}
            for fact in self._visible_facts(owner_id):
                if fact.id in fact_ids:
                    weight = min(1.0, max(0.35, self._fact_weight(owner_id, fact) + 0.25))
                    self._lowered[owner_id].discard(("fact_id", fact.id))
                    fact.refreshed_weight = weights[fact.id] = weight
                    fact.recall_override = True
                    fact.weight_steps = 0
            if weights:
                self.facts_version[owner_id] += 1
            return weights

    def search_facts(
        self,
        owner_id: str,
        query: str,
        *,
        limit: int = 20,
        source_prefix: str | None = None,
        include_lowered: bool = False,
    ) -> list[dict[str, Any]]:
        with self._lock:
            q_tokens = [t for t in _fold(query).split() if t]
            recs = self.records.get(owner_id, {})
            visible = [
                f
                for f in self._visible_facts(owner_id) if include_lowered or self._fact_weight(owner_id, f) >= 0.10
                if f.status not in ("superseded", "history")
            ]
            matched: list[_FakeFact] = []
            for f in visible:
                if source_prefix is not None:
                    if not f.evidence:
                        continue
                    if not all(
                        (rid in recs and recs[rid].erased_at is None and recs[rid].source.startswith(source_prefix))
                        for rid in f.evidence
                    ):
                        continue
                if q_tokens:
                    hay = _fold(f"{f.text} {f.text_orig or ''} {f.subject_path}")
                    if not all(tok in hay for tok in q_tokens):
                        continue
                matched.append(f)
            matched.sort(key=lambda x: (x.valid_from or "", x.id), reverse=True)
            return [self._fact_to_dict(owner_id, f) for f in matched[: max(1, int(limit))]]

    def get_vault_subjects(self, owner_id: str) -> dict[str, Any]:
        with self._lock:
            now_iso = _now_iso()
            is_demo = self.owners.get(owner_id, {}).get("kind") == "demo"
            visible = [
                f for f in self._visible_facts(owner_id) if f.status != "history"
            ]
            counts: dict[str, int] = defaultdict(int)
            for f in visible:
                counts[f.subject_id] += 1
            themes = [
                {
                    **subj,
                    "fact_count": counts[subj["id"]],
                    "direct_fact_count": counts[subj["id"]],
                    "provenance": "user_supplied" if subj["status"] == "active" else "inferred",
                    "as_of": now_iso,
                    "demo_data": is_demo,
                    "children": [],
                }
                for subj in sorted(self.subjects.get(owner_id, {}).values(), key=lambda s: s["path"])
            ]
            return {
                "owner": owner_id,
                "themes": themes,
                "total_facts": sum(counts.values()),
                "provenance": "user_supplied",
                "as_of": now_iso,
                "demo_data": is_demo,
            }

    def get_vault_people(self, owner_id: str) -> dict[str, Any]:
        with self._lock:
            now_iso = _now_iso()
            is_demo = self.owners.get(owner_id, {}).get("kind") == "demo"
            ents = self.entities.get(owner_id, [])
            people = [e for e in ents if e.get("kind") == "person" and e.get("status") != "merged"]
            places = [e for e in ents if e.get("kind") == "place" and e.get("status") != "merged"]
            orgs = [e for e in ents if e.get("kind") == "org" and e.get("status") != "merged"]
            visible_fids = {f.id for f in self._visible_facts(owner_id)}
            vis_links = [
                ln
                for ln in self.links.get(owner_id, [])
                if ln.get("evidence_fact_id") is None or ln.get("evidence_fact_id") in visible_fids
            ]
            return {
                "owner": owner_id,
                "people": people,
                "places": places,
                "orgs": orgs,
                "links": vis_links,
                "provenance": "user_supplied",
                "as_of": now_iso,
                "demo_data": is_demo,
            }

    def get_hypotheses(self, owner_id: str) -> dict[str, Any]:
        with self._lock:
            now_iso = _now_iso()
            is_demo = self.owners.get(owner_id, {}).get("kind") == "demo"
            hyps = [
                f for f in self._visible_facts(owner_id) if f.status == "hypothesis"
            ]
            return {
                "owner": owner_id,
                "hypotheses": [
                    {
                        "id": f.id,
                        "text": f.text if f.text.startswith("I noticed") else f"I noticed {f.text}",
                        "subject_id": f.subject_id,
                        "subject_path": f.subject_path,
                        "evidence": list(f.evidence),
                        "valid_from": f.valid_from,
                        "provenance": f.provenance,
                        "as_of": f.valid_from or now_iso,
                        "actions": ["Confirm", "Edit", "Not true", "Forget"],
                        "demo_data": is_demo or f.demo_data,
                    }
                    for f in hyps
                ],
                "provenance": "inferred",
                "as_of": now_iso,
                "demo_data": is_demo,
            }

    def get_timeline(
        self,
        owner_id: str,
        *,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 200,
    ) -> dict[str, Any]:
        with self._lock:
            now_iso = _now_iso()
            is_demo = self.owners.get(owner_id, {}).get("kind") == "demo"
            items = [
                f
                for f in self._visible_facts(owner_id)
                if f.status != "history"
                and (not date_from or (f.valid_from or "") >= date_from)
                and (not date_to or (f.valid_from or "") <= date_to)
            ]
            items.sort(key=lambda x: (x.valid_from or "", x.id), reverse=True)
            return {
                "owner": owner_id,
                "items": [
                    {
                        "id": f.id,
                        "text": f.text,
                        "text_orig": f.text_orig,
                        "subject_id": f.subject_id,
                        "subject_path": f.subject_path,
                        "valid_from": f.valid_from,
                        "valid_to": f.valid_to,
                        "status": f.status,
                        "superseded_by": f.superseded_by,
                        "lowered": self._fact_lowered(owner_id, f),
                        "weight": self._fact_weight(owner_id, f),
                        "provenance": f.provenance,
                        "evidence": list(f.evidence),
                        "as_of": f.valid_from or now_iso,
                        "demo_data": is_demo or f.demo_data,
                    }
                    for f in items[: max(1, int(limit))]
                ],
                "provenance": "user_supplied",
                "as_of": now_iso,
                "demo_data": is_demo,
            }

    def get_why_fact(self, owner_id: str, fact_id: str) -> dict[str, Any]:
        with self._lock:
            now_iso = _now_iso()
            is_demo = self.owners.get(owner_id, {}).get("kind") == "demo"
            fact = next(
                (f for f in self._visible_facts(owner_id) if f.id == fact_id),
                None,
            )
            if fact is None:
                raise MemoryBridgeError(
                    "Fact not found or forgotten", code="not_found", status_code=404
                )
            recs = self.records.get(owner_id, {})
            ev_records = [
                recs[rid]
                for rid in fact.evidence
                if rid in recs and recs[rid].erased_at is None
            ]
            return {
                "owner": owner_id,
                "fact_id": fact.id,
                "text": fact.text,
                "text_orig": fact.text_orig,
                "status": fact.status,
                "valid_from": fact.valid_from,
                "provenance": fact.provenance,
                "evidence": [
                    {
                        "id": r.id,
                        "source": r.source,
                        "at": r.at,
                        "author": r.author,
                        "text": r.text,
                        "provenance": "user_supplied",
                        "as_of": r.at,
                    }
                    for r in ev_records
                ],
                "as_of": fact.valid_from or now_iso,
                "demo_data": is_demo or fact.demo_data,
            }

    # ------------------------------------------------------------ resolve/forget
    def resolve_fact(
        self,
        owner_id: str,
        fact_id: str,
        *,
        action: FactResolutionAction,
        new_text: str | None = None,
        valid_from: str | None = None,
        evidence_record_id: str | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            fact = next(
                (f for f in self._visible_facts(owner_id) if f.id == fact_id),
                None,
            )
            if fact is None:
                raise MemoryBridgeError(
                    f"Fact not found: {fact_id}", code="not_found", status_code=404
                )

            if action == "confirm":
                fact.status = "active"
                fact.provenance = "user_supplied"
                self.facts_version[owner_id] += 1
                return {
                    "ok": True,
                    "fact_id": fact.id,
                    "new_fact_id": None,
                    "status": "active",
                    "facts_version": self.facts_version[owner_id],
                }

            if action in ("edit", "supersede"):
                if not new_text or not new_text.strip():
                    raise MemoryBridgeError(
                        "new_text is required for edit/supersede",
                        code="missing_new_text",
                        status_code=422,
                    )
                hit = pre_write(new_text)
                if hit == "credential":
                    self.quarantine[owner_id]["credential"] = (
                        self.quarantine[owner_id].get("credential", 0) + 1
                    )
                    raise SensitiveContentError("credential")
                if hit is not None:
                    raise SensitiveContentError(hit)

                now_iso = _now_iso()
                new_fid = f"f_{uuid.uuid4().hex[:10]}"
                ev = [evidence_record_id] if evidence_record_id else list(fact.evidence)
                new_fact = _FakeFact(
                    id=new_fid,
                    owner=owner_id,
                    text=new_text.strip(),
                    subject_id=fact.subject_id,
                    subject_path=fact.subject_path,
                    valid_from=valid_from or now_iso,
                    status="active",
                    provenance="user_supplied",
                    evidence=ev,
                    entities=list(fact.entities),
                    demo_data=fact.demo_data,
                )
                fact.valid_to = valid_from or now_iso
                fact.status = "superseded"
                fact.superseded_by = new_fid
                self.facts[owner_id].append(new_fact)
                self.facts_version[owner_id] += 1
                return {
                    "ok": True,
                    "fact_id": fact.id,
                    "new_fact_id": new_fid,
                    "status": "superseded",
                    "facts_version": self.facts_version[owner_id],
                }

            if action == "reject":
                fact.weight_steps += 1
                self.facts_version[owner_id] += 1
                return {
                    "ok": True,
                    "fact_id": fact.id,
                    "new_fact_id": None,
                    "status": "rejected",
                    "facts_version": self.facts_version[owner_id],
                }

            raise MemoryBridgeError(
                f"unsupported resolution action: {action}",
                code="invalid_action",
                status_code=400,
            )

    def forget_source(self, owner_id: str, record_ids: list[str]) -> dict[str, Any]:
        with self._lock:
            if not record_ids:
                return {
                    "ok": True,
                    "generation": self.generations[owner_id],
                    "records": 0,
                    "facts_erased": 0,
                    "facts_trimmed": 0,
                    "entity_subjects_recomputed": 0,
                    "jobs_requeued": 0,
                    "jobs_enqueued": 0,
                }

            rids = sorted(set(record_ids))
            forgotten_set = set(rids)
            now_iso = _now_iso()

            self.forget_rules[owner_id].update(rids)
            records_count = 0
            max_rec_gen = 0
            for rid in rids:
                rec = self.records[owner_id].get(rid)
                if rec is not None:
                    rec.generation += 1
                    if rec.erased_at is None:
                        rec.erased_at = now_iso
                    records_count += 1
                    max_rec_gen = max(max_rec_gen, rec.generation)

            self.generations[owner_id] = max(self.generations[owner_id] + 1, max_rec_gen)
            generation = self.generations[owner_id]

            facts_erased = 0
            facts_trimmed = 0
            for fact in self.facts[owner_id]:
                if fact.erased_at is not None:
                    continue
                have = set(fact.evidence)
                if not have or not (have & forgotten_set):
                    continue
                if have <= forgotten_set:
                    fact.erased_at = now_iso
                    facts_erased += 1
                else:
                    fact.evidence = [rid for rid in fact.evidence if rid not in forgotten_set]
                    facts_trimmed += 1

            # Recompute entity-subject pairs from surviving visible non-hypothesis facts.
            es_keys: set[tuple[str, str, str]] = set()
            for fact in self._visible_facts(owner_id):
                if fact.status in ("history", "hypothesis"):
                    continue
                for ent in fact.entities:
                    es_keys.add((str(ent.get("entity_id", "")), fact.subject_id, str(ent.get("role") or "")))
            entity_subjects_recomputed = len(es_keys)

            # Requeue/dead/enqueued jobs across extract.day and extract.live.
            jobs_requeued = 0
            jobs_enqueued = 0
            to_enqueue: list[list[str]] = []
            for job in self.jobs[owner_id].values():
                if job["kind"] not in ("extract.day", "extract.live"):
                    continue
                if not (set(job["input_ref"]) & forgotten_set):
                    continue
                survivors = [r for r in job["input_ref"] if r not in forgotten_set]
                if job["state"] in ("queued", "expired", "submitted", "rejected"):
                    if survivors:
                        job["input_ref"] = survivors
                        job["input_version"] = max(
                            (
                                self.records[owner_id][r].generation
                                for r in survivors
                                if r in self.records[owner_id]
                            ),
                            default=0,
                        )
                        job["state"] = "queued"
                        jobs_requeued += 1
                    else:
                        job["state"] = "dead"
                elif job["state"] == "applied" and survivors:
                    to_enqueue.append(survivors)

            for survivors in to_enqueue:
                jid = f"job_{uuid.uuid4().hex[:10]}"
                self.jobs[owner_id][jid] = {
                    "id": jid,
                    "owner": owner_id,
                    "kind": "extract.day",
                    "input_ref": survivors,
                    "input_version": max(
                        (
                            self.records[owner_id][r].generation
                            for r in survivors
                            if r in self.records[owner_id]
                        ),
                        default=0,
                    ),
                    "state": "queued",
                }
                jobs_enqueued += 1

            self.facts_version[owner_id] += 1
            return {
                "ok": True,
                "generation": generation,
                "records": records_count,
                "facts_erased": facts_erased,
                "facts_trimmed": facts_trimmed,
                "entity_subjects_recomputed": entity_subjects_recomputed,
                "jobs_requeued": jobs_requeued,
                "jobs_enqueued": jobs_enqueued,
            }

    def forget_fact(self, owner_id: str, fact_id: str) -> dict[str, Any]:
        with self._lock:
            self.generations[owner_id] += 1
            self.forgotten_fact_ids[owner_id].add(fact_id)
            now_iso = _now_iso()
            erased = 0
            for fact in self.facts.get(owner_id, []):
                if fact.id == fact_id and fact.erased_at is None:
                    fact.erased_at = now_iso
                    erased += 1
            self.facts_version[owner_id] += 1
            return {
                "ok": True,
                "fact_id": fact_id,
                "generation": self.generations[owner_id],
                "facts_erased": erased,
            }

    def export_markdown_zip(self, owner_id: str) -> bytes:
        with self._lock:
            visible = [
                f for f in self._visible_facts(owner_id) if f.status != "history"
            ]
            regular = [f for f in visible if f.status != "hypothesis"]
            hyps = [f for f in visible if f.status == "hypothesis"]
            quar = self.quarantine.get(owner_id, {})

            files: dict[str, str] = {}
            mem_lines = [f"# Memories ({owner_id})", ""]
            for f in regular:
                mem_lines.append(f"- {f.valid_from} · {f.text} `src: {', '.join(f.evidence)}`")
            files["MEMORIES.md"] = "\n".join(mem_lines) + "\n"

            noticed_lines = ["# Noticed (hypotheses)", ""]
            for h in hyps:
                txt = h.text if h.text.startswith("I noticed") else f"I noticed {h.text}"
                noticed_lines.append(f"- {txt} `[Confirm / Edit / Not true / Forget]`")
            files["noticed.md"] = "\n".join(noticed_lines) + "\n"

            held_lines = ["# Held Back (sensitive categories — counts only, Rule 9)", ""]
            for cat, cnt in sorted(quar.items()):
                held_lines.append(f"- **{cat}:** {cnt} item(s) held back")
            if not quar:
                held_lines.append("- _(0 items held back)_")
            files["held-back.md"] = "\n".join(held_lines) + "\n"

            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                for rel_path, content in sorted(files.items()):
                    zf.writestr(f"memory/{rel_path}", content.encode("utf-8"))
            return buf.getvalue()
