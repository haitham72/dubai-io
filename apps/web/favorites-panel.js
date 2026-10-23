// Favorites slide-in panel (#chat/favorites): contacts and chats you call or open in one tap.
// Device-local (localStorage), ordered. Video buttons never simulate a call.
import { esc, svg, toast } from './ui.js';
import { api } from './service-workflow.js';
import { registerPage } from './page-host.js';
import { avatar } from './social-ui.js';
import { createFavorites, resolveFavorites, threadFav } from './chat-logic.js';
import { openThread } from './thread-nav.js';
import { startCall } from './calls-view.js';

registerPage('chat.favorites', {
  title: 'Favorites', source: 'Saved on this device',
  render: () => `<div class="fav-panel" data-fav-root><p role="status" class="today-quiet">Loading…</p></div>`,
  mount(root) {
    const fav = createFavorites(localStorage), bar = root.closest('.panel')?.querySelector('.panel-bar');
    let contacts = [], threads = [], editing = false, adding = false, loaded = false;
    const edit = document.createElement('button'); edit.className = 'btn sm panel-edit'; edit.textContent = 'Edit'; bar?.append(edit);
    const box = root.querySelector('[data-fav-root]');
    const av = f => f.type === 'thread' ? avatar({ avatar: f.avatar, name: f.name }, 't-avatar') : `<span class="t-avatar" aria-hidden="true">${esc((f.name.trim()[0] || '·').toUpperCase())}</span>`;
    function render() {
      edit.textContent = editing ? 'Done' : 'Edit'; edit.hidden = adding;
      if (adding) {
        const favIds = new Set(fav.list());
        const people = contacts.filter(c => !favIds.has(c.id)), groups = threads.filter(t => !favIds.has(threadFav(t.id)));
        const pick = (id, name, av2, sub) => `<div class="fav-row">${av2}<span class="t-copy"><b>${esc(name)}</b><span class="sub">${sub}</span></span><button class="round" data-pick="${esc(id)}" aria-label="Add ${esc(name)}">${svg('plus')}</button></div>`;
        box.innerHTML = `<div class="fav-head"><b>Add people or groups</b><button class="btn sm" data-done-add>Done</button></div><h4>People</h4>${people.map(c => pick(c.id, c.name, `<span class="t-avatar" aria-hidden="true">${esc((c.name.trim()[0] || '·').toUpperCase())}</span>`, esc(c.phone))).join('') || '<p class="today-quiet">No contacts to add. Add one under Calls › Add.</p>'}<h4>Chats and groups</h4>${groups.map(t => pick(threadFav(t.id), t.title, avatar({ avatar: t.avatar, name: t.title }, 't-avatar'), '<span class="pill demo sm">Demo</span>')).join('') || '<p class="today-quiet">Nothing else to add.</p>'}`;
        return;
      }
      const list = resolveFavorites(fav.list(), contacts, threads);
      box.innerHTML = `<button class="fav-add" data-add><span class="round">${svg('plus')}</span><b>Add people or groups</b></button>
        <div class="fav-list">${list.map((f, i) => `<div class="fav-row" data-id="${esc(f.id)}">${editing ? `<button class="minus" data-remove="${esc(f.id)}" aria-label="Remove ${esc(f.name)} from favorites">&minus;</button>` : ''}${av(f)}<span class="t-copy"><b>${esc(f.name)}${f.type === 'thread' ? ' <span class="pill demo sm">Demo</span>' : ''}</b>${f.phone ? `<span class="sub">${esc(f.phone)}</span>` : ''}</span>${editing
          ? `<button class="round" data-move="-1" data-id="${esc(f.id)}" aria-label="Move ${esc(f.name)} up" ${i === 0 ? 'disabled' : ''}>${svg('up2')}</button><button class="round" data-move="1" data-id="${esc(f.id)}" aria-label="Move ${esc(f.name)} down" ${i === list.length - 1 ? 'disabled' : ''}><span class="flip">${svg('up2')}</span></button>`
          : `<button class="round" data-phone="${esc(f.id)}" aria-label="${f.type === 'contact' ? 'Call' : 'Open chat with'} ${esc(f.name)}">${svg('phone')}</button><button class="round" data-video aria-label="Video call ${esc(f.name)}">${svg('video')}</button>`}</div>`).join('')}</div>
        ${loaded && !list.length ? '<p class="today-quiet">No favorites yet.</p>' : ''}
        <p class="fine">Favorite your contacts or groups to reach them with one tap, like speed dial.</p><p class="fine">Edit favorites here to remove them or change the order they appear in under Calls.</p>`;
    }
    edit.addEventListener('click', () => { editing = !editing; render(); });
    box.addEventListener('click', async e => {
      const b = e.target.closest('button'); if (!b) return;
      if (b.hasAttribute('data-add')) { adding = true; render(); return; }
      if (b.hasAttribute('data-done-add')) { adding = false; render(); return; }
      if (b.dataset.pick) { fav.add(b.dataset.pick); render(); return; }
      if (b.dataset.remove) { fav.remove(b.dataset.remove); render(); return; }
      if (b.dataset.move) { fav.move(b.dataset.id, Number(b.dataset.move)); render(); return; }
      if (b.hasAttribute('data-video')) { toast('Video calls are coming later.'); return; }
      if (b.dataset.phone) {
        const f = resolveFavorites([b.dataset.phone], contacts, threads)[0]; if (!f) return;
        try { if (f.type === 'thread') openThread({ ...f.thread, title: f.name }); else await startCall({ contactId: f.contact.id }); }
        catch (err) { toast(err.message); }
      }
    });
    render();
    Promise.all([api('/api/contacts'), api('/api/chats?filter=all')]).then(([p, c]) => { contacts = p.contacts || []; threads = c.threads || []; loaded = true; render(); })
      .catch(() => { loaded = true; render(); toast('Favorites could not load.'); });
  },
});
