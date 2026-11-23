"""Read bounded local agent session summaries from selected transcript roots."""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone, tzinfo
from pathlib import Path, PurePosixPath, PureWindowsPath
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from temporal_memory.models import Owner, Record

from ._redact import safe_text

_MAX_FILE_BYTES = 32 * 1024 * 1024
_MAX_LINE_BYTES = 512 * 1024
_MAX_LINES = 20_000
_MAX_ENTRIES = 10_000
_MAX_FILES = 1_000
_MAX_RECORDS = 2_000
_MAX_PROMPTS = 4
_MAX_PROMPT = 450
_MAX_SUMMARY = 900
_MAX_TITLE = 120

_CREDENTIAL_NAME = re.compile(
    r"token|credential|keychain|^(?:\.env|\.?oauth|\.aws$|\.ssh$|\.?secrets?(?:$|[._-])|"
    r"auth(?:$|[._-])|\.netrc$|\.npmrc$|id_(?:rsa|ed25519|ecdsa)|"
    r"(?:login data|local state|cookies|keyrings?|keystore)(?:$|[._-]))"
    r"|\.(?:key|pem|p12|pfx|kdbx)(?:$|\.)",
    re.I,
)
_NOISE_DIRS = {"subagents", "tool-results", "hooks"}
_WRAPPERS = re.compile(
    r"</?(?:system-reminder|system[-_]instructions?|developer[-_]message|user[-_]instructions|"
    r"environment_context|local-command-[\w-]+|command-(?:name|message|args)|"
    r"tool[_-](?:result|output)|task-notification|teammate-message|function_result|"
    r"turn_aborted|collaboration_mode|skill(?:_instructions)?|subagent_notification)\b"
    r"|^\s*(?:#\s*AGENTS\.md instructions|\*\*\* Begin Patch|diff --git\b|"
    r"Chunk ID:|Wall time:|Process exited with code|Output:)",
    re.I | re.M,
)
_DUMP = re.compile(
    r"^\s*(?:[+ -]{3} [ab]/|@@ -\d|(?:\x60{3}|~{3})(?:diff|patch|"
    r"json|jsonl|xml|yaml|toml|text|plaintext|log|bash|powershell|console)\b|"
    r"(?:begin |end )?(?:file|terminal|console) (?:contents?|dump|output):)"
    r"|</?(?:file_contents?|file_dump|terminal_output|console_output)\b",
    re.I | re.M,
)


def _denied(name: str) -> bool:
    name = name.rstrip(" .")
    return bool(_CREDENTIAL_NAME.search(name)) or name.casefold() in _NOISE_DIRS


def _is_link(info: os.stat_result) -> bool:
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
    )


def _root(path: Path) -> Path | None:
    try:
        path = path.absolute()
        # Validate ancestors before traversing a selected root.
        for directory in (*reversed(path.parents), path):
            if _denied(directory.name):
                return None
            info = directory.lstat()
            if _is_link(info) or not stat.S_ISDIR(info.st_mode):
                return None
        resolved = path.resolve(strict=True)
        if any(_denied(component.name) for component in (*resolved.parents, resolved)):
            return None
        return resolved
    except (OSError, ValueError):
        return None


def _files(root: Path, minimum_depth: int, maximum_depth: int) -> Iterator[Path]:
    pending = [(root, 0)]
    scanned = 0
    while pending and scanned < _MAX_ENTRIES:
        directory, depth = pending.pop()
        entries = []
        try:
            info = directory.lstat()
            if _is_link(info) or not stat.S_ISDIR(info.st_mode) or directory.resolve(strict=True) != directory:
                continue
            with os.scandir(directory) as listing:
                for entry in listing:
                    scanned += 1
                    if scanned > _MAX_ENTRIES:
                        return
                    if not _denied(entry.name):
                        entries.append(entry)
        except (OSError, ValueError):
            continue
        children = []
        for entry in sorted(entries, key=lambda item: item.name):
            try:
                info = entry.stat(follow_symlinks=False)
            except OSError:
                continue
            if _is_link(info):
                continue
            path = Path(entry.path)
            if stat.S_ISDIR(info.st_mode) and depth + 1 < maximum_depth:
                children.append((path, depth + 1))
            elif (
                stat.S_ISREG(info.st_mode) and minimum_depth <= depth + 1
                and path.suffix.lower() == ".jsonl"
                and 0 < info.st_size <= _MAX_FILE_BYTES
            ):
                yield path
        pending.extend(reversed(children))


