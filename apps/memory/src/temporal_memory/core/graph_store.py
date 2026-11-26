"""PostgreSQL 17 GraphStore implementation and persistence helpers (WP-A)."""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
from typing import Any, Iterator
import uuid

from temporal_memory.db.db import Database, fold_text, get_database
from temporal_memory.models import (
    Attempt,
    Candidate,
    Entity,
    EntitySubject,
    Fact,
    FactEntity,
    Job,
    Link,
    Milestone,
    Owner,
    OwnerKind,
    Record,
    Subject,
    Worker,
)


def _as_iso(val: Any) -> str | None:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.isoformat()
    return str(val)


def _as_json_list(val: Any) -> list[Any]:
    if val is None:
        return []
    if isinstance(val, str):
        return list(json.loads(val))
    return list(val)


def _record_hash(rec: Record) -> str:
    payload = f"{rec.source}\0{rec.at}\0{rec.author}\0{rec.text}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class PostgresGraphStore:
    """Postgres-backed GraphStore implementing scoped context packing and visible fact queries."""

    def __init__(self, db: Database) -> None:
        self.db = db

    # ---------------------------------------------------------------- owners & records
    def create_owner(
        self,
        owner: Owner | str,
        label: str = "",
        kind: OwnerKind = "real",
        display_name: str = "",
        self_aliases: list[str] | None = None,
        timezone: str = "Asia/Dubai",
    ) -> Owner:
        """Create or update an owner row."""
        obj = (
            owner
            if isinstance(owner, Owner)
            else Owner(
                id=owner,
                label=label or owner,
                kind=kind,
                display_name=display_name,
                self_aliases=list(self_aliases or []),
                timezone=timezone,
            )
        )
        with self.db.transaction() as conn:
            row = conn.execute(
                """
                INSERT INTO owners (id, label, kind, display_name, self_aliases, timezone, privacy_revision)
                VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    label = EXCLUDED.label,
                    kind = EXCLUDED.kind,
                    display_name = EXCLUDED.display_name,
                    self_aliases = EXCLUDED.self_aliases,
                    timezone = EXCLUDED.timezone
                RETURNING id, label, kind, display_name, self_aliases, timezone, privacy_revision
                """,
                (
                    obj.id,
                    obj.label,
                    obj.kind,
                    obj.display_name,
                    json.dumps(obj.self_aliases),
                    obj.timezone,
                    int(getattr(obj, "privacy_revision", 0) or 0),
                ),
            ).fetchone()
        return self._row_to_owner(row)

    def get_owner(self, owner_id: str) -> Owner | None:
        """Fetch an owner by id, or None if not found."""
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT id, label, kind, display_name, self_aliases, timezone, privacy_revision "
                "FROM owners WHERE id = %s",
                (owner_id,),
            ).fetchone()
        return self._row_to_owner(row) if row else None

    def get_user_md(self, owner: str) -> str:
        """Return the owner's user_md profile markdown."""
        with self.db.connection() as conn:
            row = conn.execute("SELECT user_md FROM owners WHERE id = %s", (owner,)).fetchone()
        return str(row["user_md"]) if row else ""

    def set_user_md(self, owner: str, md: str) -> None:
        """Update the owner's user_md profile markdown."""
        with self.db.transaction() as conn:
            conn.execute("UPDATE owners SET user_md = %s WHERE id = %s", (md, owner))

    def upsert_records(self, owner: str, records: list[Record]) -> int:
        """Insert or update raw source records for an owner."""
        if not records:
            return 0
        count = 0
        with self.db.transaction() as conn:
            for rec in records:
                conn.execute(
                    """
                    INSERT INTO records (id, owner, source, at, author, text, content_hash, generation)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (owner, id) DO UPDATE SET
                        source = EXCLUDED.source,
                        at = EXCLUDED.at,
                        author = EXCLUDED.author,
                        text = EXCLUDED.text,
                        content_hash = EXCLUDED.content_hash,
                        generation = GREATEST(records.generation, EXCLUDED.generation)
                    """,
                    (
                        rec.id,
                        owner,
                        rec.source,
                        rec.at,
                        rec.author,
                        rec.text,
                        _record_hash(rec),
                        rec.generation,
                    ),
                )
                count += 1
        return count

    def get_records(self, owner: str, record_ids: list[str]) -> list[Record]:
        """Fetch active (non-erased) records matching record_ids for owner."""
        if not record_ids:
            return []
        with self.db.connection() as conn:
            rows = conn.execute(
                """
                SELECT id, owner, source, at, author, text, generation
                FROM records
                WHERE owner = %s AND id = ANY(%s) AND erased_at IS NULL
                ORDER BY at ASC, id ASC
                """,
                (owner, list(record_ids)),
            ).fetchall()
        return [
            Record(
                id=r["id"],
                owner=r["owner"],
                source=r["source"],
                at=r["at"],
                author=r["author"],
                text=r["text"],
                generation=int(r["generation"]),
            )
            for r in rows
        ]

    # ---------------------------------------------------------------- GraphStore protocol
    def visible_facts(
        self,
        owner: str,
        *,
        entity_ids: list[str] | None = None,
        subject_ids: list[str] | None = None,
        limit: int = 50,
    ) -> list[Fact]:
        """Query the visible_facts view and hydrate entities and evidence."""
        clauses = ["vf.owner = %s"]
        params: list[Any] = [owner]

        if entity_ids is not None:
            clauses.append(
                "EXISTS (SELECT 1 FROM fact_entities fe "
                "WHERE fe.owner = vf.owner AND fe.fact_id = vf.id AND fe.entity_id = ANY(%s))"
            )
            params.append(list(entity_ids))

        if subject_ids is not None:
            clauses.append("vf.subject_id = ANY(%s)")
            params.append(list(subject_ids))

        params.append(limit)
        sql = f"""
            SELECT vf.id, vf.owner, vf.text, vf.text_orig, vf.lang, vf.subject_id,
                   vf.valid_from, vf.valid_to, vf.status, vf.superseded_by,
                   vf.provenance, vf.confidence, vf.job_id, vf.attempt_id,
                   vf.worker_id, vf.model, vf.prompt_version
            FROM visible_facts vf
            WHERE {' AND '.join(clauses)}
            ORDER BY CASE WHEN vf.status = 'active' THEN 0 ELSE 1 END,
                     vf.valid_from DESC, vf.created_at DESC
            LIMIT %s
        """
        with self.db.connection() as conn:
            fact_rows = conn.execute(sql, params).fetchall()
            if not fact_rows:
                return []
            fids = [r["id"] for r in fact_rows]
            ent_rows = conn.execute(
                """
                SELECT fact_id, entity_id, role
                FROM fact_entities
                WHERE owner = %s AND fact_id = ANY(%s)
                ORDER BY entity_id ASC
                """,
                (owner, fids),
            ).fetchall()
            ev_rows = conn.execute(
                """
                SELECT fact_id, record_id
                FROM fact_evidence
                WHERE owner = %s AND fact_id = ANY(%s)
                ORDER BY record_id ASC
                """,
                (owner, fids),
            ).fetchall()

        ents_by_fact: dict[str, list[FactEntity]] = {}
        for r in ent_rows:
            ents_by_fact.setdefault(r["fact_id"], []).append(
                FactEntity(entity_id=r["entity_id"], role=r["role"])
            )

        ev_by_fact: dict[str, list[str]] = {}
        for r in ev_rows:
            ev_by_fact.setdefault(r["fact_id"], []).append(r["record_id"])

        return [
            Fact(
                id=r["id"],
                owner=r["owner"],
                text=r["text"],
                subject_id=r["subject_id"],
                valid_from=r["valid_from"],
                evidence=ev_by_fact.get(r["id"], []),
                entities=ents_by_fact.get(r["id"], []),
                text_orig=r["text_orig"],
                lang=r["lang"],
                valid_to=r["valid_to"],
                status=r["status"],
                superseded_by=r["superseded_by"],
                provenance=r["provenance"],
                confidence=r["confidence"],
                job_id=r["job_id"],
                attempt_id=r["attempt_id"],
                worker_id=r["worker_id"],
                model=r["model"],
                prompt_version=r["prompt_version"],
            )
            for r in fact_rows
        ]

    def scoped_context(self, owner: str, records: list[Record], max_tokens: int = 3000) -> dict:
        """Match entities from folded records, expand 1-hop links, and pack context within max_tokens."""
        char_budget = max(0, max_tokens * 4)
        combined_folded = fold_text(" ".join(f"{r.author} {r.text}" for r in records))
        padded_text = f" {combined_folded} " if combined_folded else ""

        with self.db.connection() as conn:
            alias_rows = conn.execute(
                """
                SELECT ea.entity_id, ea.alias, ea.alias_folded
                FROM entity_aliases ea
                JOIN entities e ON e.owner = ea.owner AND e.id = ea.entity_id
                WHERE ea.owner = %s AND e.erased_at IS NULL AND e.status <> 'merged'
                """,
                (owner,),
            ).fetchall()

            matched_ids: set[str] = set()
            aliases_by_ent: dict[str, list[str]] = {}
            for row in alias_rows:
                eid = row["entity_id"]
                aliases_by_ent.setdefault(eid, []).append(row["alias"])
                af = row["alias_folded"]
                if af and padded_text and f" {af} " in padded_text:
                    matched_ids.add(eid)

            hop1_ids: set[str] = set(matched_ids)
            if matched_ids:
                link_rows = conn.execute(
                    """
                    SELECT src, dst
                    FROM links
                    WHERE owner = %s AND erased_at IS NULL
                      AND (src = ANY(%s) OR dst = ANY(%s))
                    """,
                    (owner, list(matched_ids), list(matched_ids)),
                ).fetchall()
                for lr in link_rows:
                    hop1_ids.add(lr["src"])
                    hop1_ids.add(lr["dst"])

            ent_rows = conn.execute(
                """
                SELECT id, owner, kind, name, status, relation_to_user, closeness_tier,
                       salience, first_seen, last_seen
                FROM entities
                WHERE owner = %s AND erased_at IS NULL AND status <> 'merged'
                ORDER BY salience DESC, id ASC
                """,
                (owner,),
            ).fetchall()

            subj_rows = conn.execute(
                """
                SELECT id, owner, parent_id, path, label, kind, status, fact_count, salience, sensitive_cat
                FROM subjects
                WHERE owner = %s
                ORDER BY salience DESC, fact_count DESC, path ASC
                """,
                (owner,),
            ).fetchall()

        # Prioritize direct matches, then 1-hop neighbors, then top salience entities
        ent_rows_sorted = sorted(
            ent_rows,
            key=lambda r: (
                0 if r["id"] in matched_ids else (1 if r["id"] in hop1_ids else 2),
                -float(r["salience"]),
                r["id"],
            ),
        )

        facts: list[Fact] = []
        seen_fact_ids: set[str] = set()
        if hop1_ids:
            for f in self.visible_facts(owner, entity_ids=list(hop1_ids), limit=80):
                if f.id not in seen_fact_ids:
                    seen_fact_ids.add(f.id)
                    facts.append(f)
        for f in self.visible_facts(owner, limit=50):
            if f.id not in seen_fact_ids:
                seen_fact_ids.add(f.id)
                facts.append(f)

        subj_by_id = {r["id"]: r for r in subj_rows}
        fact_dicts = [
            {
                "id": f.id,
                "text": f.text,
                "text_orig": f.text_orig,
                "subject_id": f.subject_id,
                "subject_path": subj_by_id[f.subject_id]["path"] if f.subject_id in subj_by_id else "",
                "valid_from": f.valid_from,
                "valid_to": f.valid_to,
                "status": f.status,
                "entities": [{"entity_id": fe.entity_id, "role": fe.role} for fe in f.entities],
                "evidence": list(f.evidence),
            }
            for f in facts
        ]

        entity_dicts = [
            {
                "id": r["id"],
                "kind": r["kind"],
                "name": r["name"],
                "status": r["status"],
                "relation_to_user": r["relation_to_user"],
                "aliases": sorted(set(aliases_by_ent.get(r["id"], []))),
                "salience": float(r["salience"]),
            }
            for r in ent_rows_sorted
        ]

        referenced_subj_ids = {f.subject_id for f in facts}
        subj_rows_sorted = sorted(
            subj_rows,
            key=lambda r: (0 if r["id"] in referenced_subj_ids else 1, -float(r["salience"]), r["path"]),
        )
        subject_dicts = [
            {
                "id": r["id"],
                "path": r["path"],
                "label": r["label"],
                "kind": r["kind"],
                "status": r["status"],
                "fact_count": int(r["fact_count"]),
            }
            for r in subj_rows_sorted
        ]

        return _pack_within_budget(entity_dicts, fact_dicts, subject_dicts, char_budget)

    def _hydrate_fact_rows(self, conn: Any, owner: str, fact_rows: list[dict[str, Any]]) -> list[Fact]:
        if not fact_rows:
            return []
        fids = [r["id"] for r in fact_rows]
        ent_rows = conn.execute(
            """
            SELECT fact_id, entity_id, role
            FROM fact_entities
            WHERE owner = %s AND fact_id = ANY(%s)
            ORDER BY entity_id ASC
            """,
            (owner, fids),
        ).fetchall()
        ev_rows = conn.execute(
            """
            SELECT fact_id, record_id
            FROM fact_evidence
            WHERE owner = %s AND fact_id = ANY(%s)
            ORDER BY record_id ASC
            """,
            (owner, fids),
        ).fetchall()

        ents_by_fact: dict[str, list[FactEntity]] = {}
        for r in ent_rows:
            ents_by_fact.setdefault(r["fact_id"], []).append(
                FactEntity(entity_id=r["entity_id"], role=r["role"])
            )

        ev_by_fact: dict[str, list[str]] = {}
        for r in ev_rows:
            ev_by_fact.setdefault(r["fact_id"], []).append(r["record_id"])

        return [
            Fact(
                id=r["id"],
                owner=r["owner"],
                text=r["text"],
                subject_id=r["subject_id"],
                valid_from=r["valid_from"],
                evidence=ev_by_fact.get(r["id"], []),
                entities=ents_by_fact.get(r["id"], []),
                text_orig=r["text_orig"],
                lang=r["lang"],
                valid_to=r["valid_to"],
                status=r["status"],
                superseded_by=r["superseded_by"],
                provenance=r["provenance"],
                confidence=r["confidence"],
                job_id=r["job_id"],
                attempt_id=r["attempt_id"],
                worker_id=r["worker_id"],
                model=r["model"],
                prompt_version=r["prompt_version"],
            )
            for r in fact_rows
        ]

    # ---------------------------------------------------------------- GraphStoreFull retrieval
    def search_candidates(
        self,
        owner: str,
        query: str,
        *,
        entity_ids: list[str] | None = None,
        subject_ids: list[str] | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        source_prefix: str | None = None,
        limit: int = 50,
        include_lowered: bool = False,
    ) -> list[Candidate]:
        """Rank unique visible fact IDs via Postgres multi-channel RRF."""
        from temporal_memory.core.retrieval import search_candidates as _pg_search_candidates

        return _pg_search_candidates(
            self.db,
            owner,
            query,
            entity_ids=entity_ids,
            subject_ids=subject_ids,
            date_from=date_from,
            date_to=date_to,
            source_prefix=source_prefix,
            limit=limit,
            include_lowered=include_lowered,
        )

    def get_facts(self, owner: str, fact_ids: list[str]) -> list[Fact]:
        """Hydrate visible IDs in input order, skipping missing or repeated IDs without a cap."""
        ordered_ids = list(dict.fromkeys(fid for fid in fact_ids if fid))
        if not ordered_ids:
            return []
        with self.db.connection() as conn:
            fact_rows = conn.execute(
                """
                SELECT vf.id, vf.owner, vf.text, vf.text_orig, vf.lang, vf.subject_id,
                       vf.valid_from, vf.valid_to, vf.status, vf.superseded_by,
                       vf.provenance, vf.confidence, vf.job_id, vf.attempt_id,
                       vf.worker_id, vf.model, vf.prompt_version
                FROM visible_facts vf
                WHERE vf.owner = %s AND vf.id = ANY(%s)
                """,
                (owner, ordered_ids),
            ).fetchall()
            hydrated = self._hydrate_fact_rows(conn, owner, fact_rows)
        by_id = {f.id: f for f in hydrated}
        return [by_id[fid] for fid in ordered_ids if fid in by_id]

    def fact_counts_by_subject(self, owner: str) -> dict[str, int]:
        """Count direct visible facts by subject via SQL aggregate."""
        with self.db.connection() as conn:
            rows = conn.execute(
                """
                SELECT vf.subject_id, COUNT(*)::int AS cnt
                FROM visible_facts vf
                WHERE vf.owner = %s
                GROUP BY vf.subject_id
                """,
                (owner,),
            ).fetchall()
        return {r["subject_id"]: int(r["cnt"]) for r in rows}

    def iter_visible_facts(
        self,
        owner: str,
        *,
        date_from: str | None = None,
        date_to: str | None = None,
        after: tuple[str, str] | None = None,
        page_size: int = 500,
        lowered_only: bool = False,
    ) -> Iterator[Fact]:
        """Iterate visible facts by (valid_from, id) descending using keyset cursors."""
        if page_size < 1:
            raise ValueError("page_size must be positive")
        cursor = after
        while True:
            clauses = ["vf.owner = %s"]
            params: list[Any] = [owner]
            if lowered_only:
                clauses.append("EXISTS (SELECT 1 FROM memory_fact_weights w "
                               "WHERE (w.owner,w.id) = (vf.owner,vf.id) AND w.lowered)")
            if date_from is not None:
                clauses.append("substr(vf.valid_from, 1, 10) >= %s")
                params.append(date_from[:10])
            if date_to is not None:
                clauses.append("substr(vf.valid_from, 1, 10) <= %s")
                params.append(date_to[:10])
            if cursor is not None:
                clauses.append("(vf.valid_from, vf.id) < (%s, %s)")
                params.extend([cursor[0], cursor[1]])
            params.append(page_size)
            sql = f"""
                SELECT vf.id, vf.owner, vf.text, vf.text_orig, vf.lang, vf.subject_id,
                       vf.valid_from, vf.valid_to, vf.status, vf.superseded_by,
                       vf.provenance, vf.confidence, vf.job_id, vf.attempt_id,
                       vf.worker_id, vf.model, vf.prompt_version
                FROM visible_facts vf
                WHERE {' AND '.join(clauses)}
                ORDER BY vf.valid_from DESC, vf.id DESC
                LIMIT %s
            """
            with self.db.connection() as conn:
                fact_rows = conn.execute(sql, params).fetchall()
                batch = self._hydrate_fact_rows(conn, owner, fact_rows)
            if not batch:
                break
            for fact in batch:
                yield fact
            if len(batch) < page_size:
                break
            last = batch[-1]
            cursor = (last.valid_from, last.id)

    def bump_privacy_revision(self, owner: str) -> int:
        """Increment the owner's privacy revision and return the updated value."""
        with self.db.transaction() as conn:
            row = conn.execute(
                "UPDATE owners SET privacy_revision = privacy_revision + 1 WHERE id = %s RETURNING privacy_revision",
                (owner,),
            ).fetchone()
        return int(row["privacy_revision"]) if row else 0

    def external_versions(self, owner: str) -> tuple[int, int, int] | None:
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT alias_version, facts_version, privacy_revision, deleted_from_external "
                "FROM owners WHERE id = %s", (owner,),
            ).fetchone()
        if row is None:
            return (0, 0, 0)
        if row["deleted_from_external"]:
            return None
        return row["alias_version"], row["facts_version"], row["privacy_revision"]

    def privacy_revision(self, owner: str) -> int:
        """Read current privacy_revision for cache keying."""
        with self.db.connection() as conn:
            row = conn.execute("SELECT privacy_revision FROM owners WHERE id = %s", (owner,)).fetchone()
        return int(row["privacy_revision"]) if row else 0

    def visible_entity_ids(self, owner: str) -> set[str]:
        """Return distinct entity IDs referenced by non-sensitive-leaking visible facts."""
        with self.db.connection() as conn:
            rows = conn.execute(
                """
                SELECT DISTINCT fe.entity_id
                FROM fact_entities fe
                JOIN visible_facts vf ON vf.owner = fe.owner AND vf.id = fe.fact_id
                LEFT JOIN subjects s ON s.owner = vf.owner AND s.id = vf.subject_id
                WHERE fe.owner = %s
                  AND (
                      s.id IS NULL
                      OR (s.sensitive_cat IS NULL AND split_part(s.path, '/', 1) NOT IN ('health', 'faith'))
                      OR vf.provenance IN ('user_supplied', 'provider_confirmed')
                  )
                """,
                (owner,),
            ).fetchall()
        return {r["entity_id"] for r in rows}

    def confirmed_fact_counts_by_subject(self, owner: str) -> dict[str, int]:
        """Count visible user_supplied/provider_confirmed facts by subject."""
        with self.db.connection() as conn:
            rows = conn.execute(
                """
                SELECT vf.subject_id, COUNT(*)::int AS cnt
                FROM visible_facts vf
                WHERE vf.owner = %s
                  AND vf.provenance IN ('user_supplied', 'provider_confirmed')
                GROUP BY vf.subject_id
                """,
                (owner,),
            ).fetchall()
        return {r["subject_id"]: int(r["cnt"]) for r in rows}

    def visible_fact_ids_subset(self, owner: str, fact_ids: list[str]) -> set[str]:
        """Check visibility of an explicit list of fact IDs without scanning the table."""
        clean = list(dict.fromkeys(fid for fid in fact_ids if fid))
        if not clean:
            return set()
        with self.db.connection() as conn:
            rows = conn.execute(
                "SELECT id FROM visible_facts WHERE owner = %s AND id = ANY(%s)",
                (owner, clean),
            ).fetchall()
        return {r["id"] for r in rows}

    def list_link_evidence_map(self, owner: str) -> dict[str, list[str]]:
        """Return link_id -> visible fact_ids from link_evidence + links.evidence_fact_id."""
        with self.db.connection() as conn:
            rows = conn.execute(
                """
                SELECT le.link_id, le.fact_id
                FROM link_evidence le
                JOIN visible_facts vf ON vf.owner = le.owner AND vf.id = le.fact_id
                WHERE le.owner = %s
                ORDER BY le.link_id ASC, le.fact_id ASC
                """,
                (owner,),
            ).fetchall()
        out: dict[str, list[str]] = {}
        for r in rows:
            out.setdefault(r["link_id"], []).append(r["fact_id"])
        return out

    def list_hypotheses(self, owner: str, *, limit: int = 200) -> list[Fact]:
        """Return visible hypothesis facts bounded in SQL without a 10k scan."""
        with self.db.connection() as conn:
            rows = conn.execute(
                """
                SELECT vf.id, vf.owner, vf.text, vf.text_orig, vf.lang, vf.subject_id,
                       vf.valid_from, vf.valid_to, vf.status, vf.superseded_by,
                       vf.provenance, vf.confidence, vf.job_id, vf.attempt_id,
                       vf.worker_id, vf.model, vf.prompt_version
                FROM visible_facts vf
                LEFT JOIN subjects s ON s.owner = vf.owner AND s.id = vf.subject_id
                WHERE vf.owner = %s AND vf.status = 'hypothesis'
                  AND (s.id IS NULL OR (s.sensitive_cat IS NULL AND split_part(s.path, '/', 1) NOT IN ('health', 'faith')))
                ORDER BY vf.valid_from DESC, vf.id DESC
                LIMIT %s
                """,
                (owner, limit),
            ).fetchall()
            return self._hydrate_fact_rows(conn, owner, rows)

    def list_open_changes(
        self,
        owner: str,
        *,
        entity_ids: list[str] | None = None,
        fact_ids: list[str] | None = None,
        limit: int = 16,
    ) -> list[tuple[Fact, str | None]]:
        """Return visible superseded/ended facts relevant to entity_ids/fact_ids with replacement text."""
        eids = list(entity_ids or [])
        fids = list(fact_ids or [])
        if not eids and not fids:
            return []
        with self.db.connection() as conn:
            rows = conn.execute(
                """
                SELECT vf.id, vf.owner, vf.text, vf.text_orig, vf.lang, vf.subject_id,
                       vf.valid_from, vf.valid_to, vf.status, vf.superseded_by,
                       vf.provenance, vf.confidence, vf.job_id, vf.attempt_id,
                       vf.worker_id, vf.model, vf.prompt_version,
                       sup.text AS sup_text
                FROM visible_facts vf
                LEFT JOIN visible_facts sup ON sup.owner = vf.owner AND sup.id = vf.superseded_by
                LEFT JOIN subjects s ON s.owner = vf.owner AND s.id = vf.subject_id
                WHERE vf.owner = %s
                  AND vf.status IN ('superseded', 'ended')
                  AND (s.id IS NULL OR (s.sensitive_cat IS NULL AND split_part(s.path, '/', 1) NOT IN ('health', 'faith'))
                       OR vf.provenance IN ('user_supplied', 'provider_confirmed'))
                  AND (
                      vf.id = ANY(%s)
                      OR EXISTS (
                          SELECT 1 FROM fact_entities fe
                          WHERE fe.owner = vf.owner AND fe.fact_id = vf.id AND fe.entity_id = ANY(%s)
                      )
                  )
                ORDER BY vf.valid_from DESC, vf.id ASC
                LIMIT %s
                """,
                (owner, fids, eids, limit),
            ).fetchall()
            hydrated = self._hydrate_fact_rows(conn, owner, rows)
        sup_map = {r["id"]: r["sup_text"] for r in rows}
        return [(f, sup_map.get(f.id)) for f in hydrated]

    def entity_salience_map(self, owner: str, *, entity_ids: list[str] | None = None) -> dict[str, float]:
        from temporal_memory.core.retrieval import compute_entity_salience_sql

        with self.db.connection() as conn:
            return compute_entity_salience_sql(conn, owner, entity_ids=entity_ids)

    def subject_salience_map(self, owner: str) -> dict[str, float]:
        from temporal_memory.core.retrieval import compute_subject_salience_sql

        with self.db.connection() as conn:
            return compute_subject_salience_sql(conn, owner)

    # ---------------------------------------------------------------- query helpers for vault/ops/ingest
    def list_entities(self, owner: str) -> list[Entity]:
        with self.db.connection() as conn:
            rows = conn.execute(
                """
                SELECT id, owner, kind, name, status, relation_to_user, closeness_tier,
                       salience, first_seen, last_seen,
                       provenance, user_confirmed_at, closeness_suggested,
                       closeness_suggested_evidence, tier_confirmed_at, salience_updated_at
                FROM entities
                WHERE owner = %s AND erased_at IS NULL
                ORDER BY salience DESC, id ASC
                """,
                (owner,),
            ).fetchall()
            alias_rows = conn.execute(
                "SELECT entity_id, alias FROM entity_aliases WHERE owner = %s ORDER BY alias ASC",
                (owner,),
            ).fetchall()

        aliases_map: dict[str, list[str]] = {}
        for ar in alias_rows:
            aliases_map.setdefault(ar["entity_id"], []).append(ar["alias"])

        return [
            Entity(
                id=r["id"],
                owner=r["owner"],
                kind=r["kind"],
                name=r["name"],
                status=r["status"],
                relation_to_user=r["relation_to_user"],
                closeness_tier=r["closeness_tier"],
                aliases=aliases_map.get(r["id"], []),
                salience=float(r["salience"]),
                first_seen=r["first_seen"],
                last_seen=r["last_seen"],
                provenance=r["provenance"] or "inferred",
                user_confirmed_at=_as_iso(r["user_confirmed_at"]),
                closeness_suggested=r["closeness_suggested"],
                closeness_suggested_evidence=(
                    _as_json_list(r["closeness_suggested_evidence"])
                    if r["closeness_suggested_evidence"] is not None
                    else None
                ),
                tier_confirmed_at=_as_iso(r["tier_confirmed_at"]),
                salience_updated_at=_as_iso(r["salience_updated_at"]),
            )
            for r in rows
        ]

    def list_subjects(self, owner: str) -> list[Subject]:
        with self.db.connection() as conn:
            rows = conn.execute(
                """
                SELECT id, owner, path, label, kind, parent_id, status, fact_count,
                       salience, sensitive_cat, provenance, user_confirmed_at
                FROM subjects
                WHERE owner = %s
                ORDER BY salience DESC, path ASC
                """,
                (owner,),
            ).fetchall()
        return [
            Subject(
                id=r["id"],
                owner=r["owner"],
                path=r["path"],
                label=r["label"],
                kind=r["kind"],
                parent_id=r["parent_id"],
                status=r["status"],
                fact_count=int(r["fact_count"]),
                salience=float(r["salience"]),
                sensitive_cat=r["sensitive_cat"],
                provenance=r["provenance"] or "inferred",
                user_confirmed_at=_as_iso(r["user_confirmed_at"]),
            )
            for r in rows
        ]

    def list_links(self, owner: str) -> list[Link]:
        with self.db.connection() as conn:
            rows = conn.execute(
                """
                SELECT id, owner, src, rel, dst, valid_from, valid_to, evidence_fact_id
                FROM links
                WHERE owner = %s AND erased_at IS NULL
                ORDER BY id ASC
                """,
                (owner,),
            ).fetchall()
        return [
            Link(
                id=r["id"],
                owner=r["owner"],
                src=r["src"],
                rel=r["rel"],
                dst=r["dst"],
                valid_from=r["valid_from"],
                valid_to=r["valid_to"],
                evidence_fact_id=r["evidence_fact_id"],
            )
            for r in rows
        ]

    def list_entity_subjects(self, owner: str) -> list[EntitySubject]:
        with self.db.connection() as conn:
            rows = conn.execute(
                """
                SELECT entity_id, subject_id, role, weight, fact_count, first_seen, last_seen
                FROM entity_subjects
                WHERE owner = %s
                ORDER BY weight DESC, fact_count DESC, entity_id ASC
                """,
                (owner,),
            ).fetchall()
        return [
            EntitySubject(
                entity_id=r["entity_id"],
                subject_id=r["subject_id"],
                role=r["role"] or None,
                weight=float(r["weight"]),
                fact_count=int(r["fact_count"]),
                first_seen=r["first_seen"],
                last_seen=r["last_seen"],
            )
            for r in rows
        ]

    def list_milestones(self, owner: str) -> list[Milestone]:
        with self.db.connection() as conn:
            rows = conn.execute(
                """
                SELECT id, owner, subject_id, title, state, evidence_fact_ids
                FROM milestones
                WHERE owner = %s
                ORDER BY id ASC
                """,
                (owner,),
            ).fetchall()
        return [
            Milestone(
                id=r["id"],
                owner=r["owner"],
                subject_id=r["subject_id"],
                title=r["title"],
                state=r["state"],
                evidence_fact_ids=_as_json_list(r["evidence_fact_ids"]),
            )
            for r in rows
        ]

    def get_attempt(self, attempt_id: str) -> Attempt | None:
        with self.db.connection() as conn:
            row = conn.execute(
                """
                SELECT id, job_id, owner, attempt_no, fence_token, worker_id, worker_kind,
                       model, model_observed, prompt_version, started_at, finished_at, tokens_in, tokens_out,
                       cost_usd, output_json, verdict
                FROM job_attempts
                WHERE id = %s
                """,
                (attempt_id,),
            ).fetchone()
        return self._row_to_attempt(row) if row else None

    def alias_version(self, owner: str) -> int:
        with self.db.connection() as conn:
            row = conn.execute("SELECT alias_version FROM owners WHERE id = %s", (owner,)).fetchone()
        return int(row["alias_version"]) if row else 0

    def facts_version(self, owner: str) -> int:
        with self.db.connection() as conn:
            row = conn.execute("SELECT facts_version FROM owners WHERE id = %s", (owner,)).fetchone()
        return int(row["facts_version"]) if row else 0

    def owner_generation(self, owner: str) -> int:
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT GREATEST(COALESCE(MAX(r.generation), 0), COALESCE(MAX(o.deletion_generation), 0)) AS g "
                "FROM owners o LEFT JOIN records r ON r.owner = o.id WHERE o.id = %s", (owner,),
            ).fetchone()
        return int(row["g"]) if row else 0

    def add_alias(self, owner: str, entity_id: str, alias: str) -> None:
        af = fold_text(alias)
        if not af:
            return
        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO entity_aliases (owner, entity_id, alias, alias_folded, source)
                VALUES (%s, %s, %s, %s, 'user')
                ON CONFLICT (owner, alias_folded, entity_id) DO NOTHING
                """,
                (owner, entity_id, alias.strip(), af),
            )
            conn.execute("UPDATE owners SET alias_version = alias_version + 1 WHERE id = %s", (owner,))

    def _ensure_subject_path(self, conn: Any, owner: str, subject_path: str, kind_leaf: str = "topic", label_override: str | None = None) -> str:
        parts = [p.strip() for p in subject_path.strip("/").split("/") if p.strip()] or ["general"]
        parent_id: str | None = None
        cur_id = ""
        for idx, part in enumerate(parts):
            seg = "/".join(parts[: idx + 1])
            row = conn.execute("SELECT id FROM subjects WHERE owner = %s AND path = %s", (owner, seg)).fetchone()
            if row is not None:
                cur_id = row["id"]
            else:
                cur_id = f"s_{uuid.uuid4().hex[:12]}"
                is_last = idx == len(parts) - 1
                skind = kind_leaf if is_last else ("theme" if idx == 0 else "topic")
                slabel = (label_override or part) if is_last else part.replace("-", " ").title()
                conn.execute(
                    """
                    INSERT INTO subjects (id, owner, parent_id, path, label, kind, status)
                    VALUES (%s, %s, %s, %s, %s, %s, 'candidate')
                    ON CONFLICT (owner, path) DO NOTHING
                    """,
                    (cur_id, owner, parent_id, seg, slabel, skind),
                )
                row2 = conn.execute("SELECT id FROM subjects WHERE owner = %s AND path = %s", (owner, seg)).fetchone()
                cur_id = row2["id"]
            parent_id = cur_id
        return cur_id

    def add_hypothesis_fact(
        self,
        owner: str,
        *,
        text: str,
        subject_path: str,
        valid_from: str,
        evidence: list[str],
    ) -> str:
        fid = f"hyp_{uuid.uuid4().hex[:12]}"
        tf = fold_text(text)
        with self.db.transaction() as conn:
            sid = self._ensure_subject_path(conn, owner, subject_path)
            chash = hashlib.sha256(f"{sid}|{tf}".encode("utf-8")).hexdigest()
            conn.execute(
                """
                INSERT INTO facts (
                    id, owner, text, text_folded, subject_id, valid_from, status, provenance, content_hash
                )
                VALUES (%s, %s, %s, %s, %s, %s, 'hypothesis', 'inferred', %s)
                """,
                (fid, owner, text, tf, sid, valid_from, chash),
            )
            for rid in dict.fromkeys(evidence):
                exists = conn.execute("SELECT generation FROM records WHERE owner = %s AND id = %s", (owner, rid)).fetchone()
                if exists is not None:
                    conn.execute(
                        """
                        INSERT INTO fact_evidence (owner, fact_id, record_id, record_generation)
                        VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING
                        """,
                        (owner, fid, rid, int(exists["generation"])),
                    )
            conn.execute("UPDATE owners SET facts_version = facts_version + 1 WHERE id = %s", (owner,))
        return fid

    def add_hypothesis_milestone(
        self,
        owner: str,
        *,
        title: str,
        subject_path: str,
        state: str,
        evidence_fact_ids: list[str],
    ) -> str:
        mid = f"ms_{uuid.uuid4().hex[:12]}"
        with self.db.transaction() as conn:
            sid = self._ensure_subject_path(conn, owner, subject_path, kind_leaf="goal", label_override=title)
            conn.execute(
                """
                INSERT INTO milestones (id, owner, subject_id, title, state, evidence_fact_ids)
                VALUES (%s, %s, %s, %s, %s, %s::jsonb)
                """,
                (mid, owner, sid, title, state, json.dumps(list(evidence_fact_ids))),
            )
        return mid

    def job_created_at(self, job_id: str) -> str | None:
        with self.db.connection() as conn:
            row = conn.execute("SELECT created_at FROM jobs WHERE id = %s", (job_id,)).fetchone()
        return _as_iso(row["created_at"]) if row else None

    def get_quarantine_counts(self, owner: str) -> dict[str, int]:
        with self.db.connection() as conn:
            rows = conn.execute(
                """
                SELECT category, COUNT(*)::int AS cnt
                FROM quarantine
                WHERE owner = %s AND status = 'held'
                GROUP BY category
                """,
                (owner,),
            ).fetchall()
        return {r["category"]: int(r["cnt"]) for r in rows}

    def list_jobs(self, owner: str | None = None, state: str | None = None, limit: int = 200) -> list[Job]:
        clauses: list[str] = []
        params: list[Any] = []
        if owner is not None:
            clauses.append("owner = %s")
            params.append(owner)
        if state is not None:
            clauses.append("state = %s")
            params.append(state)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(limit)
        with self.db.connection() as conn:
            rows = conn.execute(
                f"""
                SELECT id, owner, kind, priority, pool, input_ref, input_version,
                       context_hash, prompt_version, day, state, attempt_no,
                       fence_token, worker_id, lease_expires_at
                FROM jobs
                {where}
                ORDER BY priority ASC, created_at DESC
                LIMIT %s
                """,
                params,
            ).fetchall()
        return [
            Job(
                id=r["id"],
                owner=r["owner"],
                kind=r["kind"],
                priority=int(r["priority"]),  # type: ignore[arg-type]
                pool=r["pool"],
                input_ref=_as_json_list(r["input_ref"]),
                input_version=int(r["input_version"]),
                context_hash=r["context_hash"],
                prompt_version=r["prompt_version"],
                day=r["day"],
                state=r["state"],
                attempt_no=int(r["attempt_no"]),
                fence_token=r["fence_token"],
                worker_id=r["worker_id"],
                lease_expires_at=_as_iso(r["lease_expires_at"]),
            )
            for r in rows
        ]

    def list_workers(self) -> list[Worker]:
        with self.db.connection() as conn:
            rows = conn.execute(
                "SELECT id, kind, model, runner, owner, released FROM workers ORDER BY id ASC"
            ).fetchall()
        return [
            Worker(
                id=r["id"],
                kind=r["kind"],
                model=r["model"],
                runner=r["runner"],
                owner=r["owner"],
                released=bool(r["released"]),
            )
            for r in rows
        ]

    def list_attempts(self, job_id: str | None = None, owner: str | None = None, limit: int = 200) -> list[Attempt]:
        clauses: list[str] = []
        params: list[Any] = []
        if job_id is not None:
            clauses.append("job_id = %s")
            params.append(job_id)
        if owner is not None:
            clauses.append("owner = %s")
            params.append(owner)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(limit)
        with self.db.connection() as conn:
            rows = conn.execute(
                f"""
                SELECT id, job_id, owner, attempt_no, fence_token, worker_id, worker_kind,
                       model, model_observed, prompt_version, started_at, finished_at, tokens_in, tokens_out,
                       cost_usd, output_json, verdict
                FROM job_attempts
                {where}
                ORDER BY finished_at DESC, attempt_no DESC
                LIMIT %s
                """,
                params,
            ).fetchall()
        return [self._row_to_attempt(r) for r in rows]

    # ---------------------------------------------------------------- row mappers
    @staticmethod
    def _row_to_owner(row: dict[str, Any]) -> Owner:
        return Owner(
            id=row["id"],
            label=row["label"],
            kind=row["kind"],
            display_name=row["display_name"],
            self_aliases=_as_json_list(row["self_aliases"]),
            timezone=row["timezone"],
            privacy_revision=int(row.get("privacy_revision", 0) or 0),
        )

    @staticmethod
    def _row_to_attempt(row: dict[str, Any]) -> Attempt:
        att = Attempt(
            job_id=row["job_id"],
            attempt_no=int(row["attempt_no"]),
            fence_token=row["fence_token"],
            worker_id=row["worker_id"],
            worker_kind=row["worker_kind"],
            model=row["model"],
            prompt_version=row["prompt_version"],
            output=row["output_json"],
            tokens_in=int(row["tokens_in"]),
            tokens_out=int(row["tokens_out"]),
            cost_usd=float(row["cost_usd"]),
            started_at=_as_iso(row["started_at"]),
            finished_at=_as_iso(row["finished_at"]),
            model_observed=row.get("model_observed"),
        )
        setattr(att, "verdict", row["verdict"])
        return att


def visible_facts(
    owner: str,
    *,
    entity_ids: list[str] | None = None,
    subject_ids: list[str] | None = None,
    limit: int = 50,
    db: Database | None = None,
) -> list[Fact]:
    """Module-level convenience wrapper used by privacy.forget tests."""
    return PostgresGraphStore(db or get_database()).visible_facts(
        owner, entity_ids=entity_ids, subject_ids=subject_ids, limit=limit
    )


def _pack_within_budget(
    entities: list[dict[str, Any]],
    facts: list[dict[str, Any]],
    subjects: list[dict[str, Any]],
    char_budget: int,
) -> dict[str, list[dict[str, Any]]]:
    """Greedily pack entities, subjects, and facts without exceeding char_budget."""
    packed: dict[str, list[dict[str, Any]]] = {"entities": [], "facts": [], "subjects": []}
    if char_budget <= 0:
        return packed

    base_len = len(json.dumps(packed, ensure_ascii=False))
    used = base_len

    def _try_add(bucket: str, items: list[dict[str, Any]], max_share: int) -> None:
        nonlocal used
        bucket_used = 0
        for item in items:
            cost = len(json.dumps(item, ensure_ascii=False)) + 2
            if used + cost > char_budget or bucket_used + cost > max_share:
                break
            packed[bucket].append(item)
            used += cost
            bucket_used += cost

    _try_add("entities", entities, int(char_budget * 0.30))
    _try_add("subjects", subjects, int(char_budget * 0.20))
    _try_add("facts", facts, char_budget)
    return packed
