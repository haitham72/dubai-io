import os
import subprocess
import sys
import urllib.request
import json

endpoints = [
    ("LM Studio (1234)", "http://localhost:1234/v1/models"),
    ("Ollama (11434)", "http://localhost:11434/api/tags"),
]
for name, url in endpoints:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "test"})
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            data = resp.read().decode("utf-8")
            print(f"{name}: ONLINE -> {data[:120]}")
    except Exception as e:
        print(f"{name}: OFFLINE ({e})")
