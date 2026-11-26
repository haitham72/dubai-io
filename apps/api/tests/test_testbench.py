from pathlib import Path
import re
import subprocess
import sys


BENCH = Path(__file__).resolve().parents[2] / "testbench"


def test_testbench_requires_explicit_dev_opt_in():
    # Each import builds its own route table without reloading other tests' app.
    code = """
import os
from fastapi.testclient import TestClient

flag = __import__("sys").argv[1]
os.environ.pop("DEV_TESTBENCH", None)
if flag:
    os.environ["DEV_TESTBENCH"] = flag

from app.main import app
client = TestClient(app)
page = client.get("/testbench", follow_redirects=True)
asset = client.get("/testbench/testbench.js")
expected = 200 if flag == "1" else 404
assert page.status_code == asset.status_code == expected
if expected == 200:
    assert "Dubai IO Test Bench" in page.text
    assert "testbench.js" in page.text
"""
    for flag in ("", "0", "1"):
        subprocess.run([sys.executable, "-c", code, flag], check=True)


def test_testbench_only_builds_api_urls_on_local_dev_ports():
    source = (BENCH / "testbench.js").read_text(encoding="utf-8")
    assert not re.search(r"""(?i)(?:https?|wss?)://|["'`]//[^"'`]""", source)
    port_map = re.search(r"const ports = Object.freeze\(\{([^}]+)\}\);", source)
    assert port_map
    assert set(re.findall(r"\b\d{4}\b", port_map[1])) == {"8000", "8060", "8070", "8040"}
    assert "base.hostname = window.location.hostname" in source
    assert "base.port = ports[service]" in source
    assert "target.origin !== base.origin" in source
    assert source.count("fetch(") == 1
    assert 'fetch(url, { method, headers, body, credentials: "include", redirect: "error" })' in source
