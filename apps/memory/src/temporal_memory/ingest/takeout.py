"""Google Takeout importer (WP-J): YouTube, Chrome and Gemini Apps activity.

`takeout_records(owner, path, since=None)` reads a Takeout `.zip` or an
extracted folder, and **only** these members (everything else is ignored):

- `Takeout/YouTube and YouTube Music/history/watch-history.json` and
  `search-history.json` — Google shape: a JSON list of
  ``{header, title: "Watched X" | "Searched for X", titleUrl,
  subtitles: [{name: channel, url}], time: ISO-8601, products}``.
- `Takeout/Chrome/BrowserHistory.json` — ``{"Browser History":
  [{title, url, time_usec (Unix epoch microseconds), ...}]}``.
- `Takeout/My Activity/Gemini Apps/MyActivity.json` — a JSON list of
  ``{header: "Gemini Apps", title: "Prompted ...", subtitles, time,
  products}`` (the prompt is the title; Gemini's reply is never emitted).

Reuse, not duplication: YouTube normalisation is fed to
`ingest/youtube.parse_youtube_history` (its per-day aggregation, Rule-9
screening and `youtube:interests` Record shape are reused verbatim);
Chrome visits are screened with `ingest/desktop/browser` (`_url`,
`_deny_domains`, `_sensitive`, `_zone`) and aggregated per day by domain
exactly like `browser_records` — never per page; Gemini prompts go
through `ingest/desktop/_redact.safe_text` (redacted, truncated) and are
kept as the user's own prompts, one Record per day.

Rule 9: faith, health, politics and sexuality (and every other canonical
category) in watch/search/browse/Gemini text is **held back**, never
inferred; no per-video or per-page title, URL or timestamp ever appears
in a Record. Malicious archives are refused: path traversal, absolute or
symlink entries, oversized members and zip bombs raise `TakeoutError`.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, time, timezone
import json
from pathlib import Path
import re
import tempfile
import zipfile

from temporal_memory.ingest.desktop._redact import safe_text
from temporal_memory.ingest.desktop.browser import (
    DEFAULT_DENY_DOMAINS,
    _deny_domains,
    _sensitive as _browser_sensitive,
    _url,
    _zone,
)
from temporal_memory.ingest.youtube import parse_youtube_history
from temporal_memory.models import Owner, Record
from temporal_memory.privacy.sensitive import pre_write

MAX_ZIP_BYTES = 256 * 1024 * 1024       # on-disk archive size
MAX_MEMBER_BYTES = 64 * 1024 * 1024     # one allowed member, uncompressed
MAX_TOTAL_BYTES = 128 * 1024 * 1024     # all entries, uncompressed
MAX_FILES = 10_000                      # entries in the archive / folder walk
MAX_COMPRESSION_RATIO = 100             # uncompressed / compressed per member
GEMINI_PROMPT_LIMIT = 500               # chars per prompt (safe_text truncation)

_ALLOWED_SUFFIXES = {
    "youtube": (
        "youtube and youtube music/history/watch-history.json",
        "youtube and youtube music/history/search-history.json",
    ),
    "chrome": ("chrome/browserhistory.json",),
    "gemini": ("my activity/gemini apps/myactivity.json",),
}


class TakeoutError(ValueError):
    """The Takeout path is unsafe, oversized or malformed."""


def _owner_id(owner: Owner | str) -> str:
    return owner.id if isinstance(owner, Owner) else str(owner)


def _cutoff(owner: Owner | str, since) -> datetime | None:
    if since is None:
        return None
    zone = _zone(owner)
    if isinstance(since, str):
        try:
            since = datetime.fromisoformat(since.replace("Z", "+00:00"))
        except ValueError:
            since = date.fromisoformat(since)
    if isinstance(since, datetime):
        dt = since if since.tzinfo else since.replace(tzinfo=zone)
        return dt.astimezone(timezone.utc)
    if isinstance(since, date):
        return datetime.combine(since, time.min, zone).astimezone(timezone.utc)
    raise TakeoutError("since must be a date, datetime or ISO string")


def _parse_time(value) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _kind_for(name: str) -> str | None:
    low = name.replace("\\", "/").lower().lstrip("./")
    for kind, suffixes in _ALLOWED_SUFFIXES.items():
        if any(low == s or low.endswith("/" + s) for s in suffixes):
            return kind
    return None


def _check_entry_name(name: str) -> None:
    """Refuse traversal / absolute entries anywhere in the archive."""
    norm = name.replace("\\", "/")
    parts = [p for p in norm.split("/") if p not in ("", ".")]
    if norm.startswith("/") or re.match(r"^[A-Za-z]:", norm) or ".." in parts:
        raise TakeoutError(f"unsafe path in Takeout archive: {name!r}")


def _read_zip(path: Path) -> dict[str, list[bytes]]:
    if path.stat().st_size > MAX_ZIP_BYTES:
        raise TakeoutError("Takeout archive exceeds the size cap")
    try:
        archive = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, OSError) as exc:
        raise TakeoutError(f"not a readable Takeout zip: {exc}") from exc
    found: dict[str, list[bytes]] = defaultdict(list)
    with archive:
        infos = archive.infolist()
        if len(infos) > MAX_FILES:
            raise TakeoutError("Takeout archive has too many entries")
        if sum(i.file_size for i in infos) > MAX_TOTAL_BYTES:
            raise TakeoutError("Takeout archive uncompressed size exceeds the cap")
        for info in infos:
            _check_entry_name(info.filename)
            mode = (info.external_attr >> 16) & 0o170000
            if mode == 0o120000:  # symlink
                raise TakeoutError(f"symlink entry in Takeout archive: {info.filename!r}")
            if info.is_dir():
                continue
            kind = _kind_for(info.filename)
            if kind is None:
                continue  # ignore every other folder in the zip
            if info.file_size > MAX_MEMBER_BYTES:
                raise TakeoutError(f"Takeout member exceeds the size cap: {info.filename!r}")
            if info.compress_size and info.file_size / info.compress_size > MAX_COMPRESSION_RATIO:
                raise TakeoutError(f"possible zip bomb in Takeout archive: {info.filename!r}")
            with archive.open(info) as handle:
                data = handle.read(MAX_MEMBER_BYTES + 1)
            if len(data) > MAX_MEMBER_BYTES:
                raise TakeoutError(f"Takeout member exceeds the size cap: {info.filename!r}")
            found[kind].append(data)
    return found


def _read_folder(path: Path) -> dict[str, list[bytes]]:
    if not path.is_dir():
        raise TakeoutError("Takeout path is neither a zip file nor a folder")
    found: dict[str, list[bytes]] = defaultdict(list)
    count = 0
    for candidate in sorted(path.rglob("*")):
        count += 1
        if count > MAX_FILES:
            raise TakeoutError("Takeout folder has too many entries")
        if candidate.is_symlink():
            rel = candidate.relative_to(path).as_posix()
            if _kind_for(rel) is not None:
                raise TakeoutError(f"symlinked Takeout file refused: {rel!r}")
            continue
        if not candidate.is_file():
            continue
        rel = candidate.relative_to(path).as_posix()
        kind = _kind_for(rel)
        if kind is None:
            continue
        if candidate.stat().st_size > MAX_MEMBER_BYTES:
            raise TakeoutError(f"Takeout file exceeds the size cap: {rel!r}")
        found[kind].append(candidate.read_bytes())
    return found


def _load_json(data: bytes, label: str):
    try:
        return json.loads(data.decode("utf-8-sig"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise TakeoutError(f"malformed JSON in {label}: {exc}") from exc


def _youtube_records(owner, blobs: list[bytes], cutoff) -> list[Record]:
    zone = _zone(owner)
    normalized: list[dict] = []
    for blob in blobs:
        raw = _load_json(blob, "YouTube history")
        if not isinstance(raw, list):
            raise TakeoutError("YouTube history JSON must be a list")
        for item in raw:
            if not isinstance(item, dict):
                continue
            at = _parse_time(item.get("time"))
            if at is None or (cutoff is not None and at < cutoff):
                continue
            title = str(item.get("title") or "")
            for prefix in ("Watched ", "Searched for "):
                if title.startswith(prefix):
                    title = title[len(prefix):]
                    break
            channel = ""
            subs = item.get("subtitles")
            if isinstance(subs, list) and subs and isinstance(subs[0], dict):
                channel = str(subs[0].get("name") or "")
            local = at.astimezone(zone)
            normalized.append({"title": title, "channel": channel,
                               "watched_at": local.isoformat()})
    if not normalized:
        return []
    # Reuse WP-F aggregation/screening verbatim via its file-based API.
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                     encoding="utf-8") as handle:
        json.dump(normalized, handle, ensure_ascii=False)
        tmp = handle.name
    try:
        records, _held_back = parse_youtube_history(tmp, _owner_id(owner))
    finally:
        Path(tmp).unlink(missing_ok=True)
    return records


def _chrome_records(owner, blobs: list[bytes], cutoff) -> list[Record]:
    zone = _zone(owner)
    denied = _deny_domains(DEFAULT_DENY_DOMAINS)
    visits: dict[str, Counter] = defaultdict(Counter)
    for blob in blobs:
        raw = _load_json(blob, "Chrome BrowserHistory")
        items = raw.get("Browser History") if isinstance(raw, dict) else None
        if not isinstance(items, list):
            raise TakeoutError("BrowserHistory.json must hold a 'Browser History' list")
        for item in items:
            if not isinstance(item, dict):
                continue  # e.g. Google's "data is encrypted" string marker
            try:
                usec = int(item.get("time_usec"))
            except (TypeError, ValueError):
                continue
            if usec <= 0:
                continue
            at = datetime.fromtimestamp(usec / 1_000_000, tz=timezone.utc)
            if cutoff is not None and at < cutoff:
                continue
            parsed = _url(item.get("url"), denied)
            if parsed is None:
                continue  # denylisted, private, credential-bearing or malformed
            host, parts = parsed
            title = item.get("title") if isinstance(item.get("title"), str) else ""
            if pre_write(title) == "credential" or _browser_sensitive(title):
                continue  # Rule 9: sensitive page titles are held back
            tail = f"{parts.path} {parts.query} {parts.fragment}"
            if _browser_sensitive(tail):
                continue  # e.g. a symptom search in the query string
            visits[at.astimezone(zone).date().isoformat()][host] += 1
    records = []
    for day in sorted(visits):
        lines = [f"Browser visits to {domain}: {count}"
                 for domain, count in sorted(visits[day].items())]
        records.append(Record(id=f"takeout-chrome-{day}", owner=_owner_id(owner),
                              source="takeout:chrome", at=f"{day}T00:00:00",
                              author="Browser history", text="\n".join(lines),
                              generation=0))
    return records


def _gemini_records(owner, blobs: list[bytes], cutoff) -> list[Record]:
    zone = _zone(owner)
    by_day: dict[str, list[str]] = defaultdict(list)
    for blob in blobs:
        raw = _load_json(blob, "Gemini Apps MyActivity")
        if not isinstance(raw, list):
            raise TakeoutError("Gemini Apps MyActivity.json must be a list")
        for item in raw:
            if not isinstance(item, dict):
                continue
            header = str(item.get("header") or "")
            products = item.get("products") or []
            if header and "gemini" not in header.lower() and not any(
                    "gemini" in str(p).lower() for p in products):
                continue  # combined My Activity export: not Gemini
            at = _parse_time(item.get("time"))
            if at is None or (cutoff is not None and at < cutoff):
                continue
            prompt = str(item.get("title") or "")
            if prompt.startswith("Prompted "):
                prompt = prompt[len("Prompted "):]
            if _browser_sensitive(prompt):
                continue  # Rule 9 topics beyond the canonical gate
            cleaned = safe_text(prompt, GEMINI_PROMPT_LIMIT)
            if not cleaned:
                continue  # held by the canonical gate or redacted to nothing
            by_day[at.astimezone(zone).date().isoformat()].append(cleaned)
    records = []
    for day in sorted(by_day):
        text = f"Gemini prompts ({day}):\n" + "\n".join(by_day[day])
        records.append(Record(id=f"takeout-gemini-{day}", owner=_owner_id(owner),
                              source="takeout:gemini-apps", at=f"{day}T00:00:00",
                              author="owner", text=text, generation=0))
    return records


def takeout_records(owner, path, since=None) -> list[Record]:
    """Import a Google Takeout zip/folder as daily Records (see module docstring).

    Missing parts are fine (only the sources present produce Records) and
    every non-allowlisted folder is ignored. Unsafe, oversized or malformed
    allowed content raises `TakeoutError`.
    """
    root = Path(path)
    if not root.exists():
        raise TakeoutError(f"Takeout path does not exist: {path}")
    found = _read_folder(root) if root.is_dir() else _read_zip(root)
    cutoff = _cutoff(owner, since)
    records: list[Record] = []
    if found.get("youtube"):
        records.extend(_youtube_records(owner, found["youtube"], cutoff))
    if found.get("chrome"):
        records.extend(_chrome_records(owner, found["chrome"], cutoff))
    if found.get("gemini"):
        records.extend(_gemini_records(owner, found["gemini"], cutoff))
    return sorted(records, key=lambda r: (r.at, r.source, r.id))
