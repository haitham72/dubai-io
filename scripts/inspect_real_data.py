import datetime
import json
import os
import sqlite3
import sys

print("=== 1. CHROME BROWSER HISTORY (Profile 6) ===")
chrome_hist_path = r"C:\Users\h.ibrahim\AppData\Local\Google\Chrome\User Data\Profile 6\History"
if os.path.exists(chrome_hist_path):
    print(f"Found Chrome History: {chrome_hist_path} (size: {os.path.getsize(chrome_hist_path):,} bytes)")
    import shutil, tempfile
    # Chrome locks the DB if open, so copy to temp
    tmp_dir = tempfile.gettempdir()
    tmp_hist = os.path.join(tmp_dir, "Chrome_History_Profile6_Copy.db")
    try:
        shutil.copy2(chrome_hist_path, tmp_hist)
        conn = sqlite3.connect(tmp_hist)
        cur = conn.cursor()
        # Chrome timestamps are microseconds since Jan 1, 1601 UTC
        # WebKit epoch to Unix epoch: (timestamp / 1000000) - 11644473600
        cur.execute("SELECT count(*) FROM urls")
        total_urls = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM visits")
        total_visits = cur.fetchone()[0]
        print(f"Total URLs in DB: {total_urls}, Total Visits: {total_visits}")
        
        # Get past 7 days:
        # Nov 19, 2026 is today.
        cur.execute("""
            SELECT u.url, u.title, u.visit_count, v.visit_time 
            FROM visits v JOIN urls u ON v.url = u.id 
            ORDER BY v.visit_time DESC LIMIT 10
        """)
        recent_visits = cur.fetchall()
        print(f"Most recent 10 visits:")
        for r in recent_visits:
            # convert webkit timestamp
            try:
                unix_ts = (r[3] / 1000000) - 11644473600
                dt = datetime.datetime.fromtimestamp(unix_ts, datetime.timezone.utc)
                print(f"  [{dt.strftime('%Y-%m-%d %H:%M')}] {r[1][:60]} -> {r[0][:80]}")
            except Exception as e:
                print(f"  [raw {r[3]}] {r[1][:60]}")
        conn.close()
    except Exception as e:
        print(f"Error reading Chrome History: {e}")
else:
    print(f"Chrome History not found at {chrome_hist_path}")

print("\n=== 2. GMAIL LATEST ===")
gmail_path = "data/sync/gmail_latest.json"
if os.path.exists(gmail_path):
    with open(gmail_path, "r", encoding="utf-8", errors="ignore") as f:
        data = json.load(f)
    print(f"Gmail records count: {len(data) if isinstance(data, list) else 'dict'}")
    if isinstance(data, list) and len(data) > 0:
        print("Sample recent email headers:")
        for m in data[:5]:
            print(f"  [{m.get('date', 'no date')[:25]}] From: {str(m.get('from'))[:40]} | Subj: {str(m.get('subject'))[:60]}")
else:
    print("gmail_latest.json not found")

print("\n=== 3. YOUTUBE WATCH HISTORY ===")
yt_path = "data/sync/youtube_watch_history.json"
if os.path.exists(yt_path):
    with open(yt_path, "r", encoding="utf-8", errors="ignore") as f:
        yt_data = json.load(f)
    print(f"YouTube records count: {len(yt_data) if isinstance(yt_data, list) else 'dict'}")
    if isinstance(yt_data, list) and len(yt_data) > 0:
        print("Sample recent YouTube watches:")
        for y in yt_data[:5]:
            print(f"  [{y.get('time', 'no time')[:20]}] {str(y.get('title'))[:60]} ({str(y.get('channel'))[:30]})")
else:
    print("youtube_watch_history.json not found")

print("\n=== 4. DEV SESSIONS & GIT COMMITS ===")
dev_path = "data/sync/dev_sessions.json"
if os.path.exists(dev_path):
    with open(dev_path, "r", encoding="utf-8", errors="ignore") as f:
        dev_data = json.load(f)
    print(f"Dev sessions count: {len(dev_data) if isinstance(dev_data, list) else 'dict'}")
    if isinstance(dev_data, list) and len(dev_data) > 0:
        for d in dev_data[:5]:
            print(f"  [{d.get('timestamp', '')[:20]}] Project: {d.get('project')} | {d.get('narrative')[:70]}")
else:
    print("dev_sessions.json not found")

print("\n=== 5. CHAT / LAB DATA ===")
lab_dirs = [r"G:\Haitham\lab-data\mamty-hindsight", r"G:\Haitham\lab-data\comparison", "data/chat"]
for ld in lab_dirs:
    if os.path.exists(ld):
        print(f"Found chat/lab dir: {ld}")
        items = os.listdir(ld)[:10]
        print(f"  Items: {items}")
    else:
        print(f"Not found: {ld}")
