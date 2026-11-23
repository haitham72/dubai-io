"""Access the external synthetic Karim corpus and its ledger IDs."""
from __future__ import annotations

from functools import cache
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from temporal_memory.models import Record


CHATS = {"best": "wab", "work": "wag", "family": "waf"}


def gold_dir() -> Path:
    location = os.getenv("TM_E2E_GOLD_DIR")
    if not location:
        raise RuntimeError("TM_E2E_GOLD_DIR must point to the synthetic gold directory")
    return Path(location)


@cache
def _load_ledger(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_gold() -> dict:
    return _load_ledger(gold_dir() / "ledger.json")


def import_gold(stack, owner: str) -> list[Record]:
    sources = gold_dir() / "sources"
    imports = [
        ("whatsapp", f"whatsapp_{chat}.txt", ["--source-name", chat]) for chat in CHATS
    ] + [("gmail", "gmail.jsonl", []), ("notes", "notes.md", [])]

    imported = 0
    for kind, filename, flags in imports:
        command = [sys.executable, "-m", "temporal_memory.ingest.cli", "--dsn", stack.db.dsn,
                   "import", kind, str(sources / filename), "--owner", owner, "--no-split", *flags]
        result = subprocess.run(command, capture_output=True, encoding="utf-8", timeout=45)
        assert result.returncode == 0, result.stderr
        summary = json.loads(result.stdout)
        assert summary["jobs_enqueued"] == 0
        assert summary["imported"] > 0
        imported += summary["imported"]

    records = stack.rows(
        "SELECT id, owner, source, at, author, text, generation FROM records WHERE owner = %s ORDER BY at, id",
        (owner,),
    )
    assert imported == len(records)
    return [Record(**record) for record in records]


def ledger_record_id(record_id: str) -> str:
    parts = record_id.split("-")
    if len(parts) == 3 and parts[0] == "wa" and parts[1] in CHATS:
        # The importer numbers messages from zero. The ledger uses source line numbers.
        return f"{CHATS[parts[1]]}-{int(parts[2]) + 1:04d}"
    return record_id


def subject_path(subject: dict | None) -> str:
    if subject is None:
        return "general/notes"
    slug = re.sub(r"[^a-z0-9]+", "-", subject["name"].casefold()).strip("-")
    return f"{subject['kind']}/{slug}"
