"""Load connector modules. Adding a file under plugins/ does not change the record schema."""
from __future__ import annotations

import importlib
import pkgutil

from .catalog import catalog_by_id
from .plugins import BUILDERS
from .types import ConnectorSpec


_loaded = False


def discover() -> dict:
    global _loaded
    if not _loaded:
        import app.connectors.plugins as plugins

        for info in pkgutil.iter_modules(plugins.__path__):
            if info.name.startswith("_"):
                continue
            importlib.import_module(f"{plugins.__name__}.{info.name}")
        _loaded = True
    return dict(BUILDERS)


def build_implementations(specs: dict[str, ConnectorSpec] | None = None) -> dict:
    specs = specs or catalog_by_id()
    builders = discover()
    return {connector_id: builder(specs[connector_id]) for connector_id, builder in builders.items() if connector_id in specs}
