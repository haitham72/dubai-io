// Understanding only; this module never executes service actions.
const INTENTS = new Set(['lost_item','airport_guide','service_offers','places_near','order_status','task_help','info_question','market_quote','product_search','greeting','smalltalk','unclear']);
const SERVICES = new Set(['laundry','cleaning','ac','grooming','carwash','pharmacy','maid']);
const CATEGORIES = new Set(['pets','food','coffee','barber','home-help','laundry','clothing','fix-it']);
export function mapUnderstanding(value) {
  if (!value || value.via !== 'langgraph' || !INTENTS.has(value.intent) || !Number.isFinite(value.confidence) || value.confidence < 0 || value.confidence > 1) throw new Error('Invalid Luna response');
  const r = { intent:value.intent, conf:value.confidence, via:'langgraph', model:typeof value.model==='string'?value.model.slice(0,100):'Luna', ms:Number.isFinite(value.ms)?value.ms:null,
    reply:typeof value.reply==='string'?value.reply.slice(0,300):'', clarify:typeof value.clarify==='string'?value.clarify.slice(0,300):'',
    remembered:Array.isArray(value.remembered)?value.remembered.filter(f=>f?.provenance==='user_supplied'&&typeof f.key==='string'&&typeof f.value==='string'):[] };
  if(r.conf<.6 && !['greeting','smalltalk'].includes(r.intent))r.intent='unclear';
  if(r.intent==='task_help')r.task_edits=Array.isArray(value.task_edits)&&value.task_edits.length<=4?value.task_edits.filter(e=>e&&['outcome','next_step','details','due_at'].includes(e.field)&&typeof e.value==='string').map(e=>({field:e.field,value:e.value.slice(0,1600)})):[];
  if(r.intent==='lost_item'){r.item=typeof value.item==='string'?value.item.slice(0,80):'item';r.where=['taxi','metro','shop'].includes(value.where_lost)?value.where_lost:null;}
  if(r.intent==='airport_guide')r.terminal=['1','2','3'].includes(value.terminal)?value.terminal:null;
  if(r.intent==='service_offers'){if(!SERVICES.has(value.service))throw new Error('Unknown service');r.service=value.service;}
  if(['info_question','market_quote','product_search'].includes(r.intent)){r.answer=typeof value.answer==='string'?value.answer.slice(0,700):'';r.tool=typeof value.tool==='string'?value.tool.slice(0,20):'';
    r.sources=(Array.isArray(value.sources)?value.sources:[]).filter(s=>s&&typeof s.url==='string'&&/^https:\/\//.test(s.url)).slice(0,5).map(s=>({n:Number.isInteger(s.n)?s.n:null,title:String(s.title||'').slice(0,120),url:s.url,via:String(s.via||'').slice(0,30),as_of:String(s.as_of||'')}));}
  if(r.intent==='product_search')r.products=(Array.isArray(value.products)?value.products:[]).filter(p=>p&&typeof p.link==='string'&&/^https:\/\/www\.amazon\.ae\//.test(p.link)&&typeof p.title==='string').slice(0,10)
    .map(p=>({title:p.title.slice(0,140),link:p.link,price:typeof p.price==='string'?p.price.slice(0,20):null,rating:Number.isFinite(p.rating)?p.rating:null,reviews:Number.isInteger(p.reviews)?p.reviews:null,
      thumbnail:typeof p.thumbnail==='string'&&/^https:\/\/m\.media-amazon\.com\//.test(p.thumbnail)?p.thumbnail:null,as_of:String(p.as_of||'')}));
  if(r.intent==='places_near'){if(!CATEGORIES.has(value.category))throw new Error('Unknown category');r.cat=value.category;r.sub=typeof value.subcategory==='string'?value.subcategory.slice(0,80):null;}
  return r;
}
export function createLunaClient({fetcher=globalThis.fetch,timeoutMs=15000,enabled=true,identity=()=>({}),context=()=>({})}={}) {
  let generation=0, active=null, queue=Promise.resolve();
  return {
    reset(){generation++;active?.abort();active=null;queue=Promise.resolve();},
    understand(text,fallback){
      const requestContext=context();
      const owner=generation;
      const work=async()=>{
        if(owner!==generation)return null;
        const on=typeof enabled==='function'?await Promise.resolve().then(enabled).catch(()=>false):enabled;
        if(owner!==generation)return null;
        if(!on)return {...fallback(text),via:'lab router',fallback_reason:'Luna offline'};
        const controller=new AbortController();active=controller;
        let timer;
        try{
          // Promise.race also bounds fetch implementations that ignore abort.
          const timeout=new Promise((_,reject)=>{timer=setTimeout(()=>{controller.abort();reject(new Error('timeout'));},timeoutMs);});
          const call=(async()=>{const response=await fetcher('/api/luna/turn',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify({text,...identity(),...requestContext}),signal:controller.signal});if(!response.ok)throw new Error('API unavailable');return mapUnderstanding(await response.json());})();
          const result=await Promise.race([call,timeout]);return owner===generation?result:null;
        }catch(error){return owner===generation?{...fallback(text),via:'lab router',fallback_reason:error.message==='timeout'?'Luna timed out':'Luna unavailable'}:null;}
        finally{clearTimeout(timer);if(active===controller)active=null;}
      };
      const result=queue.then(work);queue=result.catch(()=>{});return result;
    },
  };
}
