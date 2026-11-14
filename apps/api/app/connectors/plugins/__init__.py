"""Independent connector modules. Importing a module registers its builder.

The universal record schema does not mention these ids.
"""
from __future__ import annotations

from collections.abc import Callable

BUILDERS: dict[str, Callable] = {}


def register(*connector_ids: str):
    def decorate(builder: Callable):
        for connector_id in connector_ids:
            if connector_id in BUILDERS:
                raise RuntimeError(f"duplicate connector builder: {connector_id}")
            BUILDERS[connector_id] = builder
        return builder

    return decorate
