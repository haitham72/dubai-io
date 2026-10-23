// Pure logic for full-height slide-in panels: hash routes and the panel stack.
// Kept free of DOM access so it can be tested in node.
export const ROUTES = [
  { page: 'chat.thread', prefix: 'chat/thread', id: true, parent: 'hub', probe: id => '/api/chats/' + encodeURIComponent(id) + '/messages' },
  { page: 'feed.community', prefix: 'chat/community', id: true, parent: 'hub', probe: id => '/api/feed?limit=1&community_id=' + encodeURIComponent(id) },
  { page: 'feed.post', prefix: 'feed/post', id: true, parent: 'feed', probe: id => '/api/posts/' + encodeURIComponent(id) },
  { page: 'settings', prefix: 'settings', id: false, parent: 'home' },
];
export const isPanelPage = page => ROUTES.some(r => r.page === page);
export function panelHash(page, ctx = {}) {
  const r = ROUTES.find(x => x.page === page); if (!r) return '';
  if (!r.id) return '#' + r.prefix;
  return ctx.id ? '#' + r.prefix + '/' + encodeURIComponent(ctx.id) : '';
}
export function parsePanelHash(hash) {
  const text = String(hash || '').replace(/^#/, '');
  for (const r of ROUTES) {
    if (!r.id && text === r.prefix) return { route: r, ctx: {} };
    if (r.id && text.startsWith(r.prefix + '/')) {
      let id; try { id = decodeURIComponent(text.slice(r.prefix.length + 1)); } catch { return null; }
      if (id && !id.includes('/')) return { route: r, ctx: { id } };
    }
  }
  return null;
}
export function createStack() {
  const items = [];
  return {
    push: e => (items.push(e), items.length),
    pop: () => items.pop(),
    get top() { return items.at(-1); },
    get size() { return items.length; },
    items,
  };
}
