// Feed tab: Reddit-like community discovery with a Snapchat-style stories rail.
// Seeded people, communities and comments are demo data and labelled; posts are
// members' words, never instructions to the assistant.
import { esc, svg, toast } from './ui.js';
import { api } from './service-workflow.js';
import { registerPage, openPage } from './page-host.js';
import { ago } from './hub.js';
import { openStories } from './stories.js';

const fmt = n => n >= 1000 ? (n / 1000).toFixed(n >= 10000 ? 0 : 1) + 'k' : String(n);

export function postCardHTML(p) {
  return `<article class="post" data-post="${esc(p.id)}">
    <header><span class="p-avatar" aria-hidden="true">${esc(p.author.emoji)}</span><span><b>${esc(p.author.name)}</b> <small>@${esc(p.author.handle)}</small><span class="p-where">${esc(p.community.name)} · ${ago(p.created_at)}</span></span>${p.provenance === 'demo_fixture' ? '<span class="pill demo">Demo</span>' : ''}</header>
    <p class="p-text">${esc(p.text)}</p>
    ${p.image ? `<img class="p-img" src="${esc(p.image)}" alt="" loading="lazy">` : ''}
    <footer><span>♥ ${fmt(p.likes)}</span><button data-open-post="${esc(p.id)}">💬 ${fmt(p.comments)} comments</button><button data-hide-post="${esc(p.id)}" aria-label="Hide this post">Hide</button></footer>
  </article>`;
}

export function createFeed(root, { openMe }) {
  let data = null, communities = [], generation = 0;
  function render() {
    const posts = data?.posts || [], stories = data?.stories || [];
    const discover = communities.filter(c => !c.joined);
    root.innerHTML = `<header class="tab-head"><h1>Feed</h1><div><button class="round" data-compose aria-label="New post">${svg('plus')}</button><button class="round" data-me aria-label="Your profile">${svg('person')}</button></div></header>
      ${stories.length ? `<div class="stories-rail" role="list" aria-label="Stories">${stories.map(s => `<button role="listitem" class="story-dot" data-story="${esc(s.community.id)}"><span class="ring"><img src="${esc(s.image)}" alt=""></span><small>${esc(s.community.name)}</small></button>`).join('')}</div>` : ''}
      ${discover.length ? `<section class="discover"><h2>Communities for you</h2><div class="discover-row">${discover.map(c => `<div class="community-chip"><img src="${esc(c.image)}" alt=""><b>${esc(c.name)}</b><small>${fmt(c.members)} members · ${esc(c.topic)}</small><button class="btn sm" data-join="${esc(c.id)}">Join</button></div>`).join('')}</div></section>` : ''}
      <section class="posts">${posts.map(postCardHTML).join('') || (data ? '<p class="today-quiet">No posts yet.</p>' : '<p role="status">Loading the feed…</p>')}</section>
      <p class="fine tab-fine">People, communities and comments here are demo data in this preview. Report or hide anything you don’t want to see.</p>`;
  }
  async function load() {
    const mine = ++generation;
    try {
      const [f, c] = await Promise.all([api('/api/feed?limit=40'), api('/api/communities')]);
      if (mine === generation) { data = f; communities = c.communities; render(); }
    } catch { if (mine === generation) { data = { posts: [], stories: [] }; render(); toast('The feed could not load.'); } }
  }
  root.addEventListener('click', async e => {
    const b = e.target.closest('button');
    const card = e.target.closest('[data-post]');
    if (!b && card) return openPage('feed.post', { id: card.dataset.post, onChange: load });
    if (!b) return;
    if (b.hasAttribute('data-me')) return openMe();
    if (b.dataset.story) return openStories(b.dataset.story);
    if (b.dataset.openPost) return openPage('feed.post', { id: b.dataset.openPost, onChange: load });
    if (b.hasAttribute('data-compose')) return openPage('feed.compose', { communities: communities.filter(c => c.joined), onChange: load });
    try {
      if (b.dataset.join) { b.disabled = true; await api('/api/communities/' + encodeURIComponent(b.dataset.join) + '/join', { method: 'POST' }); toast('Joined. Its chat is in Chat › Communities.'); dispatchEvent(new CustomEvent('dubaiio:chats-changed')); load(); }
      if (b.dataset.hidePost) { await api('/api/posts/' + encodeURIComponent(b.dataset.hidePost) + '/hide', { method: 'POST', body: JSON.stringify({ reason: 'not_for_me' }) }); toast('Hidden from your feed.'); load(); }
    } catch (err) { toast(err.message); b.disabled = false; }
  });
  render();
  return { show(visible) { if (visible) load(); }, reload: load };
}

registerPage('feed.post', {
  title: 'Post', source: 'Community · members’ words',
  render: () => '<div data-post-view><p role="status">Loading…</p></div>',
  mount(root, c) {
    const view = root.querySelector('[data-post-view]');
    async function load() {
      try {
        const [{ posts }, { comments }] = await Promise.all([api('/api/feed?limit=50'), api('/api/posts/' + encodeURIComponent(c.id) + '/comments')]);
        const post = posts.find(p => p.id === c.id);
        view.innerHTML = `${post ? postCardHTML(post) : ''}<h3 class="comments-head">${comments.length} comments</h3>
          <ol class="comments">${comments.map(m => `<li><span class="p-avatar" aria-hidden="true">${esc(m.author.emoji)}</span><div><b>${esc(m.author.name)}</b> <small>${ago(m.created_at)}${m.likes ? ' · ♥ ' + m.likes : ''}</small><p>${esc(m.text)}</p></div></li>`).join('')}</ol>
          <form class="thread-compose" data-comment><label class="sr" for="commentText">Add a comment</label><input id="commentText" maxlength="500" placeholder="Add a comment" autocomplete="off"><button class="btn primary" type="submit">Post</button></form>`;
      } catch { view.innerHTML = '<p role="alert">This post could not load.</p>'; }
    }
    root.addEventListener('submit', async e => {
      if (!e.target.matches('[data-comment]')) return;
      e.preventDefault();
      const input = root.querySelector('#commentText'), text = input.value.trim(); if (!text) return;
      try { await api('/api/posts/' + encodeURIComponent(c.id) + '/comments', { method: 'POST', body: JSON.stringify({ text }) }); await load(); c.onChange?.(); root.querySelector('.comments li:last-child')?.scrollIntoView({ block: 'nearest' }); }
      catch (err) { toast(err.message); }
    });
    load();
  },
});

registerPage('feed.compose', {
  title: 'New post', source: 'Shared with the community',
  render: c => c.communities.length
    ? `<form class="contact-add" data-new-post><label>Community<select name="community">${c.communities.map(x => `<option value="${esc(x.id)}">${esc(x.name)}</option>`).join('')}</select></label><label>What’s on your mind?<textarea name="text" rows="4" maxlength="500" required></textarea></label><button class="btn primary wide" type="submit">Post</button><p class="fine">In this preview only you see your posts; other members are demo data.</p></form>`
    : '<p class="today-quiet">Join a community first, then you can post to it.</p>',
  mount(root, c) {
    root.querySelector('[data-new-post]')?.addEventListener('submit', async e => {
      e.preventDefault();
      const f = new FormData(e.target);
      try { await api('/api/communities/' + encodeURIComponent(f.get('community')) + '/posts', { method: 'POST', body: JSON.stringify({ text: f.get('text') }) }); toast('Posted.'); c.onChange?.(); document.querySelector('#sheetClose')?.click(); }
      catch (err) { toast(err.message); }
    });
  },
});
