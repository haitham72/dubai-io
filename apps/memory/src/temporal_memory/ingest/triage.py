"""Deterministic ingest triage, forget-rule blocking, and day-packet job routing (WP-D)."""
from __future__ import annotations

import hashlib
import re
from typing import Any

from temporal_memory.core.graph_store import PostgresGraphStore
from temporal_memory.db.db import Database, get_database
from temporal_memory.models import Job, Pool, Record
from temporal_memory.core.daytime import local_day
from temporal_memory.privacy.sensitive import pre_write
from temporal_memory.queue.jobs import PostgresJobs
from .whatsapp import MEDIA

_NOISE_SENDER = re.compile(
    r"(no-?reply|do-?not-?reply|mailer-daemon|newsletter|notifications?|"
    r"updates?@|news@|info@|alerts?@|deals?@|offers?@|digest@|verify@)",
    re.I,
)

_OTP_TEXT = re.compile(
    r"(?:"
    r"\byour (?:verification |security |login |one-time )?(?:code|otp|pin|passcode) is\s*\d{4,8}\b"
    r"|\b(?:otp|verification code|security code|login code|one-time (?:password|code))\b[^\n]{0,60}\b\d{4,8}\b"
    r"|\b\d{4,8}\b[^\n]{0,40}\bexpires in \d+ min"
    r"|\bnever share (?:this|your) (?:code|otp)\b"
    r"|\bnever share it\b"
    r")",
    re.I,
)

_PROMO_NEWSLETTER = re.compile(
    r"(?:"
    r"\bunsubscribe\b"
    r"|\bflash sale\b"
    r"|\blimited-time offers?\b"
    r"|\bexclusive coupon\b"
    r"|\bshop before midnight\b"
    r"|\bprice drop on your wishlist\b"
    r"|\bnew arrivals you may like\b"
    r"|\bweekend deals inside\b"
    r"|\bview (?:this email )?in (?:your )?browser\b"
    r"|\bread the full digest in your browser\b"
    r"|\bstories you missed\b"
    r"|\bsunday digest\b"
    r"|\bweekly digest\b"
    r"|\bthis week in ai\b"
    r"|\bweekly job picks\b"
    r"|\broles may interest you\b"
    r"|\bupdate preferences anytime\b"
    r")",
    re.I,
)


def _record_hash(rec: Record) -> str:
    payload = f"{rec.source}\0{rec.at}\0{rec.author}\0{rec.text}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _extract_fields(msg: Any) -> tuple[str, str, str, str, dict[str, Any]]:
    if isinstance(msg, dict):
        text = str(msg.get("text") or msg.get("body") or "")
        sender = str(msg.get("from_addr") or msg.get("from") or msg.get("sender") or msg.get("author") or "")
        kind = str(msg.get("kind") or "message")
        meta = msg.get("meta") if isinstance(msg.get("meta"), dict) else msg
        subject = str(meta.get("subject") or "")
        return text, subject, sender, kind, meta
    text = str(getattr(msg, "text", "") or "")
    meta = getattr(msg, "meta", None)
    meta_dict = meta if isinstance(meta, dict) else {}
    subject = str(meta_dict.get("subject") or "")
    sender = str(
        meta_dict.get("from_addr")
        or meta_dict.get("from")
        or getattr(msg, "sender", None)
        or getattr(msg, "author", None)
        or ""
    )
    kind = str(getattr(msg, "kind", "message") or "message")
    return text, subject, sender, kind, meta_dict


# Account-state receipts the user would want kept: a cancellation or an
# unsubscribe confirmation. Promo mail that merely links to "unsubscribe"
# does not match.
_TRANSACTIONAL_ACCOUNT = re.compile(
    r"(?:"
    r"\bsubscription cancelled\b"
    r"|\byour [\w .'-]{0,48}subscription (?:ends|ended|was cancelled|is cancelled|has ended)\b"
    r"|\byou (?:are|have been) unsubscribed\b"
    r")",
    re.I,
)


def is_noise_email(msg: Any) -> bool:
    """Return True if an email message is promo, OTP, newsletter, bulk, or automated alert noise."""
    text, subject, sender, _kind, meta = _extract_fields(msg)
    if not text.strip() and not subject.strip():
        return True
    combined = f"{subject}\n{text}" if subject else text
    if _OTP_TEXT.search(combined):
        return True
    if _TRANSACTIONAL_ACCOUNT.search(combined):
        return False
    if meta.get("bulk") or meta.get("list_unsubscribe"):
        return True
    if str(meta.get("precedence") or "").lower() in {"bulk", "list", "junk"}:
        return True
    if sender and _NOISE_SENDER.search(sender):
        return True
    return bool(_PROMO_NEWSLETTER.search(combined))


def is_noise_whatsapp(msg: Any) -> bool:
    """Return True if a WhatsApp message is empty, pure media stub, OTP, or promo/newsletter."""
    text, _subject, _sender, kind, _meta = _extract_fields(msg)
    stripped = text.strip()
    if not stripped:
        return True
    if kind == "media" or MEDIA.match(stripped):
        return True
    return bool(_OTP_TEXT.search(stripped) or _PROMO_NEWSLETTER.search(stripped))


def _matches_forget_rule(
    kind: str,
    value: str,
    record_id: str,
    *,
    source: str | None = None,
    text: str | None = None,
) -> bool:
    if kind == "item":
        return value == record_id
    if kind == "source":
        if source is not None and (source == value or source.startswith(value)):
            return True
        return value == record_id or record_id.startswith(value)
    if kind == "text":
        return bool(text and value and value.lower() in text.lower())
    return False


