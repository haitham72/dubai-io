// Section 03 of Home. Pull on reaching the end of task history, never poll.
import { labFetch } from './api-client.js';
import { esc, svg } from './ui.js';
import { browsingSession } from './recommendation-client.js';
import { selectFocus } from './assistant-context.js';

const TOPICS = {for_you:'For you',dubai:'Dubai',arts:'Arts & culture',food:'Food',events:'Events',technology:'Technology',official:'Official updates'};
const date = value => new Intl.DateTimeFormat('en-GB',{timeZone:'Asia/Dubai',day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'}).format(new Date(value));
export function createReading(root) {
  let eligible=false, active=false, inView=false, generation=0, loaded=false, loading=false, topic='for_you', articles=[], enabled=true;
  try { enabled=localStorage.getItem('dubaiio.news.hidden')!=='1'; } catch { /* current visit */ }
  function render(data) {
    root.innerHTML=`<header class="reading-header"><div><p>For your day</p><h2>News</h2></div><button data-toggle-news>${enabled?'Hide news':'Show news'}</button></header>
      ${enabled ? `<div class="reading-topics" role="group" aria-label="News topics">${Object.entries(TOPICS).map(([key,label])=>`<button data-news-topic="${key}" aria-pressed="${key===topic}">${esc(label)}</button>`).join('')}</div>
      <p class="reading-reason">${esc(data?.reason||'Recent headlines from Dubai and topics you choose.')}</p>
      <div class="reading-articles">${articles.map(article=>`<article class="${article.thumbnail?'has-thumb':''}">${article.thumbnail?`<figure class="reading-thumb"><img src="${esc(article.thumbnail.url)}" alt="" loading="lazy" decoding="async" width="96" height="96"><figcaption>Image: ${esc(article.thumbnail.credit)}</figcaption></figure>`:''}${article.provenance==='demo_fixture'?'<span class="pill demo">Demo data</span>':''}<p>${esc(article.source)} · <time datetime="${esc(article.published_at)}">${esc(date(article.published_at))} Dubai time</time></p><h3><a href="${esc(article.url)}">${esc(article.title)}</a></h3><button data-ask-news="${esc(article.id)}">Ask about this ${svg('arrow','ic xs')}</button></article>`).join('')}</div>
      <p class="reading-status" role="status">${loading?'Finding recent headlines…':data?.status==='unavailable'?'News could not load right now. Try again shortly.':data?.status==='preferences_changed'?esc(data.reason):loaded&&!articles.length?'No recent headlines were returned for this selection.':''}</p>
      <footer><button data-refresh-news>Refresh news</button><small>${data?.checked_at?'Checked '+esc(date(data.checked_at))+' · Dubai time. ':''}${esc(data?.attribution||'Open a headline to read at its publisher.')} ${data?.date_basis?esc(data.date_basis):''}</small></footer>` : '<p class="today-quiet">News is hidden. Your tasks stay above.</p>'}`;
  }
  async function load(force=false) {
    if(!active||!eligible||!enabled||!inView||loading||(loaded&&!force))return;
    loading=true;const mine=++generation;root.setAttribute('aria-busy','true');
    const status=root.querySelector('.reading-status');if(status)status.textContent='Finding recent headlines…';
    try {
      const response=await labFetch('/api/reading?topic='+topic+'&session_id='+encodeURIComponent(browsingSession()),{signal:AbortSignal.timeout(12000)});
      const data=await response.json();
      if(mine!==generation||!active||!eligible)return;
      if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:'News could not load.');
      articles=(data.articles||[]).filter(article=>typeof article.title==='string'&&article.url?.startsWith('https://')&&Number.isFinite(Date.parse(article.published_at))).map(article=>({...article,thumbnail:article.thumbnail?.url?.startsWith('/api/reading/thumbnails/')?article.thumbnail:null}));
      loaded=true;loading=false;render(data);
    } catch(error) {
      if(mine!==generation||!active)return;
      const status=root.querySelector('.reading-status');if(status)status.textContent=error.name==='Error'&&error.message!=='News could not load.'?error.message:'News could not load right now. Try again shortly.';
    } finally {if(mine===generation){loading=false;root.removeAttribute('aria-busy');}}
  }
  render();
  // A thumbnail that fails to load disappears; the headline stays.
  root.addEventListener('error',event=>{const figure=event.target.closest?.('.reading-thumb');if(figure){figure.closest('article')?.classList.remove('has-thumb');figure.remove();}},true);
  const observer=new IntersectionObserver(entries=>{inView=entries.some(entry=>entry.isIntersecting);if(inView)load();},{root:root.closest('.home-feed'),rootMargin:'100px'});
  observer.observe(root);
  addEventListener('dubaiio:task-history-end',event=>{eligible=!!event.detail.exhausted;root.hidden=!eligible;if(eligible)load();else{generation++;loading=false;root.removeAttribute('aria-busy');}});
  addEventListener('dubaiio:interests-changing',()=>{generation++;loaded=false;loading=false;articles=[];render();});
  addEventListener('dubaiio:interests-changed',()=>load(true));
  root.addEventListener('click',event=>{
    if(event.target.closest('[data-toggle-news]')){enabled=!enabled;generation++;loading=false;root.removeAttribute('aria-busy');try{localStorage.setItem('dubaiio.news.hidden',enabled?'0':'1');}catch{/* current visit */}render();if(enabled){loaded=false;load();}}
    const select=event.target.closest('[data-news-topic]');
    if(select&&select.dataset.newsTopic!==topic){topic=select.dataset.newsTopic;generation++;loading=false;loaded=false;articles=[];render();root.querySelector(`[data-news-topic="${topic}"]`)?.focus({preventScroll:true});load();}
    if(event.target.closest('[data-refresh-news]'))load(true);
    const ask=event.target.closest('[data-ask-news]');
    if(ask){const article=articles.find(item=>item.id===ask.dataset.askNews);if(!article)return;selectFocus({entity_id:'news:'+article.id,entity_name:article.title.slice(0,120),source:'app',card:'News headline',fragment:(article.source+' · Published '+article.published_at+' · '+article.url).slice(0,300)});dispatchEvent(new CustomEvent('dubaiio:news-chat'));}
  });
  return {show(value){active=value;if(!value){generation++;loading=false;root.removeAttribute('aria-busy');}else load();}};
}
