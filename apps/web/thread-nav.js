import { openPage } from './page-host.js';
// Threads open in the slide-in panel; community threads open their community.
export function openThread(t, onClose) {
  const title = t.title || t.name;
  return t.community_id ? openPage('feed.community', { id: t.community_id, title }) : openPage('chat.thread', { id: t.id, title, onClose });
}
