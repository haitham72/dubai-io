"""Bounded exponential backoff. A Retry-After hint from the provider wins, still capped."""
from __future__ import annotations

from datetime import datetime, timedelta

MAX_ATTEMPTS = 5
CAP_SECONDS = 300


def retry_delay_seconds(attempt: int, *, retry_after: float | None = None) -> float:
    if retry_after is not None and retry_after > 0:
        return float(min(CAP_SECONDS, retry_after))
    return float(min(CAP_SECONDS, 2 ** max(attempt, 1)))


def add_seconds(stamp: str, seconds: float) -> str:
    moment = datetime.fromisoformat(stamp)
    return (moment + timedelta(seconds=seconds)).isoformat(timespec="seconds")
