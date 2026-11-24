"""One command to run the agents service locally (macOS, Linux, Windows): `npm run agents` from the repo root.

Creates agents/.venv on first run, installs requirements when they change, then starts the service on :8787.
Redis is optional: without it the service keeps memory in-process.
"""
import hashlib
import os
import subprocess
import sys
import venv
from pathlib import Path

HERE = Path(__file__).resolve().parent
VENV = HERE / ".venv"
BIN = VENV / ("Scripts" if os.name == "nt" else "bin")
PY = BIN / ("python.exe" if os.name == "nt" else "python")


def main() -> None:
    # A CA-bundle variable left pointing at a deleted venv makes pip and httpx fail; fall back to the default bundle.
    for var in ("SSL_CERT_FILE", "REQUESTS_CA_BUNDLE"):
        if os.environ.get(var) and not Path(os.environ[var]).is_file():
            print(f"agents: ignoring {var} (file not found)")
            del os.environ[var]
    if not PY.exists():
        print("agents: creating .venv …")
        venv.create(VENV, with_pip=True)
    req = (HERE / "requirements-dev.txt").read_bytes() + (HERE / "requirements.txt").read_bytes()
    stamp = VENV / ".requirements.sha"
    digest = hashlib.sha256(req).hexdigest()
    if not stamp.exists() or stamp.read_text() != digest:
        print("agents: installing requirements …")
        subprocess.check_call([str(PY), "-m", "pip", "install", "-q", "-r", str(HERE / "requirements-dev.txt")])
        stamp.write_text(digest)
    os.chdir(HERE)
    if sys.argv[1:2] == ["test"]:
        sys.exit(subprocess.call([str(PY), "-m", "pytest", "-q", *sys.argv[2:]]))
    if sys.argv[1:2] == ["eval"]:
        sys.exit(subprocess.call([str(PY), "-m", "eval.run_eval", *sys.argv[2:]]))
    # An open voice WebSocket would otherwise block --reload forever (old code keeps serving): cap the shutdown wait.
    args = sys.argv[1:] or ["--port", "8787", "--reload", "--timeout-graceful-shutdown", "2"]
    os.execv(str(PY), [str(PY), "-m", "uvicorn", "messenger_agents.app:app", *args])


if __name__ == "__main__":
    main()
