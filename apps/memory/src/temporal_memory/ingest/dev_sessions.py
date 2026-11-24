"""Developer session and git commit importer with secret and path redaction."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any

from temporal_memory.models import Record

# ported from G:\Haitham\VsCode\contest\scripts\extract_dev_sessions.py:25-40
SECRET_PATTERNS = [
    re.compile(r"(?<![\w])\.env[\w.-]*", re.I),
    re.compile(r"^[ \t]*(?:export[ \t]+)?[A-Z][A-Z0-9_]{2,}[ \t]*=[ \t]*\S.*$", re.M),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?(-----END [A-Z ]*PRIVATE KEY-----|$)", re.M),
    re.compile(r"\b(sk|pk|rk)-[A-Za-z0-9_-]{16,}"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{16,}", re.I),
    re.compile(r"\b(api[_-]?key|token|secret|password|passwd)\b\s*[:=]\s*['\"]?[^\s'\",;]+", re.I),
]

_WIN_PATH_PATTERN = re.compile(r"[A-Za-z]:\\[^\s'\"]+")
_UNIX_PATH_PATTERN = re.compile(r"/(?:Users|home|root|etc|var)/[^\s'\"]+")


def redact(text: str) -> str:
    """Redact credentials, .env tokens, Windows paths, and Unix home/system paths."""
    cleaned = text or ""
    for pattern in SECRET_PATTERNS:
        cleaned = pattern.sub("[redacted]", cleaned)
    cleaned = _WIN_PATH_PATTERN.sub("[redacted-path]", cleaned)
    cleaned = _UNIX_PATH_PATTERN.sub("[redacted-path]", cleaned)
    return cleaned


def _normalize_ts(raw_ts: Any, fallback: str = "") -> str:
    val = str(raw_ts or "").strip() or fallback
    if not val:
        return ""
    try:
        dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt.isoformat(timespec="seconds")
    except ValueError:
        return val


def parse_dev_sessions(path: str | Path, owner: str) -> list[Record]:
    """Parse dev_sessions JSON into concise, redacted project/subject evidence Records."""
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError("dev_sessions JSON must be an object")

    extracted_at = _normalize_ts(data.get("extracted_at"))
    records: list[Record] = []

    sessions = data.get("claude_sessions") or []
    for idx, sess in enumerate(sessions):
        if not isinstance(sess, dict):
            continue
        source_tool = redact(str(sess.get("source") or "claude").strip())
        project = redact(str(sess.get("project") or "").strip())
        branch = redact(str(sess.get("git_branch") or "").strip())
        title = redact(str(sess.get("title") or "").strip())
        total_prompts = int(sess.get("total_prompts") or 0)
        at = _normalize_ts(sess.get("timestamp"), extracted_at)

        parts = [f"Dev session ({source_tool})"]
        if project:
            parts.append(f"project={project}")
        if branch:
            parts.append(f"branch={branch}")
        parts.append(f"prompts={total_prompts}")
        header = " ".join(parts)
        text = f"{header}: {title}" if title else header

        records.append(
            Record(
                id=f"dev-sess-{idx:04d}",
                owner=owner,
                source="dev_sessions",
                at=at,
                author="owner",
                text=text,
                generation=0,
            )
        )

    commits = data.get("recent_git_commits") or []
    for idx, commit in enumerate(commits):
        if not isinstance(commit, dict):
            continue
        commit_hash = str(commit.get("hash") or "").strip()
        short_hash = commit_hash[:8] if commit_hash else f"{idx:04d}"
        author = redact(str(commit.get("author") or "owner").strip()) or "owner"
        message = redact(str(commit.get("message") or "").strip())
        at = _normalize_ts(commit.get("date"), extracted_at)
        text = f"Git commit {short_hash}: {message}" if message else f"Git commit {short_hash}"

        records.append(
            Record(
                id=f"dev-commit-{commit_hash[:12] or f'{idx:04d}'}",
                owner=owner,
                source="dev_sessions",
                at=at,
                author=author,
                text=text,
                generation=0,
            )
        )

    records.sort(key=lambda r: (r.at, r.id))
    return records
