import json
import os

data_path = "data/sync/past_week_real_data.json"
with open(data_path, "r", encoding="utf-8") as f:
    bundle = json.load(f)

print(f"Horizon: {bundle['horizon_start']} to {bundle['horizon_end']}")
print(f"Total Chrome visits: {len(bundle['chrome_visits'])}")
print(f"Total Gmail messages: {len(bundle['gmail_messages'])}")
print(f"Total YouTube watches: {len(bundle['youtube_watches'])}")
print(f"Total Dev sessions: {len(bundle['dev_sessions'])}")
print(f"Total Dev commits: {len(bundle['dev_commits'])}")
print(f"Total Chat facts: {len(bundle['chat_facts'])}")

total = (
    len(bundle['chrome_visits']) +
    len(bundle['gmail_messages']) +
    len(bundle['youtube_watches']) +
    len(bundle['dev_sessions']) +
    len(bundle['dev_commits']) +
    len(bundle['chat_facts'])
)
print(f"Total items: {total}")
