"""Convert an explicitly supplied ChatGPT export to local, redacted records."""
from __future__ import annotations

import hashlib
import json
import re
import stat
import zlib
from collections import defaultdict
from datetime import date, datetime, timezone, tzinfo
from pathlib import Path
from typing import Any, BinaryIO, Iterator
from zipfile import BadZipFile, ZIP_DEFLATED, ZIP_STORED, ZipFile

from temporal_memory.ingest.desktop._redact import safe_text
from temporal_memory.ingest.desktop.agent_sessions import _since, _zone
from temporal_memory.models import Owner, Record

_SOURCE = "ai:chatgpt"
_MAX_JSON_BYTES = 64 * 1024 * 1024
_MAX_ARCHIVE_ENTRIES = 10_000
_MAX_COMPRESSION_RATIO = 1_000
_CHUNK_NAME = re.compile(r"conversations(?:-([0-9]{1,6}))?\.json")
_CODE_MARKER = re.compile(
    r"(?P<fence>`{3,}|~{3,})|<(?P<close>/)?(?P<tag>pre|code)\b[^<>]*>",
    re.IGNORECASE,
)
_CODE_LINE = re.compile(
    r"^(?:\s{4,}|\t)|^\s*(?:#!|>>> |\$ |"
    r"(?:async\s+)?(?:def|function|class)\s+\w+\s*[(:{]|"
    r"(?:import|from)\s+[\w.]+(?:\s+import\s+\w+)?\s*$|"
    r"(?:const\s+|let\s+|var\s+)?[\w.]+\s*=(?!=)|"
    r"(?:if|while|for|switch)\s*\([^\n]*\)\s*[{:]\s*$|"
    r"(?:return|throw|console\.\w+)\b.+;\s*$|"
    r"[\w.]+\([^\r\n]*\)\s*;?\s*$|"
    r"[{}\[\]();,]+\s*$|[\"'][^\r\n]+?[\"']\s*:\s*.+)"
)
_HIDDEN_FLAGS = (
    "is_visually_hidden_from_conversation",
    "is_user_system_message",
    "is_hidden",
    "is_automation",
    "is_automated",
)


def _read_json(stream: BinaryIO, limit: int) -> list[dict]:
    raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError("ChatGPT export exceeds the JSON size limit")
    try:
        rows = json.loads(raw)
    except (ValueError, RecursionError):
        raise ValueError("ChatGPT export contains invalid conversation JSON") from None
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError("ChatGPT export must contain a list of conversations")
    return rows


def _conversations(path: Path) -> Iterator[dict]:
    try:
        if path.suffix.lower() == ".json":
            with path.open("rb") as stream:
                yield from _read_json(stream, _MAX_JSON_BYTES)
            return
        if path.suffix.lower() != ".zip":
            raise ValueError("ChatGPT export must be a JSON or ZIP file")

        with ZipFile(path) as archive:
            entries = archive.infolist()
            if len(entries) > _MAX_ARCHIVE_ENTRIES:
                raise ValueError("ChatGPT export ZIP has too many entries")
            members = {}
            remaining = _MAX_JSON_BYTES
            for entry in entries:
                match = _CHUNK_NAME.fullmatch(entry.orig_filename)
                if not match:
                    continue
                number = int(match[1]) if match[1] is not None else -1
                if (
                    number in members
                    or stat.S_IFMT(entry.external_attr >> 16) not in (0, stat.S_IFREG)
                    or entry.flag_bits & 1
                    or entry.compress_type not in (ZIP_STORED, ZIP_DEFLATED)
                ):
                    raise ValueError("ChatGPT export ZIP has an unsafe conversation entry")
                if entry.file_size > _MAX_COMPRESSION_RATIO * max(1, entry.compress_size):
                    raise ValueError("ChatGPT export ZIP exceeds the compression ratio limit")
                remaining -= entry.file_size
                if remaining < 0:
                    raise ValueError("ChatGPT export exceeds the JSON size limit")
                members[number] = entry
            if not members:
                raise ValueError("ChatGPT export ZIP is missing root conversation JSON")
            if -1 in members and len(members) > 1:
                raise ValueError("ChatGPT export ZIP contains both whole and numbered conversation JSON")
            for _, entry in sorted(members.items()):
                with archive.open(entry) as stream:
                    yield from _read_json(stream, entry.file_size)
    except (OSError, BadZipFile, RuntimeError, EOFError, NotImplementedError, zlib.error):
        raise ValueError("ChatGPT export cannot be read") from None


def _timestamp(value: object) -> datetime | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        return datetime.fromtimestamp(value, timezone.utc)
    except (OSError, OverflowError, ValueError):
        return None


def _messages(conversation: dict[str, Any]) -> list[dict]:
    # ChatGPT exports a message tree. `current_node` marks the visible branch.
    # See the data preparation methods at https://spirals.stanford.edu/assets/pdf/moore_characterizing_2026.pdf.
    mapping = conversation.get("mapping")
    if not isinstance(mapping, dict):
        raise ValueError("ChatGPT export has an invalid conversation mapping")

    parents = {}
    messages = {}
    for node_id, node in mapping.items():
        if not isinstance(node, dict):
            raise ValueError("ChatGPT export has an invalid conversation node")
        message, parent = node.get("message"), node.get("parent")
        if message is not None and not isinstance(message, dict):
            raise ValueError("ChatGPT export has an invalid message")
        if parent is not None and (not isinstance(parent, str) or parent not in mapping):
            raise ValueError("ChatGPT export has an invalid parent link")
        parents[node_id] = parent
        if message is not None:
            messages[node_id] = message

    checked = set()
    for node_id in parents:
        pending = set()
        while node_id is not None and node_id not in checked:
            if node_id in pending:
                raise ValueError("ChatGPT export has a conversation cycle")
            pending.add(node_id)
            node_id = parents[node_id]
        checked.update(pending)

    current = conversation.get("current_node")
    if current is not None and (not isinstance(current, str) or current not in mapping):
        raise ValueError("ChatGPT export has an invalid current node")
    if current is not None and any("parent" in node for node in mapping.values()):
        branch = []
        while current is not None:
            if current in messages:
                branch.append(messages[current])
            current = parents[current]
        return branch[::-1]
    linked_parents = [parent for parent in parents.values() if parent is not None]
    if len(set(linked_parents)) != len(linked_parents):
        raise ValueError("ChatGPT export has a forked conversation without a current node")

    earliest = datetime.min.replace(tzinfo=timezone.utc)
    return [
        message
        for _, message in sorted(
            messages.items(), key=lambda item: (_timestamp(item[1].get("create_time")) or earliest, item[0])
        )
    ]


