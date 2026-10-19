// Understanding only; this module never executes service actions.
const INTENTS = new Set(['lost_item','airport_guide','service_offers','places_near','greeting','smalltalk','unclear']);
const SERVICES = new Set(['laundry','cleaning','ac','grooming','carwash','pharmacy','maid']);
const CATEGORIES = new Set(['pets','food','coffee','barber','home-help','laundry','clothing','fix-it']);
export function mapUnderstanding(value) {
  if (!value || value.via !== 'langgraph' || !INTENTS.has(value.intent) || !Number.isFinite(value.confidence) || value.confidence < 0 || value.confidence > 1) throw new Error('Invalid Luna response');
  const r = { intent:value.intent, conf:value.confidence, via:'langgraph', model:typeof value.model==='string'?value.model.slice(0,100):'Luna', ms:Number.isFinite(value.ms)?value.ms:null,
    reply:typeof value.reply==='string'?value.reply.slice(0,300):'', clarify:typeof value.clarify==='string'?value.clarify.slice(0,300):'',
    remembered:Array.isArray(value.remembered)?value.remembered.filter(f=>f?.provenance==='user_supplied'&&typeof f.key==='string'&&typeof f.value==='string'):[] };
  if(r.conf<.6 && !['greeting','smalltalk'].includes(r.intent))r.intent='unclear';
  if(r.intent==='lost_item'){r.item=typeof value.item==='string'?value.item.slice(0,80):'item';r.where=['taxi','metro','shop'].includes(value.where_lost)?value.where_lost:null;}
  if(r.intent==='airport_guide')r.terminal=['1','2','3'].includes(value.terminal)?value.terminal:null;
  if(r.intent==='service_offers'){if(!SERVICES.has(value.service))throw new Error('Unknown service');r.service=value.service;}
  if(r.intent==='places_near'){if(!CATEGORIES.has(value.category))throw new Error('Unknown category');r.cat=value.category;r.sub=typeof value.subcategory==='string'?value.subcategory.slice(0,80):null;}
  return r;
}
export function createLunaClient({fetcher=globalThis.fetch,timeoutMs=15000,enabled=true,identity=()=>({})}={}) {
  let generation=0, active=null, queue=Promise.resolve();
  return {
    reset(){generation++;active?.abort();active=null;queue=Promise.resolve();},
    understand(text,fallback){
      const owner=generation;
      const work=async()=>{
        if(owner!==generation)return null;
        if(!enabled)return {...fallback(text),via:'lab router',fallback_reason:'Offline demo'};
        const controller=new AbortController();active=controller;
        let timer;
        try{
          // Promise.race also bounds fetch implementations that ignore abort.
          const timeout=new Promise((_,reject)=>{timer=setTimeout(()=>{controller.abort();reject(new Error('timeout'));},timeoutMs);});
          const call=(async()=>{const response=await fetcher('/api/luna/turn',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify({text,...identity()}),signal:controller.signal});if(!response.ok)throw new Error('API unavailable');return mapUnderstanding(await response.json());})();
          const result=await Promise.race([call,timeout]);return owner===generation?result:null;
        }catch(error){return owner===generation?{...fallback(text),via:'lab router',fallback_reason:error.message==='timeout'?'Luna timed out':'Luna unavailable'}:null;}
        finally{clearTimeout(timer);if(active===controller)active=null;}
      };
      const result=queue.then(work);queue=result.catch(()=>{});return result;
    },
  };
}
