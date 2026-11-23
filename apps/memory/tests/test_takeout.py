"""WP-J Google Takeout importer tests (synthetic data only).

Fixture shapes are Google's documented Takeout structures, verified:
watch/search-history.json = [{header, title:"Watched X"|"Searched for X",
titleUrl, subtitles:[{name:channel}], time:ISO-8601, products}];
BrowserHistory.json = {"Browser History":[{title,url,time_usec}]};
MyActivity.json = [{header:"Gemini Apps", title:"Prompted ...", subtitles,
time:ISO-8601, products}].
"""
from __future__ import annotations

from datetime import date, datetime, timezone
import json
from pathlib import Path
import zipfile

import pytest

from temporal_memory.ingest import takeout
from temporal_memory.ingest.takeout import TakeoutError, takeout_records
from temporal_memory.models import Owner

OWNER = Owner(id="karim", label="Karim", kind="simulated",
              display_name="Karim Haddad", timezone="Asia/Dubai")
FIXTURE_DIR = Path(__file__).parent / "fixtures" / "takeout"
DAY = "2026-10-21"


def _blob(records) -> str:
    return "\n".join(f"{r.id}\n{r.source}\n{r.at}\n{r.author}\n{r.text}" for r in records)


def _yt_watch(title, channel="Fireship", when=f"{DAY}T09:15:33.000Z", vid="abc123XYZ09"):
    return {"header": "YouTube", "title": f"Watched {title}",
            "titleUrl": f"https://www.youtube.com/watch?v={vid}",
            "subtitles": [{"name": channel}], "time": when, "products": ["YouTube"]}


def _yt_search(query, when=f"{DAY}T09:15:33.000Z"):
    return {"header": "YouTube", "title": f"Searched for {query}",
            "titleUrl": "https://www.youtube.com/results?search_query=x",
            "time": when, "products": ["YouTube"]}


def _usec(iso: str) -> int:
    return int(datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp() * 1_000_000)


def _chrome(url, title="A page", when=f"{DAY}T13:47:29.000Z"):
    return {"title": title, "url": url, "time_usec": _usec(when)}


def _gemini(prompt, when=f"{DAY}T08:00:00.000Z", header="Gemini Apps"):
    return {"header": header, "title": f"Prompted {prompt}",
            "subtitles": [{"name": "RAW_RESPONSE_993"}], "time": when,
            "products": ["Gemini Apps"]}


def _zip(path: Path, members: dict[str, object]) -> Path:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, payload in members.items():
            data = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
            zf.writestr(name, data)
    return path


def _full_zip(tmp_path: Path) -> Path:
    return _zip(tmp_path / "takeout.zip", {
        "Takeout/YouTube and YouTube Music/history/watch-history.json": [
            _yt_watch("Python FastAPI Tutorial RAW_TITLE_991"),
            _yt_watch("Blender Render Nodes", channel="Blender Guru",
                      when=f"{DAY}T17:00:00.000Z", vid="def456XYZ09"),
        ],
        "Takeout/YouTube and YouTube Music/history/search-history.json": [
            _yt_search("postgres tutorial"),
        ],
        "Takeout/Chrome/BrowserHistory.json": {"Browser History": [
            _chrome("https://docs.python.org/3/tutorial/", "Python docs"),
            _chrome("https://stackoverflow.com/questions/1", "Stack Overflow"),
        ]},
        "Takeout/My Activity/Gemini Apps/MyActivity.json": [
            _gemini("Summarise my meeting notes about the Dubai launch"),
        ],
        "Takeout/Gmail/ignored.json": [{"canary": "IGNORED_FOLDER_CANARY"}],
        "Takeout/Photos/photo-info.json": {"canary": "IGNORED_PHOTO_CANARY"},
    })


# ---------------------------------------------------------------- happy path

def test_synthetic_zip_aggregates_all_sources(tmp_path):
    records = takeout_records(OWNER, _full_zip(tmp_path))
    by_source = {r.source: r for r in records}
    assert set(by_source) == {"youtube:interests", "takeout:chrome", "takeout:gemini-apps"}
    yt = by_source["youtube:interests"]
    assert yt.id == f"yt-day-{DAY}" and yt.at == f"{DAY}T00:00:00"
    assert "3 videos watched" in yt.text  # 2 watched + 1 search, one daily record
    chrome = by_source["takeout:chrome"]
    assert chrome.text == "Browser visits to docs.python.org: 1\nBrowser visits to stackoverflow.com: 1"
    gemini = by_source["takeout:gemini-apps"]
    assert "Summarise my meeting notes" in gemini.text
    blob = _blob(records)
    for canary in ("RAW_TITLE_991", "SECRETVID", "watch?v=", "RAW_RESPONSE_993",
                   "IGNORED_FOLDER_CANARY", "IGNORED_PHOTO_CANARY", "09:15:33",
                   "13:47:29", "postgres tutorial"):
        assert canary not in blob


