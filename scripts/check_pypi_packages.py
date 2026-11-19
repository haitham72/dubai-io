import json
import urllib.request

def check_pkg(name):
    url = f"https://pypi.org/pypi/{name}/json"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            info = data.get("info", {})
            print(f"[FOUND] {name}: version={info.get('version')} | summary={info.get('summary')}")
    except Exception as e:
        print(f"[NOT FOUND / ERROR] {name}: {e}")

pkgs = [
    "mem0ai",
    "hindsight-client",
    "hindsight-api-slim",
    "hindsight-api",
    "hindsight",
    "honcho-ai",
    "mnemosyne",
    "mnemosyne-ai",
    "graphiti-core",
    "zep-python",
    "letta",
]

for p in pkgs:
    check_pkg(p)
