import json

with open("data/sync/two_tower_results.json", encoding="utf-8") as f:
    res = json.load(f)

print(f"Total slots: {len(res)}")
for r in res:
    hits = r.get("results", [])
    top = hits[0]["title"] if hits else "None"
    print(f"Slot {r['slot']}: [{r['category']}] {r['topic']} -> {top}")
