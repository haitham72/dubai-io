import { statusLabel } from './status-labels.js';
// Host request workflow. Merchant widgets cannot access anonymous sessions.
import { registerPage, openPage } from './page-host.js';
import { $, esc, toast, told } from './ui.js';
import { getDraft, saveDraft } from './session-state.js';
let sessionPromise=null;
const visible=body=>body.isConnected&&!$('#sheet').hidden&&ownBody()===body;
const draftKey=c=>c.capability+':'+(c.provider?.id||'generic');
const LABELS={request:'What do you need?',area:'Area',provider:'Provider',description:'Item description',when:'Date and time',from:'Pickup',to:'Drop-off',plate:'Taxi plate',roof:'Roof colour',fare:'Trip fare',payment:'Payment method',booking:'Booking reference'};
const FIELD_KEYS={request:['request','area','provider'],recovery:['description','when','from','to','plate','roof','fare','payment','booking']};
const completeFields=(capability,fields)=>Object.fromEntries(FIELD_KEYS[capability==='recovery.rta'?'recovery':'request'].map(key=>[key,fields?.[key]||'']));
const REQUIRED={request:['request','area'],recovery:['description','when','from','to']};
const SERVICES={laundry:'Laundry',cleaning:'Home cleaning',ac:'AC service',grooming:'Pet grooming',carwash:'Car wash',pharmacy:'Pharmacy',maid:'Maid hire'};
export async function api(url, options={}) {
  if(!sessionPromise)sessionPromise=fetch('/api/session',{credentials:'same-origin',signal:AbortSignal.timeout(4000)}).then(r=>{if(!r.ok)throw new Error('Session unavailable');return r.json();}).catch(e=>{sessionPromise=null;throw e;});
  await sessionPromise;
  const r=await fetch(url,{...options,credentials:'same-origin',signal:options.signal||AbortSignal.timeout(5000),headers:{'Content-Type':'application/json',...options.headers}});
  const data=await r.json();if(!r.ok)throw new Error(typeof data.detail==='string'?data.detail:'Could not save this request');return data;
}
function ownBody(){return document.querySelector('[data-page-id="service.request"] .page-host-content');}
function values(){return Object.fromEntries([...ownBody().querySelectorAll('[data-request-field]')].map(e=>[e.dataset.requestField,e.value.trim()]));}
function safeFields(fields){return Object.fromEntries(Object.entries(fields||{}).filter(([key,value])=>Object.hasOwn(LABELS,key)&&typeof value==='string').map(([key,value])=>[key,value.slice(0,600)]));}
registerPage('service.request', {
  title:c=>c.title,source:'Dubai-io · service request',
  render:c=>'<div class="request-workflow">'+(c.provider?'<p><b>'+esc(c.provider.name)+'</b> · demo provider</p>':'')+'<p class="request-intro">I’ll keep the details here. You review what will be shared before any action is sent.</p><form id="serviceRequestForm">'+Object.entries(c.fields).map(([key,value])=>'<label>'+esc(LABELS[key])+ (c.required.includes(key)?' <span class="request-required">needed</span>':'')+(key==='request'||key==='description'?'<textarea data-request-field="'+key+'" maxlength="600" placeholder="'+esc(LABELS[key])+'">'+esc(value)+'</textarea>':'<input data-request-field="'+key+'" maxlength="600" value="'+esc(value)+'">')+'</label>').join('')+'<p id="serviceRequestError" role="alert"></p><button class="btn primary wide" type="submit">Save and review request</button></form><section id="serviceRequestResult" aria-live="polite"></section></div>',
  mount:(body,c)=>{

    body.querySelector('#serviceRequestForm').addEventListener('input',()=>{
      c.fields=values();c.result=null;c.prepareKey=null;saveDraft(draftKey(c),{fields:c.fields,draft_id:c.draft_id});
      body.querySelector('#serviceRequestResult').innerHTML='';
    });
    body.querySelector('#serviceRequestForm').addEventListener('submit',async e=>{
      e.preventDefault();const button=e.submitter||e.target.querySelector('button');button.disabled=true;
      body.querySelectorAll('[data-request-field]').forEach(el=>el.disabled=true);
      c.fields=values();c.prepareKey||=crypto.randomUUID();saveDraft(draftKey(c),{fields:c.fields,draft_id:c.draft_id,prepareKey:c.prepareKey});
      try{
        const result=await api('/api/actions/prepare',{method:'POST',body:JSON.stringify({capability_id:c.capability,draft_id:c.draft_id||null,preparation_key:c.prepareKey,fields:Object.fromEntries(Object.entries(c.fields).map(([key,value])=>[key,{value,provenance:'user_supplied'}]))})});
        c.result=result;c.draft_id=result.id;c.prepareKey=null;saveDraft(draftKey(c),{fields:c.fields,draft_id:result.id});
        if(visible(body))renderResult(body,c);
      }catch(err){if(visible(body))body.querySelector('#serviceRequestError').textContent='Saved in this browser. '+err.message+'. Nothing has been sent.';}
      finally{if(body.isConnected){button.disabled=false;body.querySelectorAll('[data-request-field]').forEach(el=>el.disabled=false);}}
    });
    if(c.result)renderResult(body,c);
    else if(c.draft_id)api('/api/actions/'+encodeURIComponent(c.draft_id)).then(result=>{if(visible(body)){c.result=result;renderResult(body,c);}}).catch(()=>{});
  },
});
function renderResult(body,c){
  const result=c.result, box=body.querySelector('#serviceRequestResult');
  const missing=result.status==='DRAFT'&&result.missing?.length;
  box.innerHTML='<article class="request-result" data-status="'+esc(result.status)+'"><span class="page-tag">'+esc(({SUBMITTED:'Provider response',DISPATCHING:'Sending',UNKNOWN_STATUS:'Needs checking',CANCELLED:'Discarded draft'})[result.status]||'Saved draft')+'</span><h3>'+esc(({DRAFT:'A few details are missing',AWAITING_APPROVAL:'Review before sending',SUBMITTED:'Provider received the request',DISPATCHING:'Sending request',UNKNOWN_STATUS:'Provider outcome unknown',CANCELLED:'Draft discarded'})[result.status]||'Prepared · not sent')+'</h3><p>'+esc(missing?'Add '+result.missing.map(key=>LABELS[key]||key).join(', ')+'.':result.blocked_reason||'Check the recipient and exact details below.')+'</p><p><b>Recipient:</b> '+esc(result.recipient)+'</p><p>'+esc(result.effect||'')+(result.fixed_total_aed!=null?' · AED '+esc(result.fixed_total_aed):'')+'</p><dl>'+Object.entries(result.fields).map(([key,f])=>'<div><dt>'+esc(LABELS[key]||key)+'</dt><dd>'+esc(f.value)+'</dd></div>').join('')+'</dl>'+(result.evidence?'<p>Provider reference: <b>'+esc(result.evidence.reference)+'</b></p>':'')+(result.status==='AWAITING_APPROVAL'&&result.execution_available?'<button class="btn primary wide" id="serviceApprove">Approve and send these details</button>':'')+(['DRAFT','BLOCKED','AWAITING_APPROVAL'].includes(result.status)?'<button class="btn wide" id="serviceDiscard">Discard draft</button>':'')+'</article>';
  if(result.status==='CANCELLED')body.querySelectorAll('[data-request-field], #serviceRequestForm button').forEach(el=>el.disabled=true);
  box.querySelector('#serviceDiscard')?.addEventListener('click',async e=>{e.target.disabled=true;try{c.result=await api('/api/actions/'+encodeURIComponent(result.id)+'/cancel',{method:'POST'});saveDraft(draftKey(c),null);if(visible(body))renderResult(body,c);}catch(error){toast(error.message);if(e.target.isConnected)e.target.disabled=false;}});
  box.querySelector('#serviceApprove')?.addEventListener('click',async e=>{
    e.target.disabled=true;
    body.querySelectorAll('[data-request-field], #serviceRequestForm button').forEach(el=>el.disabled=true);
    c.approvalKey||=crypto.randomUUID();
    try{c.result=await api('/api/actions/'+encodeURIComponent(result.id)+'/approve',{method:'POST',headers:{'Idempotency-Key':c.approvalKey},body:JSON.stringify({snapshot_hash:result.snapshot_hash,revision:result.revision})});if(body.isConnected)renderResult(body,c);}
    catch(err){toast(err.message);if(e.target.isConnected)e.target.disabled=false;}
    finally{if(body.isConnected)body.querySelectorAll('[data-request-field], #serviceRequestForm button').forEach(el=>el.disabled=false);}
  });
}
export function openServiceRequest(service,{provider=null,request=''}={}){
  if(!Object.hasOwn(SERVICES,service))return;
  const capability=service+'.request',saved=getDraft(capability+':'+(provider?.id||'generic'));
  openPage('service.request',{capability,title:SERVICES[service],provider,fields:safeFields(saved?.fields||{request,area:told.area||'',provider:provider?.name||''}),required:REQUIRED.request,draft_id:saved?.draft_id||null,prepareKey:saved?.prepareKey||null});
}
export function openRecoveryRequest(report){
  const capability='recovery.rta',saved=getDraft(capability+':generic');
  const fields=safeFields(saved?.fields||{description:report.description,...Object.fromEntries(report.fields.filter(f=>f.provenance==='user_supplied').map(f=>[f.key,f.value]))});
  for(const key of ['description','when','from','to','plate','roof','fare','payment','booking'])fields[key]||='';
  openPage('service.request',{capability,title:'Taxi lost item report',fields,required:REQUIRED.recovery,draft_id:saved?.draft_id||null,prepareKey:saved?.prepareKey||null});
}
registerPage('service.saved',{
  title:'Saved requests',source:'Dubai-io · your progress',
  render:()=>'<div id="savedRequests"><p>Loading your saved requests…</p></div>',
  mount:body=>{api('/api/actions').then(data=>{if(!body.isConnected)return;body.querySelector('#savedRequests').innerHTML=data.actions.length?data.actions.map(a=>'<button class="btn wide" data-saved-action="'+esc(a.id)+'" data-status="'+esc(a.status)+'">'+esc(SERVICES[a.capability_id.split('.')[0]]||'Taxi lost item')+' · '+esc(statusLabel(a.status))+'</button>').join(''):'<p>No saved requests yet.</p>';body.querySelectorAll('[data-saved-action]').forEach(button=>button.addEventListener('click',async()=>{try{const a=await api('/api/actions/'+button.dataset.savedAction),service=a.capability_id.split('.')[0];openPage('service.request',{capability:a.capability_id,title:SERVICES[service]||'Taxi lost item report',fields:completeFields(a.capability_id,safeFields(Object.fromEntries(Object.entries(a.fields).map(([k,f])=>[k,f.value])))),required:a.capability_id==='recovery.rta'?REQUIRED.recovery:REQUIRED.request,draft_id:a.id,result:a});}catch(e){toast(e.message);}}));}).catch(()=>{if(body.isConnected)body.querySelector('#savedRequests').innerHTML='<p>The request server is unavailable. Draft edits remain saved in this browser.</p>';});},
});
export function openSavedRequests(){openPage('service.saved');}
