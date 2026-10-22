// Same-browser lab continuity only. No credentials, OAuth grants or raw HTML.
const KEY='dubaiio.lab.session.v1';
const id=()=>globalThis.crypto?.randomUUID?.() || 'lab-'+Date.now().toString(36)+'-'+Math.random().toString(36).slice(2);
function read(){try{const v=JSON.parse(localStorage.getItem(KEY));return v?.version===1?v:null;}catch{return null;}}
let state=read()||{version:1,user_id:id(),thread_id:id(),messages:[],facts:{},drafts:{}};
export const identity=()=>({user_id:state.user_id,thread_id:state.thread_id});
export function getMessages(){return Array.isArray(state.messages)?state.messages.slice(-100):[];}
export function getFacts(){return state.facts&&typeof state.facts==='object'?state.facts:{};}
export function getDraft(key){return state.drafts?.[key]||null;}
export function saveDraft(key,value){state.drafts||={};state.drafts[key]=value;save();}
export function saveFacts(facts){state.facts=JSON.parse(JSON.stringify(facts,(key,value)=>key==='receipt'?undefined:value));save();}
export function saveMessages(messages){const next=messages.slice(-100);if(JSON.stringify(next)!==JSON.stringify(state.messages)){state.updated_at=new Date().toISOString();}state.messages=next;save();}
function save(){try{localStorage.setItem(KEY,JSON.stringify(state));return true;}catch{return false;/* Private/full storage: current session still works. */}}
export function resetSession(){state={version:1,user_id:id(),thread_id:id(),messages:[],facts:{},drafts:{}};save();}

// Conversation history stays on this device. A new chat changes the model's
// thread, never the signed-in owner or their saved facts and service drafts.
function storedConversations(){return Array.isArray(state.conversations)?state.conversations.filter(c=>c&&typeof c.thread_id==='string'&&Array.isArray(c.messages)&&c.thread_id!==state.thread_id):[];}
function currentConversation(){return {thread_id:state.thread_id,messages:getMessages(),updated_at:state.updated_at||null,project_id:state.project_id||null};}
export function setConversationProject(projectId){state.project_id=projectId||null;save();}
export const currentConversationProject=()=>state.project_id||null;
export function listConversations(){
  return [...storedConversations(),currentConversation()].filter(c=>c.messages.length||c.project_id).map(c=>({
    id:c.thread_id,title:String(c.messages.find(m=>m.who==='me'&&typeof m.text==='string')?.text||(c.project_id?'New chat':'Conversation')).replace(/\s+/g,' ').slice(0,80),
    updated_at:c.updated_at,active:c.thread_id===state.thread_id,project_id:c.project_id||null,
  })).sort((a,b)=>(b.updated_at||'').localeCompare(a.updated_at||''));
}
function moveToConversation(target,conversations){
  const previous=state;
  state={...state,thread_id:target.thread_id,messages:target.messages.slice(-100),updated_at:target.updated_at,project_id:target.project_id||null,conversations};
  if(!save()){state=previous;throw new Error('Chat history could not be saved on this device. Free some browser storage and try again.');}
}
export function newConversation(){
  const conversations=storedConversations();
  if(getMessages().length||state.project_id)conversations.push(currentConversation());
  moveToConversation({thread_id:id(),messages:[],updated_at:new Date().toISOString()},conversations);
}
export function switchConversation(threadId){
  if(threadId===state.thread_id)return true;
  const conversations=storedConversations(),target=conversations.find(c=>c.thread_id===threadId);
  if(!target)return false;
  const remaining=conversations.filter(c=>c.thread_id!==threadId);
  if(getMessages().length||state.project_id)remaining.push(currentConversation());
  moveToConversation(target,remaining);return true;
}