def _visible_message(message: dict) -> tuple[str, str] | None:
    author = message.get("author")
    role = author.get("role") if isinstance(author, dict) else None
    if role not in ("user", "assistant"):
        return None
    metadata = message.get("metadata")
    metadata = metadata if isinstance(metadata, dict) else {}
    if any(message.get(flag) or metadata.get(flag) for flag in _HIDDEN_FLAGS):
        return None
    if message.get("recipient") not in (None, "all") or message.get("channel") not in (None, "final"):
        return None
    if role == "assistant" and (
        message.get("end_turn") is False or message.get("status") not in (None, "finished_successfully")
    ):
        return None
    content = message.get("content")
    if not isinstance(content, dict) or content.get("content_type") not in (None, "text", "multimodal_text"):
        return None
    parts = content.get("parts")
    if not isinstance(parts, list):
        return None
    # Join first so a fence spanning multiple string parts suppresses the whole block.
    text = "\n".join(part for part in parts if isinstance(part, str))
    cleaned = _safe_prose(text, 300 if role == "assistant" else 800)
    return (role, cleaned) if cleaned else None


def _safe_prose(text: str, limit: int) -> str:
    prose = []
    start = 0
    opener: tuple[str, int] | None = None
    for marker in _CODE_MARKER.finditer(text):
        fence = marker["fence"]
        delimiter = (fence[0], len(fence)) if fence else (marker["tag"].lower(), 0)
        closes_tag = bool(marker["close"])
        if opener is None:
            if not closes_tag:
                prose.append(text[start:marker.start()])
                opener = delimiter
        elif delimiter[0] == opener[0] and (closes_tag or (fence and delimiter[1] >= opener[1])):
            opener = None
            start = marker.end()
    if opener is None:
        prose.append(text[start:])
    text = "\n".join(prose)
    return safe_text("\n".join(line for line in text.splitlines() if not _CODE_LINE.match(line)), limit)


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def _daily_records(
    conversation: dict, owner_id: str, zone: tzinfo, cutoff: datetime | None
) -> Iterator[Record]:
    messages = _messages(conversation)
    identity = next(
        (conversation[key] for key in ("conversation_id", "id")
         if isinstance(conversation.get(key), str) and conversation[key].strip()),
        None,
    )
    if identity is None:
        identity = "fallback:" + _digest(conversation)

    title = conversation.get("title")
    title = _safe_prose(title, 120) if isinstance(title, str) else ""
    days: dict[date, list[tuple[datetime, str]]] = defaultdict(list)
    last_answer = None
    has_user = False
    for message in messages:
        at = _timestamp(message.get("create_time"))
        if at is None or (visible := _visible_message(message)) is None:
            continue
        try:
            at = at.astimezone(zone)
        except OverflowError:
            continue
        role, text = visible
        if role == "assistant":
            last_answer = at, text
        else:
            has_user = True
            if cutoff is None or at >= cutoff:
                days[at.date()].append((at, f"User: {text}"))
    if has_user and last_answer is not None:
        at, text = last_answer
        if cutoff is None or at >= cutoff:
            days[at.date()].append((at, f"Assistant: {text}"))

    for day, lines in days.items():
        lines.sort(key=lambda item: item[0].astimezone(timezone.utc))
        digest = _digest((owner_id, _SOURCE, identity, day.isoformat()))[:32]
        yield Record(
            id=f"chatgpt-{digest}",
            owner=owner_id,
            source=_SOURCE,
            at=lines[0][0].isoformat(),
            author="session",
            text="\n".join([f"Conversation: {title or 'ChatGPT'}", *(line for _, line in lines)]),
        )


def chatgpt_records(
    owner: Owner | str,
    path: str | Path,
    since: str | date | datetime | None = None,
) -> list[Record]:
    """Group visible ChatGPT text by conversation and owner-local day.

    Accept a conversation JSON file or a ZIP with conversation files at its
    root. ``since`` is inclusive and dates start at midnight in the owner's zone.
    """
    owner_id = owner if isinstance(owner, str) else owner.id
    zone = _zone("Asia/Dubai" if isinstance(owner, str) else owner.timezone)
    try:
        cutoff = _since(since, zone)
        # Compare absolute instants across ambiguous local clock hours.
        cutoff = cutoff.astimezone(timezone.utc) if cutoff is not None else None
    except (ValueError, AttributeError, TypeError, OverflowError):
        raise ValueError("ChatGPT export cutoff must be an ISO date or datetime") from None
    records: dict[str, Record] = {}
    for conversation in _conversations(Path(path)):
        for record in _daily_records(conversation, owner_id, zone, cutoff):
            records.setdefault(record.id, record)
    return sorted(records.values(), key=lambda record: (datetime.fromisoformat(record.at), record.id))
