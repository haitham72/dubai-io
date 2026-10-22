// Workspaces organize references and explicit shared notes, never execution.
import { api } from './service-workflow.js';
import { esc, svg, closeSheet, toast } from './ui.js';
import { registerPage, openPage } from './page-host.js';
import { identity, listConversations, setConversationProject, currentConversationProject } from './session-state.js';
import { startNewChat, openConversation } from './chat.js';
import { openTask, taskStateLabel } from './tasks.js';
import { selectProjectFocus, setProjectContextReady } from './assistant-context.js';

const key=()=>crypto.randomUUID();
const current=root=>root.isConnected&&root.closest('#sheet')?.classList.contains('open');
const post=(path,body)=>api(path,{method:'POST',body:JSON.stringify(body)});
const projectUrl=id=>'/api/projects/'+encodeURIComponent(id);
let focusGeneration=0;
export function refreshProjectContext(){
  const mine=++focusGeneration,thread=identity().thread_id;
  selectProjectFocus(null);
  const work=(async()=>{try{const data=await api('/api/projects/for-chat/'+encodeURIComponent(thread));if(mine===focusGeneration&&identity().thread_id===thread){selectProjectFocus(data.project);setConversationProject(data.project?.id);}}catch(error){if(mine===focusGeneration&&identity().thread_id===thread&&currentConversationProject())throw error;/* Unscoped chats retain the existing offline fallback. */}})();
  setProjectContextReady(work);return work.catch(()=>{});
}
addEventListener('dubaiio:conversation-changed',refreshProjectContext);
addEventListener('dubaiio:project-changed',refreshProjectContext);
function changed(){dispatchEvent(new CustomEvent('dubaiio:project-changed'));}
function error(root,message){const el=root.querySelector('[data-project-error]');if(el){el.hidden=false;el.textContent=message;}const reload=root.querySelector('[data-reload-project]');if(reload)reload.hidden=false;}
const failure='<p data-project-error role="alert" hidden></p><button class="today-note" data-reload-project hidden>Reload latest project</button>';
function open(id,focus=false){openPage('projects.detail',{id,focus});}
export function openProjects(){openPage('projects.list');}
document.addEventListener('click',event=>{const button=event.target.closest('[data-project-page]');if(button)open(button.dataset.projectPage);});

registerPage('projects.list',{
  title:'Projects',source:'Your workspaces',
  render:()=>'<p class="lead">Related chats, tasks and the context you choose to share.</p><button class="btn primary wide" data-new-project>New project</button><div data-project-list></div><p data-project-error role="alert" hidden></p>',
  mount(root){
    let offset=0,busy=false;
    root.querySelector('[data-new-project]').onclick=()=>openPage('projects.new');
    async function load(){if(busy||offset===null)return;busy=true;try{const data=await api('/api/projects?offset='+offset);if(!root.isConnected)return;root.querySelector('[data-more-projects]')?.remove();const list=root.querySelector('[data-project-list]');if(!offset&&!data.projects.length)list.innerHTML='<p class="today-quiet">Start a project when a few things belong together.</p>';list.insertAdjacentHTML('beforeend',data.projects.map(p=>`<button class="project-list-row" data-project-id="${esc(p.id)}"><span>${svg('folder','ic sm')}</span><span><b>${esc(p.name)}</b><small>${p.status==='ARCHIVED'?'Archived':'Workspace'}</small></span>${svg('chev','ic sm')}</button>`).join(''));offset=data.next_offset;if(offset!==null)list.insertAdjacentHTML('beforeend','<button class="btn wide" data-more-projects>More projects</button>');}catch(e){error(root,e.message);}finally{busy=false;}}
    root.addEventListener('click',e=>{const row=e.target.closest('[data-project-id]');if(row)open(row.dataset.projectId);if(e.target.closest('[data-more-projects]'))load();});
    load();
  }
});
const fields=p=>`<label>Project name<input name="name" maxlength="120" required autofocus value="${esc(p?.name||'')}" placeholder="For example, Moving home"></label><label>Shared context <small>optional</small><textarea name="context" maxlength="4000" rows="5" placeholder="Details you want chats in this project to use">${esc(p?.context||'')}</textarea></label>`;
registerPage('projects.new',{
  title:'New project',source:'A workspace for related work',
  render:()=>`<form class="task-form" data-project-form>${fields()}<p class="task-boundary">Shared context is used only when you chat within this project. Adding tasks never starts or sends them.</p><p role="alert" data-project-error hidden></p><button class="btn primary wide" type="submit">Create project</button></form>`,
  mount(root){const form=root.querySelector('form');const creation_key=key();let busy=false;form.onsubmit=async event=>{event.preventDefault();if(busy)return;busy=true;const button=form.querySelector('[type=submit]');button.disabled=true;try{const data=await post('/api/projects',{name:form.elements.name.value,context:form.elements.context.value,creation_key});changed();if(current(root))openPage('projects.detail',{id:data.project.id,focus:true},{replace:true});}catch(e){error(root,e.message);}finally{busy=false;if(button.isConnected)button.disabled=false;}};}
});

