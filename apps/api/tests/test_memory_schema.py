from app.db import connect
from app.memory.schema import ensure_memory_schema
from app.memory.store import MemoryStore


def test_memory_schema_idempotent(tmp_path):
    db = connect(tmp_path / "mem.db")
    ensure_memory_schema(db)
    ensure_memory_schema(db)
    rows = db.execute("SELECT path FROM mem_ontology_paths WHERE path=?", ("lifestyle/sports/gym",)).fetchall()
    assert rows and rows[0][0] == "lifestyle/sports/gym"


def test_memory_forget_removes_from_search(tmp_path):
    db = connect(tmp_path / "mem2.db")
    mem = MemoryStore(db)
    added = mem.add_event("owner-a", kind="fact", text="I live in Dubai Marina", provenance="user_supplied", ontology_path="household/home/area")
    assert mem.search("owner-a", "Marina")
    mem.forget("owner-a", added["id"])
    assert mem.search("owner-a", "Marina") == []
    assert mem.timeline("owner-a") == []


def test_memory_owner_isolation(tmp_path):
    db = connect(tmp_path / "mem3.db")
    mem = MemoryStore(db)
    mem.add_event("owner-a", kind="fact", text="secret A", provenance="user_supplied")
    assert mem.search("owner-b", "secret") == []
