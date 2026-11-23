import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from messenger_agents.contacts import Contact  # noqa: E402


@pytest.fixture
def contacts() -> list[Contact]:
    return [Contact(**c) for c in json.loads((ROOT / "eval" / "contacts.json").read_text(encoding="utf-8"))]