registerPage('projects.detail',{
  title:'Project',source:'Shared context and related work',render:()=>'<div data-project-detail><p role="status">Loading project…</p></div>',
  mount(root,context){
    let data=null,busy=false,newChatReference=null;const attempts=new Map();
    async function command(kind,params={},button){
      if(busy||!data)return null;busy=true;if(button)button.disabled=true;
      const signature=JSON.stringify({kind,...params,expected_revision:data.project.revision});
      if(!attempts.has(signature))attempts.set(signature,{kind,...params,expected_revision:data.project.revision,command_key:key()});
      try{const result=await post(projectUrl(context.id)+'/commands',attempts.get(signature));changed();return result;}
      catch(e){error(root,e.message);if(button?.isConnected)button.textContent='Retry change';return null;}
      finally{busy=false;if(button?.isConnected)button.disabled=false;}
    }
    async function load(){
      try{
        data=await api(projectUrl(context.id));if(!root.isConnected)return;const p=data.project,active=p.status==='ACTIVE';
        const local=new Map(listConversations().map(c=>[c.id,c]));
        data.chats=data.chats.map(chat=>({...chat,title:local.get(chat.id)?.title||chat.title}));
        root.querySelector('[data-project-detail]').innerHTML=`<div class="project-detail"><span class="task-state" data-project-state tabindex="-1" aria-live="polite">${active?(context.focus?'Project updated':'Active project'):'Archived'}</span><h3>${esc(p.name)}</h3>
          <section><h4>Shared context</h4><p class="project-context">${p.context?esc(p.context):'No shared context yet.'}</p><p class="task-boundary">Chats in this project use these notes. Edits affect future turns; earlier chat messages remain in history. Notes never authorize requests.</p>${active?'<button class="today-note" data-edit-project>Edit name or context</button>':''}</section>
          <section><header><h4>Chats</h4>${active?'<button class="today-note" data-new-project-chat>New chat</button>':''}</header>${data.chats.length?data.chats.map(c=>`<div class="project-member"><button data-open-project-chat="${esc(c.id)}" ${local.has(c.id)?'':'disabled'}><b>${esc(c.title)}</b><small>${local.has(c.id)?'Saved on this device':'Chat is not available on this device'}</small></button>${active?`<button class="today-note" data-unlink-chat="${esc(c.id)}" aria-label="Remove ${esc(c.title)} from project">Remove</button>`:''}</div>`).join(''):'<p class="today-quiet">Start a chat or add your current one.</p>'}${active?'<button class="today-note" data-add-current-chat>Add current chat</button>':''}</section>
          <section><header><h4>Tasks</h4>${active?'<button class="today-note" data-add-project-task>Add a task</button>':''}</header>${data.tasks.length?data.tasks.map(t=>`<div class="project-member"><button data-open-project-task="${esc(t.id)}"><b>${esc(t.outcome)}</b><small>${esc(taskStateLabel(t.status))}</small></button>${active?`<button class="today-note" data-unlink-task="${esc(t.id)}" aria-label="Remove ${esc(t.outcome)} from project">Remove</button>`:''}</div>`).join(''):'<p class="today-quiet">Your linked tasks will appear here.</p>'}<p class="task-boundary">Removing a link keeps the task and its history.</p></section>
          ${failure}<button class="today-note" data-project-archive>${active?'Archive project':'Restore project'}</button><p class="task-boundary">Archiving keeps your chats and tasks. It stops sharing project context until restored.</p></div>`;
        if(context.focus){root.querySelector('[data-project-state]')?.focus({preventScroll:true});context.focus=false;}
      }catch(e){root.querySelector('[data-project-detail]').innerHTML=`<p data-project-error role="alert">${esc(e.message)}</p><button class="btn wide" data-reload-project>Try again</button>`;}
    }
    root.addEventListener('click',async event=>{
      const button=event.target.closest('button');if(!button||!data)return;
      if(button.matches('[data-reload-project]')){attempts.clear();await load();return;}
      if(button.matches('[data-edit-project]')){openPage('projects.edit',{id:context.id,project:data.project});return;}
      if(button.matches('[data-add-project-task]')){openPage('projects.pick-task',{id:context.id,revision:data.project.revision});return;}
      if(button.matches('[data-open-project-task]')){openTask(button.dataset.openProjectTask);return;}
      if(button.matches('[data-open-project-chat]')){try{openConversation(button.dataset.openProjectChat);closeSheet();dispatchEvent(new CustomEvent('dubaiio:project-chat'));}catch(e){error(root,e.message);}return;}
      let result=null;
      if(button.matches('[data-new-project-chat]')){try{if(!newChatReference){startNewChat();newChatReference=identity().thread_id;}result=await command('add_chat',{thread_id:newChatReference,title:'New chat'},button);if(result){if(identity().thread_id===newChatReference)setConversationProject(context.id);closeSheet();dispatchEvent(new CustomEvent('dubaiio:project-chat'));}}catch(e){error(root,e.message);}return;}
      if(button.matches('[data-add-current-chat]')){const chat=listConversations().find(c=>c.active);result=await command('add_chat',{thread_id:identity().thread_id,title:chat?.title.slice(0,120)||'New chat'},button);}
      if(button.matches('[data-unlink-task]'))result=await command('remove_task',{task_id:button.dataset.unlinkTask},button);
      if(button.matches('[data-unlink-chat]'))result=await command('remove_chat',{thread_id:button.dataset.unlinkChat},button);
      if(button.matches('[data-project-archive]'))result=await command(data.project.status==='ACTIVE'?'archive':'restore',{},button);
      if(result&&root.isConnected){context.focus=true;await load();}
    });
    root.addEventListener('dubaiio:page-restored',()=>{context.focus=true;load();});load();
  }
});

