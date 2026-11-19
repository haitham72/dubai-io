import urllib.request
import json

def check_pypi(pkg):
    try:
        url = f"https://pypi.org/pypi/{pkg}/json"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read())
            summary = data["info"].get("summary") or "No summary"
            version = data["info"].get("version")
            print(f"PyPI [{pkg}]: {summary[:70]} (v{version})")
    except Exception as e:
        print(f"PyPI [{pkg}]: Not found ({e})")

for p in ["mem0ai", "honcho-ai", "honcho", "hindsight", "hindsight-ai", "mnemosyne", "graphiti-core"]:
    check_pypi(p)
