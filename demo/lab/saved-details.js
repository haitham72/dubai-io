import { registerPage, openPage } from './page-host.js';
import { labFetch } from './api-client.js';
import { told, esc, toast } from './ui.js';
const KEYS={area:['Area','area'],hotel:['Hotel','hotel'],terminal:['Terminal','terminal'],taxi_plate:['Taxi plate','plate'],taxi_roof:['Roof colour','roof'],deadline:['Deadline','deadline'],pet:['Pet','pet'],language:['Language','language'],other:['Other detail','other']};
let version=0;
registerPage('memory.details',{
  title:'Your saved details',source:'You told me',
  render:()=>'<div class="request-workflow"><p>Details you gave Dubai-io. Edit or forget them here.</p><div id="savedDetails"></div></div>',
  mount:body=>{
    const current=++version;let dirty=false;
    body.addEventListener('input',()=>{dirty=true;});
    const draw=()=>{body.querySelector('#savedDetails').innerHTML=Object.entries(KEYS).filter(([,pair])=>typeof told[pair[1]]==='string'&&told[pair[1]]).map(([key,[label,local]])=>'<form class="saved-detail" data-fact="'+key+'"><label>'+esc(label)+'<input maxlength="80" value="'+esc(told[local])+'"></label><div class="actions"><button class="btn sm">Save change</button><button class="btn sm" type="button" data-forget>Forget</button></div></form>').join('')||'<p>No saved details yet.</p>';body.querySelectorAll('form').forEach(form=>{
      const key=form.dataset.fact, local=KEYS[key][1];
      form.addEventListener('submit',async e=>{e.preventDefault();const value=form.querySelector('input').value.trim();if(!value)return;form.querySelectorAll('button').forEach(b=>b.disabled=true);try{const response=await labFetch('/api/session/memory/'+key,{method:'PUT',signal:AbortSignal.timeout(4000),headers:{'Content-Type':'application/json'},body:JSON.stringify({value})});if(!response.ok)throw new Error();told[local]=value;toast('Saved. You told me.');}catch{toast('Could not update saved details. Try again.');}finally{form.querySelectorAll('button').forEach(b=>b.disabled=false);}});
      form.querySelector('[data-forget]').addEventListener('click',async()=>{form.querySelectorAll('button').forEach(b=>b.disabled=true);try{const response=await labFetch('/api/session/memory/'+key,{method:'DELETE',signal:AbortSignal.timeout(4000)});if(!response.ok)throw new Error();delete told[local];draw();toast('Forgotten.');}catch{toast('Could not forget this detail. Try again.');form.querySelectorAll('button').forEach(b=>b.disabled=false);}});
    });};
    draw();
    labFetch('/api/session/memory',{signal:AbortSignal.timeout(4000)}).then(r=>{if(!r.ok)throw new Error();return r.json();}).then(data=>{if(current!==version||!body.isConnected||dirty)return;for(const fact of data.told||[])if(fact.provenance==='user_supplied'&&KEYS[fact.key]&&typeof fact.value==='string')told[KEYS[fact.key][1]]=fact.value;draw();}).catch(()=>{});
  },
});
export function openSavedDetails(){openPage('memory.details');}