def _rows(path: Path) -> Iterator[dict]:
    try:
        before = path.lstat()
        if (
            _denied(path.name) or _is_link(before) or not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1 or not 0 < before.st_size <= _MAX_FILE_BYTES
            or path.resolve(strict=True) != path
        ):
            return
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
        fd = os.open(path, flags | getattr(os, "O_NONBLOCK", 0))
        with os.fdopen(fd, "rb") as handle:
            opened = os.fstat(handle.fileno())
            if (
                not os.path.samestat(before, opened) or _is_link(opened)
                or not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1
                or not 0 < opened.st_size <= _MAX_FILE_BYTES
            ):
                return
            remaining = opened.st_size
            for _ in range(_MAX_LINES):
                if not remaining:
                    break
                line = handle.readline(min(_MAX_LINE_BYTES + 1, remaining))
                if not line or len(line) > _MAX_LINE_BYTES:
                    break
                remaining -= len(line)
                try:
                    row = json.loads(line)
                except (ValueError, RecursionError):
                    continue
                if isinstance(row, dict):
                    yield row
    except (OSError, ValueError):
        return


def _zone(name: str) -> tzinfo:
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        # Dubai has a fixed UTC+4 offset over the supported CLIs' lifetime.
        if name == "Asia/Dubai":
            return timezone(timedelta(hours=4), name)
        if name in {"UTC", "Etc/UTC"}:
            return timezone.utc
        raise


def _timestamp(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _since(value: str | date | datetime | None, zone: tzinfo) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=zone)
    return datetime(value.year, value.month, value.day, tzinfo=zone)


def _basename(value: object) -> str:
    if isinstance(value, str):
        path = PureWindowsPath(value) if "\\" in value or re.match(r"^[A-Za-z]:", value) else PurePosixPath(value)
        if path.name not in {"", ".", ".."}:
            return safe_text(path.name, 100)
    return ""


def _conversation_text(content: object, types: set[str], limit: int) -> str:
    if isinstance(content, list):
        content = "\n".join(
            block["text"] for block in content
            if isinstance(block, dict) and isinstance(block.get("type"), str)
            and block["type"] in types and isinstance(block.get("text"), str)
        )
    if not isinstance(content, str):
        return ""
    text = content.strip()
    if not text or _WRAPPERS.search(text) or _DUMP.search(text):
        return ""
    if text.startswith(("{", "[")):
        try:
            decoded = json.loads(text)
        except (ValueError, RecursionError):
            pass
        else:
            if isinstance(decoded, (dict, list)):
                return ""
    return safe_text(text, limit)


@dataclass
class _Day:
    at: datetime
    prompts: list[str] = field(default_factory=list)
    summary: tuple[int, datetime, str] | None = None

    def add(self, at: datetime, role: str, text: str, priority: int) -> None:
        self.at = min(self.at, at)
        if role == "user":
            if len(self.prompts) < _MAX_PROMPTS and text not in self.prompts:
                self.prompts.append(text)
        elif self.summary is None or (priority, at) >= self.summary[:2]:
            self.summary = (priority, at, text)


@dataclass
class _Session:
    title: str = ""
    project: str = ""
    identity: str = ""
    days: dict[date, _Day] = field(default_factory=dict)


_Message = tuple[str, str, int]
_EMPTY: _Message = "", "", 0


def _claude(row: dict, session: _Session) -> _Message:
    kind = row.get("type")
    if not session.project:
        session.project = _basename(row.get("cwd"))
    if not session.identity and isinstance(row.get("sessionId"), str):
        session.identity = row["sessionId"]
    if kind in ("ai-title", "custom-title"):
        title = row.get("aiTitle" if kind == "ai-title" else "customTitle")
        session.title = _conversation_text(title, {"text"}, _MAX_TITLE) or session.title
    if kind not in ("user", "assistant") or any(
        row.get(flag) for flag in (
            "isMeta", "isSidechain", "isCompactSummary", "isVisibleInTranscriptOnly", "isApiErrorMessage"
        )
    ):
        return _EMPTY
    message = row.get("message")
    priority = 0
    if isinstance(message, dict) and message.get("role", kind) == kind:
        content = message.get("content")
        if isinstance(content, list) and any(
            isinstance(block, dict) and block.get("type") in ("tool_result", "tool_use") for block in content
        ):
            return _EMPTY
        stop = message.get("stop_reason")
        if kind == "assistant" and stop not in (None, "end_turn", "stop_sequence"):
            return _EMPTY
        priority = int(stop in ("end_turn", "stop_sequence"))
    elif isinstance(message, str):
        content = message
    else:
        return _EMPTY
    return kind, _conversation_text(content, {"text"}, _MAX_PROMPT if kind == "user" else _MAX_SUMMARY), priority


