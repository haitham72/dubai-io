import json
from app import social_generation as social
from tests.test_communities import client, other


def test_post_reply_slots_identity_scope_and_replay(client, monkeypatch):
    c, store = client
    seen = []
    def provider(actors, context):
        # The network must never run under the shared DB lock.
        assert not store.lock._is_owned()
        seen.append((actors, context))
        return [f"Reply by {actor['name']}" for actor in actors]
    monkeypatch.setattr(social, "generate", provider)
    c.post('/api/communities/marina-foodies/join')
    payload = {"text":"Where can I buy a second-hand table?", "request_id":"new-post-1"}
    posted = c.post('/api/communities/marina-foodies/posts', json=payload).json()
    assert posted['generation']['status'] == 'completed'
    replies = c.get(f"/api/posts/{posted['id']}/comments").json()['comments']
    assert len(replies) == 10
    assert len({r['author']['persona_id'] for r in replies}) == 10
    assert all(not r['mine'] and r['provenance']=='ai_demo' and r['model']==social.settings.social_model for r in replies)
    again = c.post('/api/communities/marina-foodies/posts', json=payload).json()
    assert again == posted and len(seen)==1
    assert c.post('/api/communities/marina-foodies/posts', json={**payload,"text":"different"}).status_code==409
    assert other(c).get(f"/api/posts/{posted['id']}/comments").status_code==404


def test_nested_reply_targets_parent_and_original_author(client, monkeypatch):
    c, _ = client
    seen=[]
    def provider(actors, context):
        seen.append((actors,context))
        return ['I can help with that.' for _ in actors]
    monkeypatch.setattr(social,'generate',provider)
    post=c.get('/api/feed').json()['posts'][0]
    comments=c.get(f"/api/posts/{post['id']}/comments").json()['comments']
    parent=next(m for m in comments if m['author']['persona_id']!=post['author']['persona_id'])
    result=c.post(f"/api/posts/{post['id']}/comments",json={"text":"Could you explain your suggestion?","parent_id":parent['id'],"request_id":"nested-1"}).json()
    assert result['generation']['reply_count']==2
    assert [p['id'] for p in seen[0][0]][:2]==[parent['author']['persona_id'],post['author']['persona_id']]
    own=c.get(f"/api/posts/{post['id']}/comments").json()['comments']
    assert next(m for m in own if m['id']==result['id'])['parent_id']==parent['id']
    assert all(m['parent_id']==result['id'] for m in own if m['provenance']=='ai_demo')
    outsider=other(c)
    assert not any(m['provenance']=='ai_demo' for m in outsider.get(f"/api/posts/{post['id']}/comments").json()['comments'])
    assert outsider.post(f"/api/posts/{post['id']}/comments",json={"text":"x","parent_id":result['id']}).status_code==404


def test_failure_preserves_input_without_fake_replies(client,monkeypatch):
    c,_=client
    def fail(*args):
        raise TimeoutError('private upstream details')
    monkeypatch.setattr(social,'generate',fail)
    post=c.get('/api/feed').json()['posts'][0]
    payload={"text":"Can someone help?","request_id":"failed-1"}
    result=c.post(f"/api/posts/{post['id']}/comments",json=payload).json()
    assert result['generation']['status']=='failed' and result['generation']['reply_count']==0
    assert 'private' not in json.dumps(result)
    assert c.post(f"/api/posts/{post['id']}/comments",json=payload).json()==result
    assert sum(m['text']==payload['text'] for m in c.get(f"/api/posts/{post['id']}/comments").json()['comments'])==1


def test_direct_persona_history_does_not_leak_between_threads_or_owners(client,monkeypatch):
    c,_=client
    fixtures={"personas":[{"id":"mom-test","name":"Mother","handle":"mom","emoji":"🌸","bio":"Caring mother","area":"Dubai","relationship":"mother"},{"id":"boss-test","name":"Boss","handle":"boss","emoji":"💼","bio":"Manager","area":"Dubai"}],"threads":[{"id":"direct:mother","title":"Mother","persona_ids":["mom-test"],"messages":[{"persona_id":"mom-test","text":"Did you have lunch?"}]},{"id":"direct:boss","title":"Boss","persona_ids":["boss-test"],"messages":[{"persona_id":"boss-test","text":"Private work discussion"}]}]}
    monkeypatch.setattr(social,'chat_fixture',lambda:fixtures)
    seen=[]
    monkeypatch.setattr(social,'generate',lambda actors,context: seen.append((actors,context)) or ['How was your lunch?'])
    c.get('/api/chats')
    result=c.post('/api/chats/direct:mother/messages',json={"text":"I ate well","request_id":"mother-1"}).json()
    assert result['generation']['status']=='completed'
    assert seen[0][0][0]['id']=='mom-test' and seen[0][0][0]['profile']['relationship']=='mother'
    assert 'Private work discussion' not in json.dumps(seen)
    assert 'I ate well' in json.dumps(seen)
    messages=c.get('/api/chats/direct:mother/messages').json()['messages']
    assert messages[-1]['author']=='Mother' and messages[-1]['persona_id']=='mom-test' and not messages[-1]['mine']
    outsider=other(c); outsider.get('/api/chats')
    assert 'I ate well' not in json.dumps(outsider.get('/api/chats/direct:mother/messages').json())


