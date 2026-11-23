"""Local sanitisation for agent transcripts."""
from __future__ import annotations

import re
import unicodedata

from temporal_memory.privacy.sensitive import pre_write

# Ported from scripts/extract_dev_sessions.py:26-40. Expanded for session imports.
_SECRETS = (
    re.compile(r"^[ \t]*(?:export[ \t]+)?[A-Z][A-Z0-9_]{2,}[ \t]*=[ \t]*\S.*$", re.M),
    re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----[\s\S]*?(?:-----END [A-Z0-9 ]*PRIVATE KEY-----|$)", re.I),
    re.compile(r"\b(?:sk|pk|rk)-[A-Za-z0-9_-]{16,}"),
    re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})"),
    re.compile(r"\b(?:AIza[A-Za-z0-9_-]{30,}|(?:AKIA|ASIA)[A-Z0-9]{16}|xox[baprs]-[A-Za-z0-9-]{10,})"),
    re.compile(r"\b(?:Bearer|Basic)\s+[A-Za-z0-9._~+/=-]{4,}", re.I),
    re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"),
    re.compile(r"(?<!\w)[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]){11,30}(?!\w)"),
    re.compile(r"(?<!\w)(?:\d[ -]?){12,18}\d(?!\w)"),
    re.compile(
        r"""(?<![\w-])(?:[\w-]+[_-])?(?:api[_-]?key|token|secret|password|passwd|"""
        r"""authorization|client[_-]?secret)["']?\s*[:=]\s*(?:"(?:[^"\\\r\n]|\\[^\r\n])*(?:"|$)|"""
        r"""'(?:[^'\\\r\n]|\\[^\r\n])*(?:'|$)|[^\s'"\x60,;\]}]+)""",
        re.I | re.M,
    ),
    re.compile(r"(?<=://)[^/\s:@]+:[^/\s@]+@"),
)
_WINDOWS_PATH = r"(?:[A-Z]:[\\/]|\\\\)"
_PATH_START = rf"(?:file://|{_WINDOWS_PATH}|//[^/]|~/|/(?!/))"
_PATHS = (
    re.compile(r"""(?<!\w)(?P<quote>["'`])""" + _PATH_START + r"[^\r\n]*?(?P=quote)", re.I),
    re.compile(
        r"(?<![\w/.-])" + _WINDOWS_PATH
        + r"""(?:[^\r\n"'\x60<>|;,()\[\]{}\\/]*[\\/])*[^\s"'\x60<>|;,()\[\]{}]*""",
        re.I,
    ),
    re.compile(r"""(?<![\w/.-])file://[^\s"'\x60<>|;,()\[\]{}]*""", re.I),
    re.compile(r"""(?:(?<![\w/.-])~?/(?!/)|(?<![\w:/.-])//[^/])[^\s"'\x60<>|;,()\[\]{}]*"""),
)
_ENV = re.compile(r"(?<!\w)\.env[\w.-]*", re.I)
_SURROGATE = re.compile(r"[\ud800-\udfff]")
_REPLACEMENT = "[redacted]"


def safe_text(text: str, limit: int) -> str:
    text = unicodedata.normalize("NFKC", _SURROGATE.sub("\ufffd", text))
    for pattern in _SECRETS:
        text = pattern.sub(_REPLACEMENT, text)
    for pattern in _PATHS:
        text = pattern.sub(_REPLACEMENT, text)
    text = _ENV.sub(_REPLACEMENT, text)
    if pre_write(text) is not None or not text.replace(_REPLACEMENT, "").strip():
        return ""
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit - 1].rstrip() + "…"
