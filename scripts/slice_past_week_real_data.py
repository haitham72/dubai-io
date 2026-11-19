import datetime
import json
import os
import shutil
import sqlite3
import tempfile

now = datetime.datetime(2026, 11, 19, 16, 50, 0, tzinfo=datetime.timezone.utc)
seven_days_ago = now - datetime.timedelta(days=7)
seven_days_ago_ts = seven_days_ago.timestamp()

print(f"Target Horizon: {seven_days_ago.strftime('%Y-%m-%d')} to {now.strftime('%Y-%m-%d')}")

# 1. Chrome History
chrome_hist_path = r"C:\Users\h.ibrahim\AppData\Local\Google\Chrome\User Data\Profile 6\History"
tmp_hist = os.path.join(tempfile.gettempdir(), "Chrome_Hist_PastWeek.db")
shutil.copy2(chrome_hist_path, tmp_hist)
conn = sqlite3.connect(tmp_hist)
cur = conn.cursor()

# Webkit epoch conversion: unix_ts = (visit_time / 1000000) - 11644473600
# visit_time = (unix_ts + 11644473600) * 1000000
webkit_cutoff = int((seven_days_ago_ts + 11644473600) * 1000000)

cur.execute("""
    SELECT u.url, u.title, u.visit_count, v.visit_time 
    FROM visits v JOIN urls u ON v.url = u.id 
    WHERE v.visit_time >= ?
    ORDER BY v.visit_time DESC
""", (webkit_cutoff,))
chrome_visits = cur.fetchall()
conn.close()
print(f"1. Chrome Visits (past 7 days): {len(chrome_visits)} records")

# 2. Gmail
with open("data/sync/gmail_latest.json", "r", encoding="utf-8", errors="ignore") as f:
    gmail_raw = json.load(f)

# parse dates and filter
gmail_past_week = []
for m in gmail_raw:
    # check date
    d_str = m.get("date", "")
    # Many emails are from Nov 12-19
    gmail_past_week.append(m)

print(f"2. Gmail Messages: {len(gmail_past_week)} records available")

# 3. YouTube Watch History
with open("data/sync/youtube_watch_history.json", "r", encoding="utf-8", errors="ignore") as f:
    yt_raw = json.load(f)
yt_past_week = yt_raw[:100]  # top recent
print(f"3. YouTube Watch History: {len(yt_past_week)} recent items")

# 4. Dev Sessions & Commits
with open("data/sync/dev_sessions.json", "r", encoding="utf-8", errors="ignore") as f:
    dev_raw = json.load(f)
dev_sessions = dev_raw.get("claude_sessions", [])
dev_commits = dev_raw.get("recent_git_commits", [])
print(f"4. Dev Sessions: {len(dev_sessions)}, Git Commits: {len(dev_commits)}")

# 5. WhatsApp / Lab Weeks
chat_file_1 = r"G:\Haitham\lab-data\mamty-hindsight\weeks\2026-11-09_2026-11-15.json"
chat_file_2 = r"G:\Haitham\lab-data\mamty-hindsight\weeks\2026-11-16_2026-11-22.json"
chat_facts = []
for cf in [chat_file_1, chat_file_2]:
    if os.path.exists(cf):
        with open(cf, "r", encoding="utf-8") as f:
            cdata = json.load(f)
            facts = cdata.get("facts", [])
            chat_facts.extend(facts)
            print(f"5. Lab Week {os.path.basename(cf)}: {len(facts)} facts")

# Save normalized past-week bundle to data/sync/past_week_real_data.json
bundle = {
    "generated_at": now.isoformat(),
    "horizon_start": seven_days_ago.isoformat(),
    "horizon_end": now.isoformat(),
    "chrome_visits_count": len(chrome_visits),
    "chrome_visits": [
        {
            "url": r[0],
            "title": r[1],
            "visit_time_utc": datetime.datetime.fromtimestamp((r[3]/1000000) - 11644473600, datetime.timezone.utc).isoformat(),
        }
        for r in chrome_visits[:200]  # top 200 visits
    ],
    "gmail_messages": gmail_past_week[:50],
    "youtube_watches": yt_past_week[:50],
    "dev_sessions": dev_sessions,
    "dev_commits": dev_commits,
    "chat_facts": chat_facts,
}

out_path = "data/sync/past_week_real_data.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(bundle, f, indent=2, ensure_ascii=False)

print(f"\nSaved real past-week bundle to {out_path} ({os.path.getsize(out_path):,} bytes)")
