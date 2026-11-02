"""Product memory engine (temporal_note-slim). Owner-scoped; never imports personal vault data."""
from .schema import ensure_memory_schema
from .store import MemoryStore

__all__ = ["ensure_memory_schema", "MemoryStore"]
