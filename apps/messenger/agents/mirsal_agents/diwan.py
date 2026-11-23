"""Diwan: today's and upcoming UAE events, shown as Mirsal notifications.

The events backend is a separate project (Diwan, an MCP server). This service does only three things:
  1. calls Diwan's `upcoming_events` tool for events in the next 7 days (plus yesterday, so an event that just passed
     still shows as "Yesterday"),
  2. fetches at most 3 pictures per event from Supabase Storage (bucket `DIWAN_BUCKET`, one folder per event), and
  3. "More from this picture": asks Diwan's `more_from_image` tool for variations of one picture. Mirsal never makes
     pictures; Diwan returns ones it already has. Storage layout: variations of `<stem>.jpg` are `<stem>/<stem>-01.jpg …`.

Without DIWAN_MCP_URL / SUPABASE_URL it serves a labelled demo event with its pictures in public/diwan/<image_folder>/ (same layout as the Supabase bucket).
"""
from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

import httpx2 as httpx

from .mcp_client import McpClient
from .store import Store

DEMO_FILE = Path(__file__).with_name("diwan_demo.json")
IMAGE_EXT = (".jpg", ".jpeg", ".png", ".webp")
MAX_IMAGES = 3
MAX_MORE = 6
MORE_TOOL = "more_from_image"
# A picture is named by its file name only: no folders, no "..", so it can't reach outside the event's folder.
IMAGE_NAME = re.compile(r"^[\w ().-]{1,120}\.(?:jpe?g|png|webp)$", re.I)


def image_name(url_or_name: str) -> str:
    """'…/rashid/03.jpg?x=1' → '03.jpg'; raises ValueError for anything that is not a plain picture file name."""
    name = url_or_name.split("?")[0].rstrip("/").rsplit("/", 1)[-1]
    if not IMAGE_NAME.match(name) or name.startswith(".") or "\\" in url_or_name:
        raise ValueError(f"not a picture name: {name!r}")
    return name
WINDOW_DAYS = 7


class SupabaseImages:
    """Lists an event's folder in a public Supabase Storage bucket and returns up to 3 public image URLs."""

    def __init__(self, url: str, key: str, bucket: str, http: httpx.AsyncClient | None = None) -> None:
        self.url, self.key, self.bucket = url.rstrip("/"), key, bucket
        self.http = http or httpx.AsyncClient(timeout=8)

    async def listing(self, folder: str, limit: int = MAX_IMAGES) -> tuple[list[str], set[str]]:
        """Public URLs of the folder's first `limit` pictures, and the names of its sub-folders (Supabase lists a
        sub-folder as an entry with no id)."""
        folder = folder.strip("/")
        res = await self.http.post(
            f"{self.url}/storage/v1/object/list/{self.bucket}",
            headers={"apikey": self.key, "Authorization": f"Bearer {self.key}"},
            json={"prefix": folder, "limit": 50, "sortBy": {"column": "name", "order": "asc"}})
        res.raise_for_status()
        rows = res.json()
        names = [o["name"] for o in rows if str(o.get("name", "")).lower().endswith(IMAGE_EXT)]
        folders = {o["name"] for o in rows if o.get("id") is None and not str(o.get("name", "")).lower().endswith(IMAGE_EXT)}
        return [f"{self.url}/storage/v1/object/public/{self.bucket}/{folder}/{n}" for n in names[:limit]], folders

    async def images(self, folder: str) -> list[str]:
        return (await self.listing(folder))[0]


def occurrence(event: dict, today: dt.date, *, pinned: bool = False) -> dt.date | None:
    """The event's date nearest to today: a fixed `date`, or an annual `month`/`day`.
    Pinned demo events use the most recent occurrence (never a year away)."""
    if event.get("date"):
        return dt.date.fromisoformat(event["date"][:10])
    if event.get("month") and event.get("day"):
        this_year = dt.date(today.year, int(event["month"]), int(event["day"]))
        if pinned:
            return this_year if this_year <= today else dt.date(today.year - 1, this_year.month, this_year.day)
        return this_year if this_year >= today - dt.timedelta(days=1) else dt.date(today.year + 1, this_year.month, this_year.day)
    return None


def when_label(day: dt.date, today: dt.date) -> str:
    delta = (day - today).days
    return {-1: "Yesterday", 0: "Today", 1: "Tomorrow"}.get(delta, f"In {delta} days" if delta > 1 else f"{-delta} days ago")


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60]


