import json
from collections import Counter

with open('data/sync/gaming_history_extracted.json', 'r', encoding='utf-8') as f:
    items = json.load(f)

print(f"Total items: {len(items)}")
# Deduplicate by title
seen = set()
unique_items = []
for item in items:
    t = item['title'].strip()
    if t and t not in seen:
        seen.add(t)
        unique_items.append(item)

print(f"Unique titles: {len(unique_items)}")
for i, item in enumerate(unique_items):
    print(f"{i+1:2d}. [{item['time']}] ({item['matched']}) {item['title']} -> {item['url'][:80]}")
