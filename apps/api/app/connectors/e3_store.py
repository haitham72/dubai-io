"""E3 consent, receipts and owner-scoped temporal_memory transport."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from hashlib import sha256
import itertools
import os
from urllib.parse import quote
from zoneinfo import ZoneInfo

from fastapi import HTTPException
import httpx
import psycopg
from psycopg.rows import dict_row

from .crypto import decrypt_json, encrypt_json

SOURCES = {
    "gmail": ("gmail", "gmail:%"),
    "calendar": ("calendar", "calendar:%", "gcal:%", "google:calendar%"),
    "youtube": ("youtube:api%", "youtube_api%", "youtube-api%"),
    "takeout": ("takeout:%",),
    "whatsapp": ("whatsapp", "whatsapp:%"),
    "browser": ("browser", "browser:%"),
    "agent_sessions": ("agent:%", "dev_sessions", "ai:chatgpt%"),
}


def _source_sql(alias="r"):
    return (
        f"({alias}.source LIKE ANY(%s) OR "
        f"(%s='takeout' AND {alias}.source='youtube:interests' AND starts_with({alias}.id,'e3:takeout:')))"
    )


def utcnow():
    return datetime.now(timezone.utc)


def measured(value, provenance="provider_confirmed", now=None):
    return {"value": value, "provenance": provenance, "as_of": (now or utcnow()).isoformat()}


class State:
    def __init__(self, dsn, cipher):
        self.dsn, self.cipher = dsn, cipher
        with self.connection() as conn:
            with conn.transaction():
                conn.execute("SELECT pg_advisory_xact_lock(hashtext('e3:ingest:schema'))")
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS e3_ingest_sources (
                        owner TEXT NOT NULL, source TEXT NOT NULL, enabled BOOL NOT NULL DEFAULT FALSE,
                        revision BIGINT NOT NULL DEFAULT 0, last_pull TIMESTAMPTZ, grant_cipher BYTEA,
                        PRIMARY KEY(owner,source)
                    );
                    CREATE TABLE IF NOT EXISTS e3_ingest_oauth (
                        state_hash TEXT PRIMARY KEY, owner TEXT NOT NULL, expires TIMESTAMPTZ NOT NULL,
                        payload BYTEA NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS e3_ingest_google_accounts (
                        owner TEXT PRIMARY KEY, subject TEXT UNIQUE NOT NULL
                    );
                """)

    def connection(self):
        return psycopg.connect(self.dsn, autocommit=True, row_factory=dict_row, connect_timeout=5)

    @contextmanager
    def lock(self, owner, source):
        # A session lock serializes committed writes with disable and Forget across API processes.
        with self.connection() as conn:
            conn.execute("SELECT pg_advisory_lock(hashtextextended(%s,0))", (f"e3:{owner}:{source}",))
            yield conn

    def source(self, conn, owner, source):
        row = conn.execute(
            "SELECT enabled,revision,last_pull,grant_cipher FROM e3_ingest_sources WHERE owner=%s AND source=%s",
            (owner, source),
        ).fetchone()
        return row or {"enabled": False, "revision": 0, "last_pull": None, "grant_cipher": None}

    def require(self, conn, owner, source, revision=None):
        state = self.source(conn, owner, source)
        if not state["enabled"]:
            raise HTTPException(403, "Enable this source before importing data")
        if revision is not None and state["revision"] != revision:
            raise HTTPException(409, "Source consent changed during this operation")
        return state

    def set_consent(self, conn, owner, source, enabled):
        conn.execute(
            """INSERT INTO e3_ingest_sources (owner,source,enabled) VALUES (%s,%s,%s)
               ON CONFLICT (owner,source) DO UPDATE SET enabled=excluded.enabled,
                  revision=e3_ingest_sources.revision+1,
                  grant_cipher=CASE WHEN excluded.enabled THEN e3_ingest_sources.grant_cipher ELSE NULL END
               WHERE e3_ingest_sources.enabled IS DISTINCT FROM excluded.enabled""",
            (owner, source, enabled),
        )

    def grant(self, row):
        return decrypt_json(self.cipher, row["grant_cipher"]) if row["grant_cipher"] else None

    def save_grant(self, conn, owner, source, grant):
        conn.execute(
            "UPDATE e3_ingest_sources SET grant_cipher=%s WHERE owner=%s AND source=%s",
            (encrypt_json(self.cipher, grant), owner, source),
        )

    def authorize_attempt(self, owner, key, payload, expires):
        with self.connection() as conn:
            conn.execute("DELETE FROM e3_ingest_oauth WHERE expires<=now()")
            conn.execute(
                "INSERT INTO e3_ingest_oauth (state_hash,owner,expires,payload) VALUES (%s,%s,%s,%s)",
                (sha256(key.encode()).hexdigest(), owner, expires, encrypt_json(self.cipher, payload)),
            )

    def consume_attempt(self, owner, key):
        with self.connection() as conn:
            row = conn.execute(
                "DELETE FROM e3_ingest_oauth WHERE state_hash=%s AND owner=%s AND expires>now() RETURNING payload",
                (sha256(key.encode()).hexdigest(), owner),
            ).fetchone()
        payload = decrypt_json(self.cipher, row["payload"]) if row else None
        if not payload:
            raise HTTPException(400, "Google authorization expired or belongs to another session")
        return payload

    @staticmethod
    def mark_pulled(conn, owner, source, now):
        conn.execute(
            "UPDATE e3_ingest_sources SET last_pull=%s WHERE owner=%s AND source=%s",
            (now, owner, source),
        )

    @staticmethod
    def record_ids(conn, owner, source):
        return [
            row["id"] for row in conn.execute(
                f"SELECT id FROM records r WHERE r.owner=%s AND r.erased_at IS NULL AND {_source_sql()} ORDER BY id",
                (owner, list(SOURCES[source]), source),
            )
        ]

    def statistics(self, conn, owner, source, now):
        row = self.source(conn, owner, source)
        keys = (owner, list(SOURCES[source]), source)
        result = conn.execute(
            f"""
            WITH inputs AS (
              SELECT id FROM records r WHERE r.owner=%s AND r.erased_at IS NULL AND {_source_sql()}
            ), source_jobs AS (
              SELECT j.id,j.state FROM jobs j WHERE j.owner=%s AND j.kind IN ('extract.day','extract.session','extract.live')
              AND EXISTS (SELECT 1 FROM inputs i WHERE i.id=ANY(j.input_ref))
            )
            SELECT (SELECT count(*) FROM inputs) AS records,
                   count(*) FILTER (WHERE state IN ('queued','leased','submitted','expired','rejected')) AS queued,
                   count(*) FILTER (WHERE state='applied') AS done,
                   count(*) FILTER (WHERE state='dead') AS failed
            FROM source_jobs
            """,
            (*keys, owner),
        ).fetchone()
        return {
            "enabled": row["enabled"], "connected": bool(row["enabled"] and self.grant(row)),
            "last_pull": measured(row["last_pull"].isoformat() if row["last_pull"] else None, now=now),
            **{key: measured(value, now=now) for key, value in result.items()},
        }