def test_leaving_community_removes_chat_and_blocks_access(client):
    c,_=client
    c.post('/api/communities/marina-foodies/join');c.get('/api/chats')
    c.post('/api/communities/marina-foodies/leave')
    assert 'community:marina-foodies' not in json.dumps(c.get('/api/chats').json())
    assert c.get('/api/chats/community:marina-foodies/messages').status_code==404
    assert c.post('/api/chats/community:marina-foodies/messages',json={"text":"hello"}).status_code==404


def test_provider_output_cannot_assign_identity(client, monkeypatch):
    from types import SimpleNamespace
    c, _ = client
    monkeypatch.setattr(social.settings,'nararouter_api_key','test-only')
    class FakeProvider:
        def __init__(self, **kwargs):
            assert kwargs['max_retries']==0 and kwargs['timeout']==social.settings.social_timeout_s
            self.chat=SimpleNamespace(completions=self)
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def create(self,**kwargs):
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps({'replies':[{'author_id':'attacker','text':'Forged'}]})))])
    monkeypatch.setattr(social,'OpenAI',FakeProvider)
    c.post('/api/communities/marina-foodies/join')
    result=c.post('/api/communities/marina-foodies/posts',json={'text':'Hello neighbours'}).json()
    assert result['generation']['status']=='failed'
    assert c.get(f"/api/posts/{result['id']}/comments").json()['comments']==[]


def test_cross_post_parent_rejected(client):
    c,_=client
    posts=c.get('/api/feed').json()['posts']
    first=next(p for p in posts if p['comments'])
    parent=c.get(f"/api/posts/{first['id']}/comments").json()['comments'][0]
    second=next(p for p in posts if p['id']!=first['id'])
    assert c.post(f"/api/posts/{second['id']}/comments",json={'text':'wrong thread','parent_id':parent['id']}).status_code==404


def test_community_actor_never_receives_private_relationship_profile(client, monkeypatch):
    c,store=client
    c.get('/api/communities')
    private={'id':'p01','name':'Sara','bio':'Your wife; knows your private household plans','relationship':'wife','profile':{'relationship':'wife','private_context':'secret family plans'}}
    store.db.execute('UPDATE personas SET profile=?,bio=? WHERE id=?',(json.dumps(private),private['bio'],'p01'))
    store.db.commit()
    seen=[]
    monkeypatch.setattr(social,'generate',lambda actors,context: seen.append((actors,context)) or ['Thanks for asking.' for _ in actors])
    post=store.db.execute("SELECT id FROM posts WHERE persona_id='p01' AND kind='post' LIMIT 1").fetchone()[0]
    c.post(f'/api/posts/{post}/comments',json={'text':'Any recommendations?'})
    actor=next(p for p in seen[-1][0] if p['id']=='p01')
    encoded=json.dumps(actor).lower()
    assert 'wife' not in encoded and 'relationship' not in encoded and 'secret family' not in encoded
    c.post('/api/communities/marina-foodies/join'); c.get('/api/chats')
    c.post('/api/chats/community:marina-foodies/messages',json={'text':'Hello neighbours'})
    assert 'wife' not in json.dumps(seen[-1][0]).lower()


def test_leaving_during_provider_wait_drops_late_reply(client,monkeypatch):
    c,store=client
    c.post('/api/communities/marina-foodies/join');c.get('/api/chats')
    def provider(actors,context):
        assert not store.lock._is_owned()
        assert c.post('/api/communities/marina-foodies/leave').status_code==200
        return ['A late reply' for _ in actors]
    monkeypatch.setattr(social,'generate',provider)
    result=c.post('/api/chats/community:marina-foodies/messages',json={'text':'See you tomorrow','request_id':'leave-during-generation'}).json()
    assert result['generation']['status']=='failed' and result['generation']['reply_count']==0
    assert store.db.execute("SELECT COUNT(*) FROM chat_messages WHERE trigger_id=?",(result['id'],)).fetchone()[0]==0
    assert store.db.execute("SELECT text FROM chat_messages WHERE id=?",(result['id'],)).fetchone()[0]=='See you tomorrow'


def test_hiding_post_during_provider_wait_drops_late_reply(client,monkeypatch):
    c,store=client
    post=c.get('/api/feed').json()['posts'][0]
    def provider(actors,context):
        c.post(f"/api/posts/{post['id']}/hide",json={})
        return ['A late reply' for _ in actors]
    monkeypatch.setattr(social,'generate',provider)
    result=c.post(f"/api/posts/{post['id']}/comments",json={'text':'Tell me more'}).json()
    assert result['generation']['status']=='failed'
    assert store.db.execute('SELECT COUNT(*) FROM comments WHERE trigger_id=?',(result['id'],)).fetchone()[0]==0
