"""One local-day function for triage, import split, and the bridge."""
from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo


def local_day(at: str, tz: str) -> str:
    """Return the owner's calendar day for an ISO timestamp.

    Aware timestamps convert into ``tz``. A naive timestamp is already wall
    time in that zone, so its date is kept. ``20:30Z`` in ``Asia/Dubai`` is
    the next local day.
    """
    raw = (at or "").strip()
    if not raw:
        return ""
    stamp = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        return stamp.date().isoformat()
    if stamp.tzinfo is timezone.utc or stamp.utcoffset() is not None:
        stamp = stamp.astimezone(ZoneInfo(tz or "Asia/Dubai"))
    return stamp.date().isoformat()
