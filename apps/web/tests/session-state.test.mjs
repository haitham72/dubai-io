import test from 'node:test';
import assert from 'node:assert/strict';

async function storage(initial) {
  const values=new Map(initial?[['dubaiio.lab.session.v1',JSON.stringify(initial)]]:[]);
  globalThis.localStorage={getItem:key=>values.get(key)||null,setItem:(key,value)=>values.set(key,value)};
  return import('../session-state.js?test='+Math.random());
}

test('existing single chat migrates without losing messages, identity, facts or drafts',async()=>{
  const initial={version:1,user_id:'existing-user',thread_id:'existing-thread',messages:[{who:'me',text:'My lost bag'}],facts:{area:'Marina'},drafts:{report:{description:'Bag'}}};
  const s=await storage(initial);
  assert.deepEqual(s.identity(),{user_id:'existing-user',thread_id:'existing-thread'});
  assert.equal(s.listConversations()[0].title,'My lost bag');
  s.newConversation();
  assert.notEqual(s.identity().thread_id,'existing-thread');
  assert.equal(s.identity().user_id,'existing-user');
  assert.deepEqual(s.getFacts(),initial.facts);assert.deepEqual(s.getDraft('report'),initial.drafts.report);
  assert.deepEqual(s.getMessages(),[]);
  assert.equal(s.switchConversation('existing-thread'),true);
  assert.deepEqual(s.getMessages(),initial.messages);
});

test('switching chats preserves structured source/task references and separate histories',async()=>{
  const s=await storage();const first=s.identity().thread_id;
  const messages=[{who:'me',text:'Track my order'},{who:'bot',text:'Review it',actionId:'action-1',taskId:'task-1',taskProposal:{task_id:'task-1',expected_revision:2,changes:{details:'New note'}}}];
  s.saveMessages(messages);s.newConversation();const second=s.identity().thread_id;
  s.saveMessages([{who:'me',text:'A different conversation'}]);
  assert.equal(s.switchConversation(first),true);assert.deepEqual(s.getMessages(),messages);
  assert.equal(s.listConversations().length,2);
  assert.equal(s.switchConversation(second),true);assert.equal(s.getMessages()[0].text,'A different conversation');
  assert.equal(s.switchConversation('missing'),false);assert.equal(s.identity().thread_id,second);
});

test('failed storage cannot replace or discard the current conversation',async()=>{
  const s=await storage();s.saveMessages([{who:'me',text:'Keep this'}]);const before=s.identity();
  globalThis.localStorage.setItem=()=>{throw Error('full');};
  assert.throws(()=>s.newConversation(),/could not be saved/);
  assert.deepEqual(s.identity(),before);assert.equal(s.getMessages()[0].text,'Keep this');
});

test('new empty chats do not create empty history entries; restart retains its explicit reset contract',async()=>{
  const s=await storage();s.newConversation();s.newConversation();assert.deepEqual(s.listConversations(),[]);
  s.saveMessages([{who:'me',text:'Hello'}]);s.newConversation();assert.equal(s.listConversations().length,1);
  s.resetSession();assert.deepEqual(s.listConversations(),[]);
});

test('empty project chats survive switching; a new chat starts outside the project',async()=>{
  const s=await storage();const projectThread=s.identity().thread_id;
  s.setConversationProject('moving-home');s.newConversation();
  assert.equal(s.listConversations().find(c=>c.id===projectThread).project_id,'moving-home');
  assert.equal(s.switchConversation(projectThread),true);
  assert.equal(s.listConversations().find(c=>c.active).project_id,'moving-home');
  s.setConversationProject(null);assert.deepEqual(s.listConversations(),[]);
});