class Bridge:
    def __init__(self, base_url, owner_token, *, transport=None):
        self.base_url, self.owner_token, self.transport = base_url, owner_token, transport

    def request(self, owner, method, path, *, body=None, device_token=None):
        token = device_token or self.owner_token(owner)
        url = f"{self.base_url}/v1/owners/{quote(owner, safe='')}/{path}"
        try:
            with httpx.Client(timeout=30, transport=self.transport) as client:
                response = client.request(method, url, headers={"Authorization": f"Bearer {token}"}, json=body)
        except httpx.HTTPError as exc:
            raise HTTPException(503, "Memory bridge is unavailable") from exc
        if device_token and response.status_code in (401, 403):
            raise HTTPException(403, "Memory device token is invalid for this owner")
        if not response.is_success:
            raise HTTPException(409 if response.status_code == 409 else 502, "Memory bridge did not accept the request")
        return response.json()

    def ingest(self, conn, owner, records, *, device_token=None):
        info = conn.execute("SELECT timezone FROM owners WHERE id=%s", (owner,)).fetchone()
        zona = ZoneInfo(info["timezone"] if info else "Asia/Dubai")
        prepared = {}
        for record in records:
            try:
                stamp = datetime.fromisoformat(record["at"].replace("Z", "+00:00"))
            except ValueError:
                continue
            if stamp.tzinfo is None:
                stamp = stamp.replace(tzinfo=zona)
            normalized = {**record, "at": stamp.astimezone(zona).isoformat()}
            prepared[record["id"]] = normalized
        if not prepared:
            return 0, 0, 0
        # Match the bridge's record fingerprint, including the owner-local timestamp.
        fingerprints = {rid: _record_hash(record) for rid, record in prepared.items()}
        ids, hashes = list(prepared), list(fingerprints.values())
        prior = conn.execute(
            """SELECT id,content_hash,erased_at FROM records
               WHERE owner=%s AND (id=ANY(%s) OR content_hash=ANY(%s))""",
            (owner, ids, hashes),
        ).fetchall()
        by_id = {row["id"]: row for row in prior}
        by_hash = {row["content_hash"]: row for row in prior if row["erased_at"] is None}
        already_queued = {
            row["record_id"] for row in conn.execute(
                """SELECT DISTINCT unnest(input_ref) AS record_id FROM jobs
                   WHERE owner=%s AND kind='extract.day' AND input_ref && %s""",
                (owner, list(by_id)),
            )
        } if by_id else set()
        forgotten = {
            row["value"] for row in conn.execute(
                "SELECT value FROM forget_rules WHERE owner=%s AND kind='item' AND value=ANY(%s)",
                (owner, ids + hashes),
            )
        }
        scheduled = {}
        seen_hashes = set()
        skipped = 0
        for rid, record in prepared.items():
            digest = fingerprints[rid]
            existing = by_id.get(rid) or by_hash.get(digest)
            if rid in forgotten or digest in forgotten or digest in seen_hashes:
                skipped += 1
                continue
            seen_hashes.add(digest)
            if existing:
                skipped += 1
                if (existing["erased_at"] is None and existing["id"] not in already_queued
                        and existing["content_hash"] == digest):
                    # Recover a bridge call that saved records but failed before enqueue.
                    scheduled[existing["id"]] = {**record, "id": existing["id"]}
            else:
                scheduled[rid] = record
        to_send = sorted(scheduled.values(), key=lambda record: (record["at"], record["id"]))
        accepted = set()
        jobs = set()
        for _, group in itertools.groupby(to_send, key=lambda record: record["at"][:10]):
            for packet in _packets(group):
                receipt = self.request(owner, "POST", "records", body={"records": packet, "enqueue": "extract.day"},
                                       device_token=device_token)
                accepted.update(rid for rid in receipt["record_ids"] if rid in scheduled and rid not in by_id)
                if receipt["job_id"]:
                    jobs.add(receipt["job_id"])
        return len(accepted), skipped, len(jobs)



def _record_hash(record):
    value = chr(0).join(record[key] for key in ("source", "at", "author", "text"))
    return sha256(value.encode("utf-8")).hexdigest()


def _packets(records):
    # Cap each day packet independently. The same date can have several bounded jobs.
    packet, size = [], 0
    for record in records:
        weight = len(record["text"].encode()) + 160
        if packet and (size + weight > 12_000 or len(packet) >= 60):
            yield packet
            packet, size = [], 0
        packet.append(record)
        size += weight
    if packet:
        yield packet
