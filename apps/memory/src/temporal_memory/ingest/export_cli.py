"""Safe Quest-style Markdown export helper that refuses writes inside the repository (WP-D)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from temporal_memory.api.export_md import render
from temporal_memory.core.graph_store import PostgresGraphStore
from temporal_memory.db.db import Database


def find_repo_root(start: Path | None = None) -> Path:
    """Walk parent directories looking for `.git`, falling back to the app root."""
    cur = (start or Path(__file__)).resolve()
    if cur.is_file():
        cur = cur.parent
    for candidate in (cur, *cur.parents):
        if (candidate / ".git").exists():
            return candidate
    return Path(__file__).resolve().parents[3]


def export_owner_tree(
    db: Database,
    owner: str,
    out_dir: str | Path,
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    """Render an owner's Markdown memory tree into `out_dir` outside the repository."""
    out_path = Path(out_dir).resolve()
    root = Path(repo_root).resolve() if repo_root else find_repo_root()

    if out_path == root or out_path.is_relative_to(root):
        raise ValueError(f"Refusing to write export inside repository root {root}: {out_path}")

    files = render(owner, store=PostgresGraphStore(db))
    written: list[str] = []
    for rel_path, content in files.items():
        rel = Path(rel_path)
        if rel.is_absolute():
            raise ValueError(f"Refusing absolute export path: {rel_path}")
        target = (out_path / rel).resolve()
        if not target.is_relative_to(out_path) or target == out_path:
            raise ValueError(f"Refusing path traversal outside export directory: {rel_path}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        written.append(target.relative_to(out_path).as_posix())

    return {
        "owner": owner,
        "out_dir": str(out_path),
        "files_written": len(written),
        "files": sorted(written),
    }
