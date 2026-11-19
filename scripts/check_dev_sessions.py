import json

with open("data/sync/dev_sessions.json", "r", encoding="utf-8") as f:
    dev = json.load(f)

print(f"dev_sessions.json keys: {list(dev.keys()) if isinstance(dev, dict) else type(dev)}")
if isinstance(dev, dict):
    for k in dev:
        val = dev[k]
        print(f"  key '{k}': {type(val)} (len={len(val) if hasattr(val, '__len__') else 'N/A'})")
        if isinstance(val, list) and len(val) > 0:
            print(f"    sample item: {val[0]}")