def is_forgotten(
    owner: str,
    record_id: str,
    *,
    source: str | None = None,
    content_hash: str | None = None,
    text: str | None = None,
    db: Database | None = None,
) -> bool:
    """Check whether a record is erased, generation-bumped, or blocked by a forget_rules entry."""
    database = db or get_database()
    with database.connection() as conn:
        row = conn.execute(
            "SELECT erased_at, generation, source, text FROM records WHERE owner = %s AND id = %s",
            (owner, record_id),
        ).fetchone()
        if row is not None:
            if row["erased_at"] is not None or int(row["generation"]) > 0:
                return True
            if source is None:
                source = row["source"]
            if text is None:
                text = row["text"]

        if content_hash is not None:
            hash_row = conn.execute(
                """
                SELECT 1 FROM records
                WHERE owner = %s AND content_hash = %s
                  AND (erased_at IS NOT NULL OR generation > 0)
                LIMIT 1
                """,
                (owner, content_hash),
            ).fetchone()
            if hash_row is not None:
                return True

        rules = conn.execute(
            "SELECT kind, value FROM forget_rules WHERE owner = %s",
            (owner,),
        ).fetchall()

    return any(
        _matches_forget_rule(r["kind"], r["value"], record_id, source=source, text=text)
        for r in rules
    )


def owner_has_active_device(db: Database, owner: str) -> bool:
    """Return True if the owner has at least one non-revoked owner-device token."""
    with db.connection() as conn:
        row = conn.execute(
            """
            SELECT 1 FROM tokens
            WHERE owner = %s AND role = 'owner-device' AND revoked_at IS NULL
            LIMIT 1
            """,
            (owner,),
        ).fetchone()
    return row is not None


def _is_triage_noise(rec: Record) -> bool:
    if not rec.text.strip():
        return True
    if rec.source.startswith("whatsapp"):
        return is_noise_whatsapp(rec)
    if rec.source == "gmail" or rec.source == "email" or rec.source.startswith("email:"):
        return is_noise_email(rec)
    return False


def ingest_records(
    db: Database,
    owner: str,
    records: list[Record],
    *,
    split: bool = True,
    apply_triage: bool = True,
) -> dict[str, Any]:
    """Filter forgotten/duplicate records, persist survivors, and enqueue P1 day packets."""
    with db.connection() as conn:
        active_hashes = {
            r["content_hash"]
            for r in conn.execute(
                "SELECT content_hash FROM records WHERE owner = %s AND erased_at IS NULL",
                (owner,),
            ).fetchall()
        }
        erased_rows = conn.execute(
            """
            SELECT id, content_hash FROM records
            WHERE owner = %s AND (erased_at IS NOT NULL OR generation > 0)
            """,
            (owner,),
        ).fetchall()
        forgotten_ids = {r["id"] for r in erased_rows}
        forgotten_hashes = {r["content_hash"] for r in erased_rows}
        rules = [
            (r["kind"], r["value"])
            for r in conn.execute(
                "SELECT kind, value FROM forget_rules WHERE owner = %s",
                (owner,),
            ).fetchall()
        ]
        tz_row = conn.execute("SELECT timezone FROM owners WHERE id = %s", (owner,)).fetchone()
        owner_tz = (tz_row["timezone"] if tz_row and tz_row["timezone"] else None) or "Asia/Dubai"

    dropped_triage = 0
    blocked_forgotten = 0
    deduped = 0
    surviving: list[Record] = []

    for rec in records:
        if apply_triage and _is_triage_noise(rec):
            dropped_triage += 1
            continue
        rec_hash = _record_hash(rec)
        rule_hit = any(
            _matches_forget_rule(kind, val, rec.id, source=rec.source, text=rec.text)
            for kind, val in rules
        )
        if rec.id in forgotten_ids or rec_hash in forgotten_hashes or rule_hit:
            blocked_forgotten += 1
            continue
        if rec_hash in active_hashes:
            deduped += 1
            continue
        active_hashes.add(rec_hash)
        surviving.append(rec)

    if surviving:
        PostgresGraphStore(db).upsert_records(owner, surviving)

    enqueued_jobs: list[Job] = []
    days: list[str] = []
    if split and surviving:
        by_day: dict[str, list[Record]] = {}
        for rec in surviving:
            day = local_day(rec.at, owner_tz)
            by_day.setdefault(day, []).append(rec)
        days = sorted(by_day)
        has_device = owner_has_active_device(db, owner)
        jobs_mgr = PostgresJobs(db)
        for day in days:
            day_recs = sorted(by_day[day], key=lambda r: (r.at, r.id))
            has_sensitive = any(pre_write(r.text) is not None for r in day_recs)
            pool: Pool = "owner-device" if (has_device and not has_sensitive) else "internal"
            enqueued_jobs.extend(
                jobs_mgr.enqueue_day_packet(
                    owner,
                    day_recs,
                    pool=pool,
                    day=day,
                    sensitive_flag=has_sensitive,
                )
            )

    return {
        "owner": owner,
        "imported": len(surviving),
        "dropped_triage": dropped_triage,
        "deduped": deduped,
        "blocked_forgotten": blocked_forgotten,
        "jobs_enqueued": len(enqueued_jobs),
        "days": days,
        "jobs": [
            {"id": j.id, "day": j.day, "pool": j.pool, "records": len(j.input_ref)}
            for j in enqueued_jobs
        ],
    }
