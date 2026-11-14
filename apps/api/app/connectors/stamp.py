"""Keep a provider timestamp as it arrived. Do not reformat it."""
from __future__ import annotations


def preserve_timestamp(value) -> str:
    if value is None or isinstance(value, bool):
        return ""
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)
