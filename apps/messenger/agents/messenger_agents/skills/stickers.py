"""Sticker packs the user already has on disk. Generation is not part of this app."""
from __future__ import annotations

import json
import random
import re
from pathlib import Path

from ..text import norm
from .base import CONTEXT_MAX, Msg
STICKER_EXT = {".png", ".webp", ".gif", ".svg", ".jpg", ".jpeg", ".webm"}


class Stickers:
    """Sub-folders of `root` (optional pack.json: {title, tags})."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def packs(self) -> list[dict]:
        out: list[dict] = []
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
        p = (self.root / pack / name).resolve()
        return p if p.is_file() and self.root.resolve() in p.parents and p.suffix.lower() in STICKER_EXT else None