def test_extracted_folder_fixture(tmp_path):
    records = takeout_records("karim", FIXTURE_DIR)
    blob = _blob(records)
    assert {r.source for r in records} == {"youtube:interests", "takeout:chrome", "takeout:gemini-apps"}
    assert "1 videos watched" in blob  # the faith video in the fixture is held
    assert "docs.python.org: 1" in blob and "chase.com" not in blob
    assert "Summarise my meeting notes" in blob
    for canary in ("RAW_TITLE_991", "RAW_RESPONSE_993", "IGNORED_FOLDER_CANARY", "Quran"):
        assert canary not in blob


def test_owner_string_and_owner_object_both_accepted(tmp_path):
    path = _full_zip(tmp_path)
    assert [r.id for r in takeout_records("karim", path)] == \
           [r.id for r in takeout_records(OWNER, path)]


# ---------------------------------------------------------------- missing parts

@pytest.mark.parametrize("members", [
    {},
    {"Takeout/Chrome/BrowserHistory.json": {"Browser History": [_chrome("https://example.com/a")]}},
    {"Takeout/YouTube and YouTube Music/history/search-history.json": [_yt_search("cooking recipes")]},
])
def test_missing_parts_are_ok(tmp_path, members):
    records = takeout_records(OWNER, _zip(tmp_path / "partial.zip", members))
    if not members:
        assert records == []
    else:
        assert len(records) == 1


def test_empty_folder_is_ok(tmp_path):
    assert takeout_records(OWNER, tmp_path) == []


# ---------------------------------------------------------------- Rule 9

@pytest.mark.parametrize("title", [
    "Quran Recitation Surah Al-Kahf",       # faith
    "Managing Type 2 Diabetes Daily",       # health
    "National Election Results Breakdown",  # politics
    "LGBTQ Dating and Sexuality Guide",     # sexuality
    "My sister is recovering after surgery",  # family third-party
])
def test_sensitive_watch_topics_held(tmp_path, title):
    path = _zip(tmp_path / "t.zip", {
        "Takeout/YouTube and YouTube Music/history/watch-history.json": [
            _yt_watch(title),
            _yt_watch("Python FastAPI Tutorial", when=f"{DAY}T11:00:00.000Z"),
        ]})
    records = takeout_records(OWNER, path)
    assert len(records) == 1 and "1 videos watched" in records[0].text
    assert title not in _blob(records)


@pytest.mark.parametrize("query", ["cancer clinic near me", "how to vote in the election",
                                   "prayer times ramadan", "gay dating advice"])
def test_sensitive_search_queries_held(tmp_path, query):
    path = _zip(tmp_path / "t.zip", {
        "Takeout/YouTube and YouTube Music/history/search-history.json": [_yt_search(query)]})
    assert takeout_records(OWNER, path) == []


def test_sensitive_channel_and_third_party_title_names_held(tmp_path):
    path = _zip(tmp_path / "t.zip", {
        "Takeout/YouTube and YouTube Music/history/watch-history.json": [
            _yt_watch("Daily Vlog", channel="Cancer Recovery Clinic"),
            _yt_watch("Interview with Sarah Chen about her cancer treatment"),
        ]})
    records = takeout_records(OWNER, path)
    blob = _blob(records)
    assert records == [] and "Sarah Chen" not in blob and "Cancer Recovery Clinic" not in blob


@pytest.mark.parametrize("url,title", [
    ("https://login.chase.com/home", "Bank login"),
    ("https://mail.bankofamerica.com/inbox", "Bank mail"),
    ("https://sub.mayoclinic.org/symptoms", "Symptoms"),
    ("https://sub.pornhub.com/video", "Video"),
    ("https://agency.example.gov/home", "Gov"),
    ("https://example.com/search?q=cancer+symptoms", "Search"),
    ("https://example.com/health", "Lab Results diabetes"),
])
def test_denylisted_and_sensitive_chrome_never_appear(tmp_path, url, title):
    path = _zip(tmp_path / "t.zip", {"Takeout/Chrome/BrowserHistory.json": {"Browser History": [
        _chrome(url, title),
        _chrome("https://docs.python.org/3/", "Python docs", when=f"{DAY}T14:00:00.000Z"),
    ]}})
    records = takeout_records(OWNER, path)
    assert len(records) == 1 and records[0].text == "Browser visits to docs.python.org: 1"
    blob = _blob(records)
    for fragment in ("chase.com", "bankofamerica.com", "mayoclinic.org", "pornhub.com",
                     ".gov", "cancer", title):
        assert fragment not in blob