registerPage('projects.edit',{
  title:'Edit project',source:'Review shared workspace context',render:c=>`<form class="task-form">${fields(c.project)}${failure}<button class="btn primary wide" type="submit">Save project</button></form>`,
  mount(root,context){const form=root.querySelector('form');let attempt=null,busy=false;root.querySelector('[data-reload-project]').onclick=()=>openPage('projects.detail',{id:context.id,focus:true},{replace:true});form.onsubmit=async e=>{e.preventDefault();if(busy)return;busy=true;const button=form.querySelector('[type=submit]');button.disabled=true;attempt||={kind:'edit',expected_revision:context.project.revision,command_key:key(),changes:{name:form.elements.name.value,context:form.elements.context.value}};try{await post(projectUrl(context.id)+'/commands',attempt);changed();if(current(root))openPage('projects.detail',{id:context.id,focus:true},{replace:true});}catch(errorValue){error(root,errorValue.message);form.elements.name.disabled=true;form.elements.context.disabled=true;button.textContent='Retry same changes';}finally{busy=false;if(button.isConnected)button.disabled=false;}};}
});

registerPage('projects.pick-task',{
  title:'Add a saved task',source:'Reference only · nothing starts or sends',render:()=>`<div data-project-task-options></div>${failure}`,
  mount(root,context){let offset=0,busy=false;const attempts=new Map();async function load(){try{const data=await api('/api/tasks?offset='+offset);if(!root.isConnected)return;const host=root.querySelector('[data-project-task-options]');host.querySelector('[data-more-task-options]')?.remove();host.insertAdjacentHTML('beforeend',data.tasks.map(t=>`<button class="project-list-row" data-link-task="${esc(t.id)}"><span><b>${esc(t.outcome)}</b><small>${esc(taskStateLabel(t.status))}</small></span>${svg('chev','ic sm')}</button>`).join('')||(!offset?'<p class="today-quiet">Save a task first, then add it to your project.</p>':''));offset=data.next_offset;if(offset!==null)host.insertAdjacentHTML('beforeend','<button class="btn wide" data-more-task-options>More tasks</button>');}catch(e){error(root,e.message);}}
    root.addEventListener('click',async e=>{const b=e.target.closest('button');if(!b||busy)return;if(b.matches('[data-reload-project]')){openPage('projects.detail',{id:context.id},{replace:true});return;}if(b.matches('[data-more-task-options]')){await load();return;}if(!b.matches('[data-link-task]'))return;busy=true;b.disabled=true;const id=b.dataset.linkTask;if(!attempts.has(id))attempts.set(id,{kind:'add_task',task_id:id,expected_revision:context.revision,command_key:key()});try{await post(projectUrl(context.id)+'/commands',attempts.get(id));changed();if(current(root))openPage('projects.detail',{id:context.id,focus:true},{replace:true});}catch(errorValue){error(root,errorValue.message);}finally{busy=false;if(b.isConnected)b.disabled=false;}});load();}
});
