"""Read explicitly selected Chromium profile history and emit daily aggregates."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Iterator
from contextlib import closing, contextmanager
from datetime import date, datetime, time, timedelta, timezone, tzinfo
from io import BufferedReader
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import stat
from tempfile import TemporaryDirectory
import unicodedata
from urllib.parse import SplitResult, parse_qsl, unquote, urlsplit
from zoneinfo import ZoneInfo

from ...models import Owner, Record
from ...privacy.sensitive import pre_write

DEFAULT_DENY_DOMAINS = frozenset({
    "bankofamerica.com", "chase.com", "wellsfargo.com", "citi.com", "hsbc.com",
    "adcb.com", "emiratesnbd.com", "bankfab.com", "mashreqbank.com", "paypal.com",
    "webmd.com", "mayoclinic.org", "healthline.com", "mychart.com", "clevelandclinic.org",
    "zocdoc.com", "nhs.uk", "plannedparenthood.org", "medlineplus.gov", "cdc.gov",
    "pornhub.com", "xvideos.com", "xnxx.com", "xhamster.com", "onlyfans.com",
    "redtube.com", "youporn.com", "gov", "mil", "int", "whitehouse.gov", "u.ae",
})
_PRIVATE_SUFFIXES = {"localhost", "local", "localdomain", "internal", "intranet", "lan",
                     "corp", "home", "onion", "invalid", "arpa", "private", "test"}
_PRIVATE_LABELS = {"localhost", "intranet"}
_PRIVATE_DNS_DOMAINS = {"nip.io", "sslip.io", "xip.io", "localtest.me", "lvh.me",
                        "localhost.direct", "127-0-0-1.org"}
_SENSITIVE_DOMAIN_LABEL = re.compile(
    r"(?:^|[.-])(?:bank(?:ing)?|onlinebanking|creditunion|health(?:care)?|hospital|clinic|"
    r"medical|pharmacy|adult|porn(?:ography)?|xxx|gov(?:ernment)?|gouv|gob|govt|mil)(?:[.-]|$)",
    re.I,
)
_LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\Z", re.ASCII)
_CREDENTIAL_KEY = re.compile(
    r"(?:^|[^a-z])(?:pass(?:word|code|wd)?|pwd|otp|pin|cvv|credentials?|secret|"
    r"(?:access|auth|refresh|session|id)[_-]?tokens?|tokens?|auth(?:orization)?|"
    r"api[_-]?key|session(?:id)?|jwt|signature|login|email|username)(?:[^a-z]|$)", re.I,
)
_EXTRA_SENSITIVE = re.compile(
    r"\b(?:porn\w*|xxx|nsfw|nude\w*|nudity|explicit|sex|erotic\w*|fetish\w*|"
    r"bank(?:s|ing|er)?|mortgage\w*|loan\w*|salary|paycheck|personal finance|"
    r"credit card|credit score|tax(?:es)?|medical\w*|adhd|autism|suicid\w*|"
    r"addiction|hormone\w*|diabet\w*|passport|immigration|govt)\b",
    re.I,
)
_WATCH_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com",
                "youtu.be", "www.youtu.be"}
_CHANNEL = re.compile(r"@[A-Za-z][A-Za-z0-9_.-]{2,29}\Z", re.ASCII)
_ATTRIBUTION = re.compile(r"(?:\bchannel\s*:\s*|\s+by\s+)(@[\w.-]+)(?=\s|$)", re.I)
_VIDEO_ID = re.compile(r"[-_A-Za-z0-9]{11}\Z", re.ASCII)
_TOPICS = {
    "Cooking": r"\b(?:cooking|recipes?|baking|bread making)\b",
    "Photography": r"\b(?:photography|camera lenses?)\b",
    "Programming": r"\b(?:programming|coding|python|javascript|software development)\b",
    "Gardening": r"\b(?:gardening|growing vegetables|vegetable garden)\b",
    "Music": r"\b(?:music theory|piano|guitar|songwriting)\b",
    "Art": r"\b(?:watercolou?r|drawing|illustration|oil painting)\b",
    "Woodworking": r"\b(?:woodworking|carpentry|woodturning)\b",
    "Astronomy": r"\b(?:astronomy|astrophotography|telescope|solar system)\b",
    "Fitness": r"\b(?:fitness|strength training|workout|weightlifting)\b",
    "Gaming": r"\b(?:gaming|video games?|gameplay)\b",
}
_TOPIC_PATTERNS = {topic: re.compile(pattern, re.I) for topic, pattern in _TOPICS.items()}
_CHROMIUM_EPOCH = datetime(1601, 1, 1, tzinfo=timezone.utc)
_MAX_BOOKMARK_BYTES = 64 * 1024 * 1024
_HISTORY_COLUMNS = {"urls": {"id", "url", "title"}, "visits": {"url", "visit_time"}}


class BrowserProfileError(ValueError):
    """The selected profile cannot be safely read."""


def _signature(info: os.stat_result) -> tuple[int, ...]:
    # Windows stat and fstat can report different st_ctime for the same handle.
    return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink, info.st_size,
            info.st_mtime_ns)


def _stat(path: Path, *, directory: bool = False) -> os.stat_result:
    info = path.lstat()
    reparse = getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
    valid_type = stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)
    if reparse or not valid_type or (not directory and info.st_nlink != 1):
        raise BrowserProfileError("Browser profile paths must use ordinary local directories and files")
    return info


def _profile(profile_dir: str | os.PathLike[str]) -> Path:
    path = Path(profile_dir)
    if path.drive.startswith("\\\\") or ".." in path.parts or (path.drive and not path.is_absolute()):
        raise BrowserProfileError("Select a local Chromium profile directory without traversal")
    is_reserved = getattr(os.path, "isreserved", None)
    for part in path.parts[1 if path.anchor else 0:]:
        reserved = os.name == "nt" and (is_reserved(part) if is_reserved else Path(part).is_reserved())
        if any(char in part for char in '<>:"|?*') or part.endswith((" ", ".")) or reserved:
            raise BrowserProfileError("Invalid browser profile path")
    path = path.absolute()
    try:
        _validate_directories(path)
    except OSError:
        raise BrowserProfileError("Browser profile directory is missing or inaccessible") from None
    return path


def _validate_directories(path: Path) -> None:
    for directory in reversed((path, *path.parents)):
        _stat(directory, directory=True)


def _optional_stat(path: Path) -> os.stat_result | None:
    try:
        return _stat(path)
    except FileNotFoundError:
        return None


@contextmanager
def _open_file(path: Path, expected: os.stat_result) -> Iterator[BufferedReader]:
    _validate_directories(path.parent)
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    handle = os.open(path, flags | getattr(os, "O_NONBLOCK", 0))
    with os.fdopen(handle, "rb") as source:
        _validate_directories(path.parent)
        if (_signature(os.fstat(source.fileno())) != _signature(expected)
                or _signature(_stat(path)) != _signature(expected)):
            raise OSError("Browser source changed before it could be read")
        yield source
        if _signature(os.fstat(source.fileno())) != _signature(expected):
            raise OSError("Browser source changed while it was being read")


def _copy_file(path: Path, info: os.stat_result, target: Path) -> None:
    with _open_file(path, info) as source, target.open("wb") as destination:
        shutil.copyfileobj(source, destination)


@contextmanager
def _history(profile: Path) -> Iterator[sqlite3.Connection]:
    history = profile / "History"
    wal = profile / "History-wal"
    try:
        _stat(history)
    except FileNotFoundError:
        raise BrowserProfileError("History is missing from the selected browser profile") from None
    except OSError:
        raise BrowserProfileError("History is locked or inaccessible") from None

    # Chromium timestamp epoch and copy-before-query approach ported from
    # scripts/extract_youtube_history.py. Copy the WAL too to retain committed visits.
    with TemporaryDirectory(prefix="tm-browser-") as directory:
        for _ in range(3):
            try:
                sources = [(history, _stat(history)), (wal, _optional_stat(wal))]
                for path, info in sources:
                    target = Path(directory) / path.name
                    if info is None:
                        target.unlink(missing_ok=True)
                        continue
                    _copy_file(path, info, target)
                before = tuple(_signature(info) if info else None for _, info in sources)
                after = tuple(_signature(info) if info else None
                              for info in (_stat(history), _optional_stat(wal)))
                if before == after:
                    break
            except OSError:
                continue
        else:
            raise BrowserProfileError("History is locked, inaccessible, or changing. Close the browser and retry")

        uri = (Path(directory) / "History").as_uri() + "?mode=ro"
        try:
            with closing(sqlite3.connect(uri, uri=True)) as connection:
                connection.execute("PRAGMA trusted_schema = OFF")
                tables = connection.execute(
                    "SELECT name, type FROM pragma_table_list WHERE schema = 'main' "
                    "AND name IN ('visits', 'urls')"
                ).fetchall()
                if dict(tables) != dict.fromkeys(_HISTORY_COLUMNS, "table"):
                    raise BrowserProfileError("History is malformed or does not have the Chromium schema")
                for table, required in _HISTORY_COLUMNS.items():
                    columns = connection.execute(f"PRAGMA main.table_xinfo({table})")
                    if not required.issubset(row[1] for row in columns if row[6] == 0):
                        raise BrowserProfileError("History is malformed or does not have the Chromium schema")
                yield connection
        except sqlite3.Error as exc:
            if getattr(exc, "sqlite_errorcode", None) in {sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED}:
                raise BrowserProfileError("History is locked. Close the browser and retry") from None
            raise BrowserProfileError("History is malformed or does not have the Chromium schema") from None


def _deny_domains(domains: Iterable[str] | None) -> frozenset[str]:
    if domains is None:
        return DEFAULT_DENY_DOMAINS
    if isinstance(domains, str):
        domains = (domains,)
    try:
        custom = {domain.strip().strip(".").encode("idna").decode("ascii").lower()
                  for domain in domains}
    except (AttributeError, UnicodeError):
        raise ValueError("deny_domains must contain DNS domain names") from None
    if any(not all(_LABEL.fullmatch(label) for label in domain.split(".")) for domain in custom):
        raise ValueError("deny_domains must contain DNS domain names")
    return DEFAULT_DENY_DOMAINS | custom


def _decode(value: str) -> str:
    # Decode twice to screen URLs with a nested layer of percent encoding.
    return unquote(unquote(value))


def _url(value: object, denied: frozenset[str]) -> tuple[str, SplitResult] | None:
    if not isinstance(value, str) or any(c.isspace() or ord(c) < 32 for c in value) or "\\" in value:
        return None
    try:
        parts = urlsplit(value)
        if parts.scheme not in {"http", "https"} or "@" in parts.netloc or "%" in parts.netloc:
            return None
        host = (parts.hostname or "").rstrip(".").encode("idna").decode("ascii").lower()
        if parts.port not in {None, 80, 443}:
            return None
    except (ValueError, UnicodeError):
        return None
    labels = host.split(".")
    if (len(labels) < 2 or len(host) > 253 or not labels[-1][0:1].isalpha()
            or not all(_LABEL.fullmatch(label) for label in labels)):
        return None
    if (labels[-1] in _PRIVATE_SUFFIXES or _PRIVATE_LABELS.intersection(labels)
            or _SENSITIVE_DOMAIN_LABEL.search(host) or pre_write(re.sub(r"[._-]", " ", host))
            or any(host == domain or host.endswith("." + domain)
                   for domain in denied | _PRIVATE_DNS_DOMAINS)):
        return None
    for component in (parts.path, parts.query, parts.fragment):
        decoded = _decode(component)
        if _CREDENTIAL_KEY.search(decoded) or pre_write(decoded.replace("_", " ")) == "credential":
            return None
    if any(key.lower() in {"code", "samlresponse", "assertion", "sso"}
           for component in (parts.query, parts.fragment)
           for key, _ in parse_qsl(component)):
        return None
    return host, parts


def _is_watch(host: str, parts: SplitResult) -> bool:
    return host in _WATCH_HOSTS and (
        host in {"youtu.be", "www.youtu.be"} or parts.path.rstrip("/") == "/watch"
    )


def _watch_id(host: str, parts: SplitResult) -> str | None:
    if not _is_watch(host, parts):
        return None
    if host in {"youtu.be", "www.youtu.be"}:
        video_id = parts.path.strip("/")
    else:
        values = [value for key, value in parse_qsl(parts.query) if key == "v"]
        video_id = values[0] if len(values) == 1 else ""
    return video_id if _VIDEO_ID.fullmatch(video_id) else None


def _bookmarks(profile: Path, denied: frozenset[str]) -> dict[str, list[str]]:
    path = profile / "Bookmarks"
    try:
        info = _optional_stat(path)
        if info is None or info.st_size > _MAX_BOOKMARK_BYTES:
            return {}
        with TemporaryDirectory(prefix="tm-bookmarks-") as directory:
            target = Path(directory) / "Bookmarks"
            _copy_file(path, info, target)
            data = json.loads(target.read_bytes())
    except BrowserProfileError:
        raise
    except (OSError, UnicodeError, ValueError, RecursionError):
        return {}
    if not isinstance(data, dict) or not isinstance(data.get("roots"), dict):
        return {}
    by_video = defaultdict(list)
    nodes = list(data["roots"].values())
    while nodes:
        node = nodes.pop()
        if not isinstance(node, dict):
            continue
        if isinstance(node.get("children"), list):
            nodes.extend(node["children"])
        if node.get("type") == "url" and isinstance(node.get("name"), str):
            parsed = _url(node.get("url"), denied)
            if parsed and (video_id := _watch_id(*parsed)):
                by_video[video_id].append(node["name"])
    return by_video


def _sensitive(text: str) -> bool:
    normalized = unicodedata.normalize("NFKC", text)
    separated = re.sub(r"([a-z])([A-Z])", r"\1 \2", normalized)
    separated = re.sub(r"[._-]", " ", separated)
    return bool(pre_write(normalized) or pre_write(separated) or _EXTRA_SENSITIVE.search(separated))


def _watch_interest(parts: SplitResult, title: str, bookmarks: list[str]) -> str | None:
    titles = [title, *bookmarks]
    # Screen channel hints, but attribute only from explicit handles in a title.
    hints = [value for key, value in parse_qsl(parts.query) if key in {"channel", "creator"}]
    handles = {match.group(1) for text in titles for match in _ATTRIBUTION.finditer(text)}
    if any(_sensitive(text) for text in [*titles, *hints, *handles]):
        return None
    normalized_handles = {handle.lower() for handle in handles}
    if len(normalized_handles) == 1:
        handle = next(iter(normalized_handles))
        if _CHANNEL.fullmatch(handle) and not _VIDEO_ID.fullmatch(handle[1:]):
            return f"channel {handle}"
    topics = {topic for topic, pattern in _TOPIC_PATTERNS.items()
              if any(pattern.search(text) for text in titles)}
    if len(topics) == 1:
        return f"topic {next(iter(topics))}"
    return "watch interest"


def _zone(owner: Owner | str) -> tzinfo:
    name = owner.timezone if isinstance(owner, Owner) else "Asia/Dubai"
    try:
        return ZoneInfo(name)
    except LookupError:
        # Windows may lack IANA tzdata. Dubai has used UTC+04 since 1920.
        if name == "Asia/Dubai":
            return timezone(timedelta(hours=4), "Asia/Dubai")
        if name in {"UTC", "Etc/UTC"}:
            return timezone.utc
        raise ValueError("The owner's browser import time zone is unavailable") from None


def _since(value: date | datetime | str | None, zone: tzinfo) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    if isinstance(value, date) and not isinstance(value, datetime):
        value = datetime.combine(value, time.min)
    if value.tzinfo is None:
        value = value.replace(tzinfo=zone)
    return value.astimezone(timezone.utc)


def _visits(
    profile: Path, denied: frozenset[str], cutoff: datetime | None = None,
) -> Iterator[tuple[datetime, str, str | None]]:
    bookmarks = _bookmarks(profile, denied)
    with _history(profile) as connection:
        for raw_url, raw_title, stamp in connection.execute(
            "SELECT urls.url, urls.title, visits.visit_time "
            "FROM visits JOIN urls ON visits.url = urls.id"
        ):
            if not isinstance(stamp, int) or stamp <= 0:
                continue
            try:
                at = _CHROMIUM_EPOCH + timedelta(microseconds=stamp)
            except OverflowError:
                continue
            if cutoff is not None and at < cutoff:
                continue
            parsed = _url(raw_url, denied)
            title = raw_title if isinstance(raw_title, str) else ""
            if parsed is None or pre_write(title) == "credential":
                continue
            host, parts = parsed
            interest = None
            if _is_watch(host, parts):
                video_id = _watch_id(host, parts)
                bookmarked_titles = bookmarks.get(video_id, []) if video_id else []
                interest = _watch_interest(parts, title, bookmarked_titles)
                if interest is None:
                    continue
            yield at, host, interest


def preview(profile_dir: str | os.PathLike[str]) -> dict[str, int]:
    """Return domain visit counts for an explicitly selected Chromium profile."""
    profile = _profile(profile_dir)
    counts = Counter(host for _, host, _ in _visits(profile, DEFAULT_DENY_DOMAINS))
    return dict(sorted(counts.items()))


def browser_records(
    owner: Owner | str,
    profile_dir: str | os.PathLike[str],
    since: date | datetime | str | None = None,
    deny_domains: Iterable[str] | None = DEFAULT_DENY_DOMAINS,
) -> list[Record]:
    """Return one aggregate per owner-local calendar day, with an inclusive cutoff."""
    profile = _profile(profile_dir)
    zone = _zone(owner)
    cutoff = _since(since, zone)
    denied = _deny_domains(deny_domains)
    visits = defaultdict(Counter)
    watches = defaultdict(Counter)
    for at, host, interest in _visits(profile, denied, cutoff):
        day = at.astimezone(zone).date()
        if interest:
            watches[day][interest] += 1
        visits[day][host] += 1

    owner_id = owner.id if isinstance(owner, Owner) else owner
    profile_key = os.path.normcase(str(profile))
    records = []
    for day, domains in sorted(visits.items()):
        lines = [f"Browser visits to {domain}: {count}" for domain, count in sorted(domains.items())]
        lines.extend(f"YouTube {interest}: {count}" for interest, count in sorted(watches[day].items()))
        identity = json.dumps([owner_id, profile_key, day.isoformat()]).encode("utf-8")
        records.append(Record(
            id=f"browser:{sha256(identity).hexdigest()}",
            owner=owner_id,
            source="browser",
            at=datetime.combine(day, time.min, zone).isoformat(),
            author="Browser history",
            text="\n".join(lines),
        ))
    return records
