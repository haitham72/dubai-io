import urllib.request

endpoints = [
    ("LM Studio (1234)", "http://localhost:1234/v1/models"),
    ("Ollama (11434)", "http://localhost:11434/api/tags"),
    ("FastAPI (8000)", "http://localhost:8000/docs"),
    ("FastAPI (8008)", "http://localhost:8008/docs"),
]

for name, url in endpoints:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "test"})
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            print(f"[ONLINE] {name}: {resp.status}")
    except Exception as e:
        print(f"[OFFLINE] {name}: {e}")