def _codex(row: dict, session: _Session) -> _Message:
    kind = row.get("type")
    payload = row.get("payload")
    if not isinstance(payload, dict):
        return _EMPTY
    subtype = payload.get("type")
    if kind == "session_meta":
        session.project = _basename(payload.get("cwd")) or session.project
        if isinstance(payload.get("id"), str):
            session.identity = payload["id"]
        session.title = _conversation_text(payload.get("title"), {"text"}, _MAX_TITLE) or session.title
    if kind == "event_msg" and subtype in ("user_message", "agent_message", "task_complete"):
        if subtype == "user_message":
            role, content = "user", payload.get("message")
        elif subtype == "task_complete":
            role, content = "assistant", payload.get("last_agent_message")
        elif payload.get("phase") == "final_answer":
            role, content = "assistant", payload.get("message")
        else:
            return _EMPTY
        priority = 0
    elif kind == "response_item" and subtype == "message" and payload.get("role") in ("user", "assistant"):
        role = payload["role"]
        content = payload.get("content")
        priority = 1
    else:
        return _EMPTY
    if role == "assistant" and payload.get("phase") not in (None, "final_answer"):
        return _EMPTY
    types = {"text", "input_text"} if role == "user" else {"text", "output_text"}
    return role, _conversation_text(content, types, _MAX_PROMPT if role == "user" else _MAX_SUMMARY), priority


def _parse(
    path: Path, parser: Callable[[dict, _Session], _Message], zone: tzinfo, cutoff: datetime | None,
) -> _Session:
    session = _Session()
    for row in _rows(path):
        role, text, priority = parser(row, session)
        if not text:
            continue
        at = _timestamp(row.get("timestamp"))
        if at is None or (cutoff is not None and at < cutoff):
            continue
        try:
            at = at.astimezone(zone)
        except (OverflowError, ValueError):
            continue
        local_day = at.date()
        if local_day not in session.days:
            session.days[local_day] = _Day(at)
        session.days[local_day].add(at, role, text, priority)
    return session


def _records(owner: str, source: str, session: _Session, fallback_id: str) -> Iterator[Record]:
    for day, group in sorted(session.days.items()):
        title = session.title or "Agent session"
        lines = [f"Session: {title}"]
        if session.project:
            lines.append(f"Project: {session.project}")
        lines.extend(f"User: {prompt}" for prompt in group.prompts)
        if group.summary is not None:
            lines.append(f"Assistant: {group.summary[2]}")
        key = json.dumps((owner, source, session.identity or fallback_id, day.isoformat()))
        digest = hashlib.sha256(key.encode()).hexdigest()[:32]
        yield Record(
            id=f"agent-{digest}",
            owner=owner,
            source=f"agent:{source}",
            at=group.at.isoformat(),
            author="session",
            text="\n".join(lines),
        )


def agent_session_records(
    owner: Owner | str,
    roots: dict[str, Path] | None = None,
    since: str | date | datetime | None = None,
) -> list[Record]:
    """Summarise genuine messages in one record per source, session and owner day.

    Explicit roots directly name the caller-approved projects or sessions
    directories. For an explicitly initiated local import, pass None to resolve
    the supported default roots. A date cutoff is local to the owner.
    """
    if roots is None:
        home = Path.home()
        roots = {"claude-code": home / ".claude" / "projects", "codex": home / ".codex" / "sessions"}
    owner_id = owner if isinstance(owner, str) else owner.id
    zone = _zone("Asia/Dubai" if isinstance(owner, str) else owner.timezone)
    cutoff = _since(since, zone)
    selected = {}
    for name, path in roots.items():
        canonical = name.lower().removeprefix("agent:").replace("_", "-")
        selected["claude-code" if canonical in {"claude", "claudecode"} else canonical] = path
    # TODO: Gemini needs verified local transcript discovery and message schemas.
    # TODO: Copilot needs a verified transcript format independent of token stores.
    # TODO: Cursor needs verified transcript timestamps and safe read-only discovery.
    adapters = {"claude-code": (_claude, 2, 2), "codex": (_codex, 1, 12)}
    records: dict[str, Record] = {}
    for source, (parser, minimum_depth, maximum_depth) in adapters.items():
        if source not in selected or (root := _root(Path(selected[source]))) is None:
            continue
        for index, path in enumerate(_files(root, minimum_depth, maximum_depth)):
            if index >= _MAX_FILES:
                break
            session = _parse(path, parser, zone, cutoff)
            for record in _records(owner_id, source, session, path.relative_to(root).as_posix()):
                records.setdefault(record.id, record)
                if len(records) >= _MAX_RECORDS:
                    return sorted(records.values(), key=lambda item: (item.at, item.id))
    return sorted(records.values(), key=lambda item: (item.at, item.id))
