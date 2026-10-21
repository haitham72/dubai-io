from types import SimpleNamespace
from fastapi.testclient import TestClient
import pytest
from app import actions, main
from app.actions import ActionEngine, ActionStore


@pytest.fixture
def clients(tmp_path, monkeypatch):
    store=ActionStore(tmp_path/'sessions.sqlite3')
    monkeypatch.setattr(actions,'_engine',ActionEngine(store))
    facts={}
    def add(owner,key,value,source):
        row={'key':key,'value':value,'provenance':'user_supplied','source':source}
        facts.setdefault(owner,{})[key]=row
        return row
    def forget(owner,key):
        return int(facts.get(owner,{}).pop(key,None) is not None)
    monkeypatch.setattr(main.luna,'facts',SimpleNamespace(current=lambda owner:list(facts.get(owner,{}).values()),add=add,forget=forget))
    yield TestClient(main.app),TestClient(main.app)
    store.db.close()


def test_memory_is_scoped_to_session_and_explicit_edits(clients):
    a,b=clients
    assert a.get('/api/session/memory').status_code==401
    a.get('/api/session');b.get('/api/session')
    result=a.put('/api/session/memory/area',json={'value':'Business Bay'})
    assert result.status_code==200
    assert result.json()['fact']['provenance']=='user_supplied'
    assert b.get('/api/session/memory').json()=={'told':[]}
    assert a.get('/api/session/memory').json()['told'][0]['value']=='Business Bay'
    assert a.put('/api/session/memory/unregistered',json={'value':'bad'}).status_code==422
    assert a.put('/api/session/memory/area',json={'value':' '}).status_code==422
    assert a.delete('/api/session/memory/area').json()=={'forgotten':1}
    assert a.get('/api/session/memory').json()=={'told':[]}


def test_luna_uses_cookie_owner_instead_of_supplied_user_id(clients,monkeypatch):
    a,b=clients;first=a.get('/api/session').json()['user_id'];second=b.get('/api/session').json()['user_id'];calls=[]
    monkeypatch.setattr(main.settings,'openai_api_key','offline-test-key')
    monkeypatch.setattr(main.luna,'turn',lambda thread,user,text:calls.append((thread,user,text)) or {'intent':'greeting'})
    for client in (a,b):
        assert client.post('/api/luna/turn',json={'text':'hi','thread_id':'shared','user_id':'someone-else'}).status_code==200
    assert [c[1] for c in calls]==[first,second]


def test_legacy_memory_cannot_read_or_delete_another_session(clients):
    a, b = clients
    assert a.get('/api/memory/demo-user').status_code == 401
    owner = a.get('/api/session').json()['user_id']
    b.get('/api/session')
    a.put('/api/session/memory/area', json={'value': 'JLT'})
    assert b.get(f'/api/memory/{owner}').status_code == 404
    assert b.delete(f'/api/memory/{owner}/area').status_code == 404
    assert a.get(f'/api/memory/{owner}').json()['told'][0]['value'] == 'JLT'
    assert a.delete(f'/api/memory/{owner}/area').json() == {'forgotten': 1}


def test_luna_rejects_client_supplied_identity_without_session(clients, monkeypatch):
    a, _ = clients
    monkeypatch.setattr(main.settings, 'openai_api_key', 'offline-test-key')
    monkeypatch.setattr(main.luna, 'turn', lambda *args: pytest.fail('unauthenticated turn executed'))
    assert a.post('/api/luna/turn', json={'text': 'hi', 'user_id': 'victim'}).status_code == 401
