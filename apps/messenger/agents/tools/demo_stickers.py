"""Writes the demo sticker packs to public/stickers/<pack>/ (one sub-folder per pack, like the mirsal-sticker project)
and public/stickers/index.json (the browser's fallback manifest when the agents service is off).

    python tools/demo_stickers.py            # from agents/
"""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / "public" / "stickers"

PACKS = {
    "nile-days": ("Nile Days", ["egypt", "cairo", "nile", "pyramids", "giza", "luxor", "trip", "travel"], [
        ("🔺", "Pyramids!"), ("🐫", "Camel ride"), ("⛵", "Nile cruise"), ("🏺", "Pharaoh mode"),
        ("🌞", "Sun's out"), ("🥙", "Koshary?"), ("😎", "Cairo vibes"), ("📸", "Photo dump")], ("#f6b73c", "#e2704b")),
    "yalla": ("Yalla", ["dubai", "uae", "weekend", "gahwa", "coffee", "friends", "habibi"], [
        ("🐪", "Yalla!"), ("☕", "Gahwa time"), ("🌴", "Weekend mode"), ("😂", "Wallah?!"),
        ("🙏", "Shukran"), ("🎉", "Mabrook!"), ("🫡", "Tamam"), ("👋", "Ahlan")], ("#4fb3ff", "#7a5cff")),
    "wheels-up": ("Wheels Up", ["flight", "flights", "travel", "airport", "holiday", "vacation", "leave", "trip"], [
        ("✈️", "Wheels up"), ("🧳", "Packed!"), ("🏝️", "Out of office"), ("🗺️", "Let's go"),
        ("🌅", "Sunset?"), ("🛂", "Visa sorted"), ("🎒", "Ready"), ("🌍", "Next stop")], ("#2ec4b6", "#3a86ff")),
    "office-mood": ("Office Mood", ["work", "meeting", "deadline", "office", "project", "launch", "monday"], [
        ("💻", "On it"), ("✅", "Done"), ("⏰", "5 min late"), ("🔥", "Ship it"),
        ("🤝", "Deal"), ("📅", "Booked"), ("😴", "Monday…"), ("🚀", "Launch")], ("#ff6b9a", "#ffb347")),
}


def sticker(emoji: str, caption: str, c1: str, c2: str, i: int) -> str:
    tilt = (-6, 4, -3, 6, -5, 3, -4, 5)[i % 8]
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{c1}"/><stop offset="1" stop-color="{c2}"/></linearGradient>
    <filter id="s" x="-20%" y="-20%" width="140%" height="140%"><feDropShadow dx="0" dy="6" stdDeviation="6" flood-color="#000" flood-opacity="0.22"/></filter>
  </defs>
  <g transform="rotate({tilt} 128 128)" filter="url(#s)">
    <rect x="22" y="22" width="212" height="212" rx="64" fill="#fff"/>
    <rect x="34" y="34" width="188" height="188" rx="54" fill="url(#g)"/>
    <text x="128" y="138" font-size="96" text-anchor="middle" dominant-baseline="middle">{emoji}</text>
    <text x="128" y="205" font-family="-apple-system, 'Segoe UI', Roboto, sans-serif" font-size="{26 if len(caption) < 11 else 21}" font-weight="800"
          text-anchor="middle" fill="#fff" stroke="#1d1d1f" stroke-width="5" paint-order="stroke" stroke-linejoin="round">{caption}</text>
  </g>
</svg>
"""


def main() -> None:
    manifest = []
    for pid, (title, tags, items, (c1, c2)) in PACKS.items():
        d = OUT / pid
        d.mkdir(parents=True, exist_ok=True)
        files = []
        for i, (emoji, caption) in enumerate(items):
            name = f"{i + 1:02d}-{caption.lower().replace(' ', '-').strip('!?.…').replace(chr(39), '')}.svg"
            (d / name).write_text(sticker(emoji, caption.replace("&", "&amp;"), c1, c2, i), encoding="utf-8")
            files.append(name)
        (d / "pack.json").write_text(json.dumps({"title": title, "tags": tags}, indent=2) + "\n", encoding="utf-8")
        manifest.append({"id": pid, "title": title, "tags": tags, "stickers": files})
    (OUT / "index.json").write_text(json.dumps({"packs": manifest}, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{sum(len(p['stickers']) for p in manifest)} stickers in {len(manifest)} packs → {OUT}")


if __name__ == "__main__":
    main()
