import os
import sqlite3
from urllib.parse import quote

import pytest

from app.actions import ActionStore
from app.migrate_supabase import import_snapshot, inventory


def test_import_is_backed_up_idempotent_and_conflicts_fail(tmp_path):
    source = tmp_path / 'source.sqlite3'
    with sqlite3.connect(source) as src:
        src.execute('CREATE TABLE sessions (token_hash TEXT PRIMARY KEY, owner TEXT)')
        src.execute('INSERT INTO sessions VALUES (?,?)',('hash-one','owner-one'))
    target_file = tmp_path / 'target.sqlite3'
    target = ActionStore(target_file)
    target_url = str(target_file)
    if target.db.dialect == 'postgres':
        base = os.environ['TEST_DATABASE_URL']
        target_url = base + ('&' if '?' in base else '?') + 'options=' + quote(target.db.conn.info.get_parameters()['options'])
    result = import_snapshot(source,target_url,tmp_path/'backup.sqlite3')
    assert result['sessions']['inserted'] == 1
    assert inventory(tmp_path/'backup.sqlite3') == {'sessions':1}
    assert import_snapshot(source,target_url,tmp_path/'backup2.sqlite3')['sessions']['already_identical'] == 1
    with sqlite3.connect(source) as src:
        src.execute("UPDATE sessions SET owner='different-owner'")
    with pytest.raises(ValueError,match='Conflicting record'):
        import_snapshot(source,target_url,tmp_path/'backup3.sqlite3')
    assert target.db.execute('SELECT owner FROM sessions').fetchone()[0] == 'owner-one'
    target.db.close()


def test_unmapped_tables_are_not_silently_skipped(tmp_path):
    source = tmp_path/'unknown.sqlite3'
    with sqlite3.connect(source) as src:
        src.execute('CREATE TABLE unknown_data (id TEXT)')
    with pytest.raises(ValueError,match='Unmapped source tables'):
        inventory(source)