class Diwan:
    def __init__(self, store: Store, mcp: McpClient | None, tool: str, images: SupabaseImages | None) -> None:
        self.store, self.mcp, self.tool, self.images = store, mcp, tool, images
        self.clock = dt.date.today  # tests pin it

    @property
    def mode(self) -> str:
        return "live" if self.mcp else "demo"

    async def _raw(self, today: dt.date) -> list[dict]:
        if self.mcp:
            out: Any = await self.mcp.call(self.tool, {"from": (today - dt.timedelta(days=1)).isoformat(), "days": WINDOW_DAYS + 1})
            return out.get("events", out) if isinstance(out, dict) else out
        return json.loads(DEMO_FILE.read_text(encoding="utf-8"))["events"]

    async def upcoming(self, today: dt.date | None = None) -> dict:
        today = today or self.clock()
        key = f"diwan:{today.isoformat()}:{self.mode}"
        if hit := await self.store.get(key):
            return hit
        events = []
        for e in await self._raw(today):
            pinned = bool(e.get("pinned"))
            day = occurrence(e, today, pinned=pinned)
            if not day or (not pinned and not (-1 <= (day - today).days < WINDOW_DAYS)):
                continue
            folder = e.get("image_folder") or slug(e.get("title", ""))
            pics: list[str] = list(e.get("images", []))[:MAX_IMAGES]
            # Pictures with "more": Diwan says so (`more_from`, file names), the demo lists them (`more`), or Supabase
            # has a sub-folder named after the picture.
            more_names = set(e.get("more_from", [])) | set(e.get("more", {}))
            if self.images:
                try:
                    pics, folders = await self.images.listing(folder)
                    more_names |= {n for n in (p.rsplit("/", 1)[-1] for p in pics) if n.rsplit(".", 1)[0] in folders}
                except Exception:  # noqa: BLE001 — a missing folder still shows the event, without pictures
                    pics = []
            events.append({"id": e.get("id") or f"{slug(e['title'])}-{day.isoformat()}", "title": e["title"],
                           "titleAr": e.get("title_ar", ""), "kind": e.get("kind", "event"), "date": day.isoformat(),
                           "when": when_label(day, today), "summary": e.get("summary", ""), "images": pics[:MAX_IMAGES],
                           "more": [p for p in pics[:MAX_IMAGES] if p.rsplit("/", 1)[-1] in more_names],
                           "source": "Diwan" if self.mcp else "Diwan · demo"})
        events.sort(key=lambda x: x["date"])
        out = {"events": events, "mode": self.mode, "window": {"from": (today - dt.timedelta(days=1)).isoformat(), "days": WINDOW_DAYS}}
        await self.store.set(key, out, ttl_s=3600)
        return out

    async def more_from_image(self, event_id: str, image: str, count: int = 3, today: dt.date | None = None) -> dict:
        """Variations of one of an event's pictures, from Diwan: MCP tool → Supabase sub-folder → demo file.
        Returns {"images": [{"url", "width"?, "height"?}], "event", "image", "mode", "source"}. Mirsal never makes them."""
        name = image_name(image)
        count = max(1, min(int(count), MAX_MORE))
        today = today or self.clock()
        event = next((e for e in (await self.upcoming(today))["events"] if e["id"] == event_id), None)
        if not event:
            raise LookupError(f"no upcoming event {event_id!r}")
        if not any(u.split("?")[0].rsplit("/", 1)[-1] == name for u in event["images"]):
            raise LookupError(f"{name!r} is not one of this event's pictures")
        key = f"diwan:more:{self.mode}:{event_id}:{name}:{count}"
        if hit := await self.store.get(key):
            return hit
        raw = next((e for e in await self._raw(today) if (e.get("id") or "") == event_id), {}) if not self.mcp else {}
        if self.mcp:
            out: Any = await self.mcp.call(MORE_TOOL, {"event_id": event_id, "image": name, "count": count})
            rows = out.get("images", []) if isinstance(out, dict) else out
        elif self.images:
            folder = raw.get("image_folder") or event_id
            urls, _ = await self.images.listing(f"{folder}/{name.rsplit('.', 1)[0]}", limit=count)
            rows = [{"url": u} for u in urls]
        else:
            rows = raw.get("more", {}).get(name, [])
        images = [{k: r[k] for k in ("url", "width", "height") if k in r}
                  for r in ({"url": r} if isinstance(r, str) else r for r in rows) if str(r.get("url", "")).strip()][:count]
        result = {"event": event_id, "image": name, "images": images, "mode": self.mode,
                  "source": "Diwan" if self.mcp else "Diwan · demo"}
        await self.store.set(key, result, ttl_s=3600)
        return result
