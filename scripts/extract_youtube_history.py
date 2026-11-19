"""Extract YouTube Watch History (Takeout JSON or Local Browser SQLite).

Paths:
1. Takeout: Reads data/sync/watch-history.json if present.
2. Local Browser: Reads Chrome / Edge history SQLite database directly for youtube.com/watch entries.
Outputs: data/sync/youtube_watch_history.json (top 500 titles).
"""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data" / "sync"
TAKEOUT_JSON = DATA_DIR / "watch-history.json"
OUTPUT_JSON = DATA_DIR / "youtube_watch_history.json"


def parse_takeout(path: Path, limit: int = 500) -> list[dict]:
    print(f"[Takeout] Reading from {path}...")
    data = json.loads(path.read_text(encoding="utf-8"))
    results = []
    for item in data:
        title = item.get("title", "")
        if title.startswith("Watched "):
            title = title[8:]
        url = item.get("titleUrl", "")
        time_str = item.get("time", "")
        subtitles = item.get("subtitles") or []
        channel = subtitles[0].get("name", "") if subtitles else ""
        
        results.append({
            "title": title,
            "url": url,
            "channel": channel,
            "watched_at": time_str,
            "source": "google_takeout",
        })
        if len(results) >= limit:
            break
    return results


def find_browser_history_files() -> list[Path]:
    candidates = []
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if not local_app_data:
        return candidates

    # Chrome profiles
    chrome_user_data = Path(local_app_data) / "Google" / "Chrome" / "User Data"
    if chrome_user_data.exists():
        for p in chrome_user_data.glob("*/History"):
            if "Snapshot" not in str(p) and p.is_file():
                candidates.append(p)
        default_hist = chrome_user_data / "Default" / "History"
        if default_hist.is_file() and default_hist not in candidates:
            candidates.append(default_hist)

    # Edge
    edge_hist = Path(local_app_data) / "Microsoft" / "Edge" / "User Data" / "Default" / "History"
    if edge_hist.is_file():
        candidates.append(edge_hist)

    return candidates


def parse_browser_sqlite(history_path: Path, limit: int = 500) -> list[dict]:
    print(f"[Browser] Reading history from: {history_path}")
    results = []
    # Copy file to temp because Chrome/Edge locks SQLite file when open
    with tempfile.NamedTemporaryFile(delete=False, suffix=".sqlite") as tmp:
        tmp_path = Path(tmp.name)

    try:
        shutil.copy2(history_path, tmp_path)
        conn = sqlite3.connect(str(tmp_path))
        cursor = conn.cursor()
        query = """
            SELECT url, title, last_visit_time 
            FROM urls 
            WHERE url LIKE '%youtube.com/watch%' AND title != ''
            ORDER BY last_visit_time DESC 
            LIMIT ?
        """
        cursor.execute(query, (limit,))
        rows = cursor.fetchall()
        conn.close()

        for url, title, last_visit in rows:
            # WebKit/Chrome timestamp is microseconds since 1601-01-01
            try:
                unix_ts = (last_visit / 1_000_000) - 11644473600
                dt = datetime.fromtimestamp(unix_ts, tz=timezone.utc)
                ts_str = dt.isoformat()
            except Exception:
                ts_str = ""

            clean_title = title.replace(" - YouTube", "").strip()
            results.append({
                "title": clean_title,
                "url": url,
                "channel": "",
                "watched_at": ts_str,
                "source": f"local_browser:{history_path.parent.name}",
            })
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass

    return results


def main():
    print("=" * 60)
    print("YouTube Watch History Extractor (Latest 500 Titles)")
    print("=" * 60)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    records = []
    if TAKEOUT_JSON.exists():
        records = parse_takeout(TAKEOUT_JSON, limit=500)
    else:
        print(f"[Info] No Takeout file found at {TAKEOUT_JSON}")
        print("[Info] Scanning local browser history (Chrome / Edge)...")
        history_files = find_browser_history_files()
        
        seen_urls = set()
        for hf in history_files:
            try:
                batch = parse_browser_sqlite(hf, limit=500)
                for r in batch:
                    if r["url"] not in seen_urls:
                        seen_urls.add(r["url"])
                        records.append(r)
            except Exception as e:
                print(f"  Warning: Could not read {hf}: {e}")

        # Sort newest first and limit to 500
        records.sort(key=lambda x: x.get("watched_at", ""), reverse=True)
        records = records[:500]

    print(f"\n[Done] Extracted {len(records)} watched video titles.")
    if records:
        OUTPUT_JSON.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[Saved] Output written to: {OUTPUT_JSON}")
        print("\n--- Sample Latest 5 Watched Titles ---")
        for i, r in enumerate(records[:5], 1):
            print(f"{i}. {r['title']} ({r.get('watched_at')[:10] if r.get('watched_at') else 'N/A'})")
            print(f"   URL: {r['url']}")
    else:
        print("[Notice] No YouTube watch history found yet.")
        print(f"Place your 'watch-history.json' from Google Takeout in {TAKEOUT_JSON} to load it.")


if __name__ == "__main__":
    main()
