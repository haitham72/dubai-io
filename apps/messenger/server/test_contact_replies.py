"""Contact replies: fake OpenAI only; no network or paid requests."""
import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
import server.server as srv

client = TestClient(srv.app)
BASE = {"chatId": "arif", "contactName": "Arif Khan", "isGroup": False,
        "history": [{"fromMe": False, "text": "Bring snacks"}, {"fromMe": True, "text": "Saturday?"}]}


def fake_client(monkeypatch, content='{"text":"Absolutely, sunset at Kite Beach 😎"}', failure=False):
    calls = []
    class FakeOpenAI:
        def __init__(self, **kwargs):
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def create(self, **kwargs):
            calls.append(kwargs)
            if failure: raise RuntimeError('private provider details')
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])
    monkeypatch.setenv('OPENAI_API_KEY', 'fake-test-key')
    monkeypatch.setattr('openai.OpenAI', FakeOpenAI)
    return calls


def test_reply_model_history_and_persona(monkeypatch):
    calls = fake_client(monkeypatch)
    monkeypatch.delenv('OPENAI_REPLY_MODEL', raising=False)
    history = [{"fromMe": i % 2 == 1, "text": str(i)} for i in range(30)]
    r = client.post('/api/reply', json={**BASE, 'history': history})
    assert r.status_code == 200
    assert r.json()['text'].startswith('Absolutely') and 'sender' not in r.json()
    call = calls[0]
    assert call['model'] == 'gpt-4o-mini'
    assert call['max_tokens'] == 120 and call['temperature'] == 0.9
    schema = call['response_format']['json_schema']
    assert call['response_format']['type'] == 'json_schema' and schema['strict']
    assert schema['schema']['required'] == ['text']
    messages = call['messages']
    assert len(messages) == 21
    assert messages[1] == {'role': 'assistant', 'content': '10'}
    assert messages[-1] == {'role': 'user', 'content': '29'}
    assert 'Arif Khan' in messages[0]['content'] and 'Kite Beach' in messages[0]['content']
    assert 'Arabic in, Arabic out' in messages[0]['content']
    assert 'never use markdown' in messages[0]['content']
    assert 'English for English input' in messages[0]['content']


@pytest.mark.parametrize('chat_id', list(srv.REPLY_PERSONAS))
def test_distinct_system_prompt_per_chat(monkeypatch, chat_id):
    group = chat_id in srv.REPLY_MEMBERS
    sender = srv.REPLY_MEMBERS[chat_id][0] if group else None
    calls = fake_client(monkeypatch, json.dumps({'text': 'Sounds good', **({'sender': sender} if group else {})}))
    r = client.post('/api/reply', json={**BASE, 'chatId': chat_id, 'isGroup': group})
    assert r.status_code == 200
    assert srv.REPLY_PERSONAS[chat_id] in calls[0]['messages'][0]['content']
    assert len(set(srv.REPLY_PERSONAS.values())) == len(srv.REPLY_PERSONAS)
    if group: assert r.json()['sender'] == sender


def test_group_sender_and_single_prefix(monkeypatch):
    calls = fake_client(monkeypatch, '{"text":"Mom: Dinner is ready 🍲", "sender":"Mom"}')
    r = client.post('/api/reply', json={**BASE, 'chatId': 'family', 'contactName': 'Family', 'isGroup': True})
    assert r.json() == {'text': 'Dinner is ready 🍲', 'sender': 'Mom'}
    assert 'Dad' in calls[0]['messages'][0]['content'] and 'Noor' in calls[0]['messages'][0]['content']
    schema = calls[0]['response_format']['json_schema']['schema']
    assert schema['properties']['sender']['enum'] == ['Mom', 'Dad', 'Noor']
    assert schema['required'] == ['text', 'sender']


def test_unknown_persona_and_model_override(monkeypatch):
    calls = fake_client(monkeypatch, '{"text":"Jules: Sure"}')
    monkeypatch.setenv('OPENAI_REPLY_MODEL', 'configured-reply-model')
    r = client.post('/api/reply', json={**BASE, 'chatId': 'new-person', 'contactName': 'Jules'})
    assert r.json() == {'text': 'Sure'}
    assert calls[0]['model'] == 'configured-reply-model'
    assert 'Jules, a friendly contact' in calls[0]['messages'][0]['content']


def test_unknown_group_uses_history_names(monkeypatch):
    calls = fake_client(monkeypatch, '{"text":"On my way", "sender":"Samira"}')
    r = client.post('/api/reply', json={**BASE, 'chatId': 'new-group', 'isGroup': True,
        'history': [{'fromMe': False, 'text': 'Samira: Hello'}, BASE['history'][-1]]})
    assert r.json() == {'text': 'On my way', 'sender': 'Samira'}
    assert 'Samira' in calls[0]['messages'][0]['content']


def test_arabic_history_kept(monkeypatch):
    calls = fake_client(monkeypatch, json.dumps({'text': 'أكيد! نروح نتعشى؟ 😋'}))
    r = client.post('/api/reply', json={**BASE, 'chatId': 'sara', 'contactName': 'Sara Ali',
        'history': [{'fromMe': True, 'text': 'مبروك الترقية! وين نحتفل؟'}]})
    assert r.json()['text'] == 'أكيد! نروح نتعشى؟ 😋'
    assert calls[0]['messages'][-1]['content'] == 'مبروك الترقية! وين نحتفل؟'
    assert 'Reply language: Arabic' in calls[0]['messages'][0]['content']


def test_missing_key(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY', '')
    r = client.post('/api/reply', json=BASE)
    assert r.status_code == 503 and r.json() == {'detail': 'OpenAI key missing'}


def test_provider_failure(monkeypatch):
    fake_client(monkeypatch, failure=True)
    r = client.post('/api/reply', json=BASE)
    assert r.status_code == 502 and r.json() == {'detail': 'OpenAI contact reply failed'}


@pytest.mark.parametrize('content', ['', 'not json', '{}', '{"text":" "}', '{"text":3}', '[]'])
def test_invalid_output(monkeypatch, content):
    fake_client(monkeypatch, content)
    assert client.post('/api/reply', json=BASE).status_code == 502


def test_unknown_group_sender_rejected(monkeypatch):
    fake_client(monkeypatch, '{"text":"Hello", "sender":"Stranger"}')
    assert client.post('/api/reply', json={**BASE, 'chatId': 'family', 'isGroup': True}).status_code == 502


@pytest.mark.parametrize('history', [[], [{'fromMe': False, 'text': 'Hi'}]])
def test_newest_user_message_required(monkeypatch, history):
    calls = fake_client(monkeypatch)
    assert client.post('/api/reply', json={**BASE, 'history': history}).status_code == 422
    assert calls == []
