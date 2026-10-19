// Anonymous local session continuity. OAuth grants remain server-side.
let session=null;
export async function ensureApiSession(signal){
  if(!session)session=fetch('/api/session',{credentials:'same-origin',signal:signal||AbortSignal.timeout(4000)}).then(async r=>{if(!r.ok)throw new Error('Session unavailable');return r.json();}).catch(e=>{session=null;throw e;});
  return session;
}
export async function labFetch(url,options={}){await ensureApiSession(options.signal);return fetch(url,{...options,credentials:'same-origin'});}
