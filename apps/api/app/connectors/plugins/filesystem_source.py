"""One folder on the API machine. Not a full-disk scan and not a phone filesystem."""
from __future__ import annotations

import os
from pathlib import Path

from ..base import BaseConnector
from ..types import AuthFailed, Page, PermanentFailure, RawItem
from . import register

TEXT_SUFFIXES = {".txt", ".md", ".csv", ".json", ".ics", ".eml"}
SENSITIVE_NAMES = {".env", ".env.local", "id_rsa", "id_ed25519", "oauth.key", "connector.key", "credentials.json"}
MAX_FILES = 200
MAX_DEPTH = 6


def _sensitive(name: str) -> bool:
    lower = name.lower()
    if lower in SENSITIVE_NAMES or lower.startswith(".env"):
        return True
    return lower.endswith((".pem", ".key"))


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


class FilesystemConnector(BaseConnector):
    transport = "local"

    def root(self, raw: str) -> Path:
        if not isinstance(raw, str) or not raw.strip():
            raise AuthFailed("Choose a folder")
        path = Path(raw).expanduser().resolve()
        if not path.is_dir():
            raise PermanentFailure("Choose a folder that exists")
        if path.parent == path:
            raise PermanentFailure("Choose a specific folder, not the disk root")
        return path

    def probe(self, client, credentials) -> str:
        return str(self.root(credentials.get("root")))

    def fetch_page(self, client, credentials, cursor) -> Page:
        root = self.root(credentials.get("root"))
        seen = dict((cursor or {}).get("files") or {})
        items: list[RawItem] = []
        files_meta: dict[str, str] = {}
        scanned = 0
        for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
            current = Path(dirpath).resolve()
            if not _inside(current, root):
                dirnames[:] = []
                continue
            depth = len(current.relative_to(root).parts)
            if depth > MAX_DEPTH:
                dirnames[:] = []
                continue
            dirnames[:] = [name for name in dirnames if not (current / name).is_symlink()]
            for name in filenames:
                if scanned >= MAX_FILES:
                    break
                scanned += 1
                path = current / name
                if path.is_symlink() or _sensitive(name):
                    continue
                resolved = path.resolve()
                if not _inside(resolved, root) or not resolved.is_file():
                    continue
                stat = resolved.stat()
                rel = resolved.relative_to(root).as_posix()
                mtime = str(stat.st_mtime_ns)
                files_meta[rel] = mtime
                if seen.get(rel) == mtime:
                    continue
                if resolved.suffix.lower() in TEXT_SUFFIXES and stat.st_size <= 256_000:
                    text = resolved.read_text(encoding="utf-8", errors="replace")
                else:
                    text = resolved.name
                items.append(
                    RawItem(
                        source_id=rel,
                        source_timestamp=mtime,
                        title=resolved.name,
                        text=text,
                        kind="file",
                        metadata={"size": stat.st_size, "mtime_ns": mtime},
                    )
                )
            if scanned >= MAX_FILES:
                break
        return Page(items=items, next_cursor={"files": files_meta})


@register("filesystem")
def build(spec):
    return FilesystemConnector(spec)
