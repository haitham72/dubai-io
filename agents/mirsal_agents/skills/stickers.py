"""Sticker packs + the Mirsal Builder Library (read in place)."""
from __future__ import annotations

import json
import random
import re
from pathlib import Path

from ..text import norm
from .base import CONTEXT_MAX, Msg
# ------------------------------------------------------------------ stickers
STICKER_EXT = {".png", ".webp", ".gif", ".svg", ".jpg", ".jpeg", ".webm"}  # .webm = animated (Telegram-style video stickers)


class BuilderLibrary:
    """The Mirsal Builder project's approved packs, read in place (never written).

    The Builder keeps its Library at <out>/library/: library.json + files/<batch>/<file>. A pack is only in `packs` after
    its review gates (stills and animations approved, then the pack); deleted packs sit in `trash`, which is skipped.
    Re-read whenever library.json changes, so a pack approved in the Builder shows up here on the next request."""

    def __init__(self, root: Path | None) -> None:
        self.root = root
        self._mtime, self._packs = -1.0, []

    @property
    def found(self) -> bool:
        return bool(self.root) and (self.root / "library.json").is_file()

    def packs(self) -> list[dict]:
        if not self.found:
            return []
        db = self.root / "library.json"
        mtime = db.stat().st_mtime
        if mtime != self._mtime:
            try:
                data = json.loads(db.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                return self._packs  # mid-write in the Builder: keep the last good read
            out = []
            for p in data.get("packs", []):
                stickers = [s for s in p.get("stickers", []) if Path(s.get("file", "")).suffix.lower() in STICKER_EXT
                            and ".." not in Path(s["file"]).parts and not Path(s["file"]).is_absolute()]
                stickers.sort(key=lambda s: s.get("type") != "animated")  # animated (.webm) first
                if not stickers:
                    continue
                words = re.findall(r"[a-z]+", f"{p.get('slug', '')} {p.get('name', '')}".lower())
                out.append({"id": f"mb-{p['id']}", "title": p.get("name") or p["id"], "tags": sorted(set(words)), "source": "mirsal-builder",
                            "stickers": [f"{s['id']}{Path(s['file']).suffix.lower()}" for s in stickers],
                            "files": {f"{s['id']}{Path(s['file']).suffix.lower()}": s["file"] for s in stickers}})
            self._mtime, self._packs = mtime, out
        return self._packs

    def file(self, pack: str, name: str) -> Path | None:
        p = next((x for x in self.packs() if x["id"] == pack), None)
        rel = p and p["files"].get(name)
        if not rel:
            return None
        files = (self.root / "files").resolve()
        path = (files / rel).resolve()
        return path if path.is_file() and files in path.parents and path.suffix.lower() in STICKER_EXT else None


class Stickers:
    """Packs: the Mirsal Builder's approved Library first (when found), then sub-folders of `root` (bundled demo packs or
    another export folder; optional pack.json: {title, tags})."""

    def __init__(self, root: Path, library: BuilderLibrary | None = None) -> None:
        self.root, self.library = root, library or BuilderLibrary(None)

    def packs(self) -> list[dict]:
        out = [{k: v for k, v in p.items() if k != "files"} for p in self.library.packs()]
        if not self.root.exists():
            return out
        for d in sorted(p for p in self.root.iterdir() if p.is_dir()):
            meta = json.loads((d / "pack.json").read_text(encoding="utf-8")) if (d / "pack.json").exists() else {}
            files = sorted(f.name for f in d.iterdir() if f.suffix.lower() in STICKER_EXT)
            if files:
                out.append({"id": d.name, "title": meta.get("title", d.name.replace("-", " ").title()),
                            "tags": meta.get("tags", []), "stickers": files})
        return out

    def pick(self, context: list[Msg], rng: random.Random | None = None, exclude: str = "") -> dict | None:
        """A pack whose tags match the chat, else a random one ("random fetch" until the sticker project is linked)."""
        packs = [p for p in self.packs() if p["id"] != exclude] or self.packs()
        if not packs:
            return None
        text = norm(" ".join(m.text for m in context[-CONTEXT_MAX:]))
        scored = [(sum(1 for t in p["tags"] if re.search(rf"\b{re.escape(t)}\b", text)), p) for p in packs]
        best = max(s for s, _ in scored)
        pool = [p for s, p in scored if s == best] if best else packs
        pack = (rng or random).choice(pool)
        files = list(pack["stickers"])
        (rng or random).shuffle(files)
        return {**pack, "stickers": files[:8], "matched": best > 0}

    def file(self, pack: str, name: str) -> Path | None:
        if pack.startswith("mb-"):
            return self.library.file(pack, name)
        p = (self.root / pack / name).resolve()
        return p if p.is_file() and self.root.resolve() in p.parents and p.suffix.lower() in STICKER_EXT else None
