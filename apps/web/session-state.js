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
export function saveMessages(messages){state.messages=messages.slice(-100);save();}
function save(){try{localStorage.setItem(KEY,JSON.stringify(state));}catch{/* Private/full storage: current session still works. */}}
export function resetSession(){state={version:1,user_id:id(),thread_id:id(),messages:[],facts:{},drafts:{}};save();}