def test_gemini_sensitive_prompts_held_and_secrets_redacted(tmp_path):
    long_secret = "Summarise this " + ("x" * 600) + " TAIL_CANARY"
    path = _zip(tmp_path / "t.zip", {"Takeout/My Activity/Gemini Apps/MyActivity.json": [
        _gemini("What are the prayer times for Ramadan today"),
        _gemini("Help me dose my insulin for diabetes"),
        _gemini("Draft an election campaign strategy"),
        _gemini("My API key is sk-1234567890abcdefghijklmnop, use it"),
        _gemini(long_secret, when=f"{DAY}T09:00:00.000Z"),
    ]})
    records = takeout_records(OWNER, path)
    assert len(records) == 1
    blob = _blob(records)
    for canary in ("prayer", "insulin", "election", "sk-1234567890", "TAIL_CANARY", "RAW_RESPONSE_993"):
        assert canary not in blob.lower() if canary.islower() else canary not in blob
    assert "[redacted]" in blob and len(records[0].text) < 700


# ---------------------------------------------------------------- zip safety

@pytest.mark.parametrize("evil", [
    "../../Takeout/YouTube and YouTube Music/history/watch-history.json",
    "/abs/Takeout/Chrome/BrowserHistory.json",
    "C:\\evil\\BrowserHistory.json",
    "Takeout\\..\\..\\watch-history.json",
])
def test_path_traversal_entries_refused(tmp_path, evil):
    path = _zip(tmp_path / "evil.zip", {evil: b"[]"})
    with pytest.raises(TakeoutError):
        takeout_records(OWNER, path)
    assert not (tmp_path / "evil").exists()


def test_symlink_entry_refused(tmp_path):
    path = tmp_path / "link.zip"
    info = zipfile.ZipInfo("Takeout/Chrome/BrowserHistory.json")
    info.external_attr = 0o120777 << 16
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(info, b"{}")
    with pytest.raises(TakeoutError):
        takeout_records(OWNER, path)


def test_zip_bomb_refused(tmp_path):
    # ~2 MB of zeros in valid JSON-string form compresses far beyond 100:1.
    payload = json.dumps({"Browser History": "A" * 2_000_000}).encode()
    path = _zip(tmp_path / "bomb.zip", {"Takeout/Chrome/BrowserHistory.json": payload})
    with pytest.raises(TakeoutError):
        takeout_records(OWNER, path)


def test_size_caps_refused(tmp_path, monkeypatch):
    path = _full_zip(tmp_path)
    monkeypatch.setattr(takeout, "MAX_MEMBER_BYTES", 10)
    with pytest.raises(TakeoutError):
        takeout_records(OWNER, path)
    monkeypatch.setattr(takeout, "MAX_MEMBER_BYTES", 64 * 1024 * 1024)
    monkeypatch.setattr(takeout, "MAX_ZIP_BYTES", 10)
    with pytest.raises(TakeoutError):
        takeout_records(OWNER, path)


def test_malformed_and_missing_paths_refused(tmp_path):
    bad = _zip(tmp_path / "bad.zip", {"Takeout/Chrome/BrowserHistory.json": b"{[ not json"})
    with pytest.raises(TakeoutError):
        takeout_records(OWNER, bad)
    with pytest.raises(TakeoutError):
        takeout_records(OWNER, tmp_path / "does-not-exist.zip")
    notzip = tmp_path / "not.zip"
    notzip.write_bytes(b"hello")
    with pytest.raises(TakeoutError):
        takeout_records(OWNER, notzip)


# ---------------------------------------------------------------- since

def test_since_filters_by_owner_local_day(tmp_path):
    # Asia/Dubai = UTC+4: 2026-10-20T20:00Z is already 2026-10-21 in Dubai.
    members = {
        "Takeout/YouTube and YouTube Music/history/watch-history.json": [
            _yt_watch("Python FastAPI Tutorial", when="2026-10-20T19:59:59.000Z"),
            _yt_watch("Blender Render Nodes", when="2026-10-20T20:00:00.000Z", vid="zzz999XYZ09"),
        ],
        "Takeout/Chrome/BrowserHistory.json": {"Browser History": [
            _chrome("https://docs.python.org/3/", when="2026-10-20T19:59:59.000Z"),
            _chrome("https://example.com/a", when="2026-10-20T20:00:00.000Z"),
        ]},
        "Takeout/My Activity/Gemini Apps/MyActivity.json": [
            _gemini("Summarise my notes", when="2026-10-20T19:59:59.000Z"),
            _gemini("Plan my week", when="2026-10-20T20:00:00.000Z"),
        ],
    }
    path = _zip(tmp_path / "t.zip", members)
    all_records = takeout_records(OWNER, path)
    assert {r.at[:10] for r in all_records} == {"2026-10-20", "2026-10-21"}
    since_records = takeout_records(OWNER, path, since=date(2026, 10, 21))
    assert since_records and {r.at[:10] for r in since_records} == {"2026-10-21"}
    assert "1 videos watched" in _blob(since_records)
    assert "example.com: 1" in _blob(since_records) and "Plan my week" in _blob(since_records)
    # String since is accepted too.
    assert takeout_records(OWNER, path, since="2026-10-21") == since_records
