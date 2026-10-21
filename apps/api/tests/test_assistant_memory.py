from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import json
import os
import sqlite3

import pytest
from langgraph.checkpoint.sqlite import SqliteSaver

from app import actions
from app.actions import ActionEngine, ActionStore
from app.luna import graph as luna
from app.luna.schema import FocusContext, Understanding
from app.user_profile import ProfileStore


@pytest.fixture
def memory(tmp_path,monkeypatch):
    store = ActionStore(tmp_path / "memory.sqlite3")
    monkeypatch.setattr(actions,"_engine",ActionEngine(store))
    if store.db.dialect == "postgres":
        from app.db import postgres_connect
        from psycopg.rows import dict_row
        from langgraph.checkpoint.postgres import PostgresSaver
        saver = PostgresSaver(postgres_connect(os.environ["TEST_DATABASE_URL"],options=store.db.conn.info.get_parameters()["options"],autocommit=True,prepare_threshold=0,row_factory=dict_row))
        saver.setup()
    else:
        saver = SqliteSaver(sqlite3.connect(tmp_path / "checkpoints.sqlite3",check_same_thread=False))
    monkeypatch.setattr(luna,"checkpointer",lambda:saver)
    monkeypatch.setattr(luna,"graph",luna.LazyGraph())
    monkeypatch.setattr(luna,"facts",ProfileStore(lambda:store))
    prompts = []
    def parse(**kwargs):
        prompts.append(kwargs["input"])
        return SimpleNamespace(output_parsed=Understanding.model_validate({
            "intent":"greeting","confidence":1,"item":None,"where_lost":None,"service":None,"category":None,
            "subcategory":None,"terminal":None,"stated_facts":[],"reply":"Hello.","clarify":None}))
    monkeypatch.setattr(luna,"client",lambda:SimpleNamespace(responses=SimpleNamespace(parse=parse)))
    yield saver,prompts
    saver.conn.close()
    store.db.close()


def test_forgetting_deletes_all_old_owner_checkpoints_but_preserves_other_user(memory):
    saver,prompts = memory
    luna.facts.add("alice","area","JLT","I live in JLT")
    luna.turn("one","alice","I live in JLT")
    luna.turn("two","alice","Hello again")
    luna.turn("one","bob","Keep my own conversation")
    assert luna.forget_fact("alice","area") == 1
    rows = list(saver.list(None))
    assert rows and all(row.checkpoint.get("channel_values",{}).get("user_id") != "alice" for row in rows)
    luna.turn("one","alice","Where am I staying?")
    assert "JLT" not in prompts[-1] and "I live in" not in prompts[-1]


def test_selected_context_is_bounded_and_not_checkpointed_or_reused(memory):
    saver,prompts = memory
    focus = FocusContext(entity_id="g:place",entity_name="Museum of the Future",source="google",
        card="facts",fragment="Tickets reportedly sell out fast",selected_at=datetime.now(timezone.utc))
    luna.turn("one","alice","Are tickets available?",focus)
    assert "Museum of the Future" in prompts[-1] and "untrusted" in prompts[-1]
    assert "Tickets reportedly" not in json.dumps([r.checkpoint for r in saver.list(None)])
    luna.turn("one","alice","Hi again")
    assert "Museum of the Future" not in prompts[-1]
    stale = focus.model_copy(update={"selected_at":datetime.now(timezone.utc)-timedelta(hours=1)})
    luna.turn("one","alice","Hi",stale)
    assert "Museum of the Future" not in prompts[-1]
    assert luna.facts.current("alice") == []


def test_recent_working_memory_is_bounded():
    assert len(luna.recent_history([{"role":"user","text":"old"}]*24,[{"role":"user","text":"new"}]*2)) == 24
