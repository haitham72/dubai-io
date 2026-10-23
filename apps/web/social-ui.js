import { esc } from './ui.js';

export function avatar(person, className = 'p-avatar') {
  const url = typeof person?.avatar === 'string' && /^(https:\/\/|\/media\/)/.test(person.avatar) ? person.avatar : '';
  return `<span class="${className}" aria-hidden="true">${url ? `<img src="${esc(url)}" alt="" loading="lazy" referrerpolicy="no-referrer">` : esc(person?.emoji || (person?.name || '?').slice(0, 1))}</span>`;
}
export function generationText(result) {
  const g = result?.generation;
  if (!g) return 'Saved.';
  if (g.status === 'completed') return `Saved · ${g.reply_count || 0} AI persona replies.`;
  if (g.status === 'processing') return 'Saved. AI replies are still processing; reopen to check.';
  return 'Saved. AI replies are unavailable right now.';
}
// Keep the same ID when a network timeout leaves the result uncertain.
export function socialRequest() {
  let previous = '', id;
  const build = body => {
    const key = JSON.stringify(body);
    if (key !== previous) { previous = key; id = crypto.randomUUID(); }
    return { method: 'POST', signal: AbortSignal.timeout(180000), body: JSON.stringify({ ...body, request_id: id }) };
  };
  build.reset = () => { previous = ''; };
  return build;
}
export function commentTree(comments) {
  const ids = new Set(comments.map(m => m.id)), children = new Map();
  comments.forEach(m => { const parent = ids.has(m.parent_id) && m.parent_id !== m.id ? m.parent_id : null; if (!children.has(parent)) children.set(parent, []); children.get(parent).push(m); });
  const seen = new Set();
  const render = (m, depth) => {
    if (seen.has(m.id)) return ''; seen.add(m.id);
    return `<li data-comment-id="${esc(m.id)}"><div class="comment-row">${avatar(m.author)}<div class="comment-copy"><b>${esc(m.author.name)}</b>${m.mine ? '' : ' <span class="pill demo">AI demo</span>'}${m.analysis?.harsh ? ' <span class="pill warn">Heated</span>' : ''}<p>${esc(m.text)}</p><button data-reply="${esc(m.id)}" data-author="${esc(m.author.name)}">Reply</button>${voteBox(m.id, 'comment', m.score ?? m.likes ?? 0, m.my_vote)}</div></div>${children.has(m.id) ? `<ol class="comments replies${depth >= 2 ? ' deep' : ''}">${children.get(m.id).map(x => render(x, depth + 1)).join('')}</ol>` : ''}</li>`;
  };
  let html = (children.get(null) || []).map(m => render(m, 0)).join('');
  html += comments.filter(m => !seen.has(m.id)).map(m => render(m, 0)).join('');
  return html;
}

export function filterCallPeople(people, query, favorites = null) {
  const text = String(query).trim().toLowerCase();
  return people.filter(p => (p.name + ' ' + p.phone).toLowerCase().includes(text) && (!favorites || favorites.has(p.id)));
}
export function voteBox(id, kind, score, mine) {
  return `<span class="votes" data-votes="${esc(String(id))}" data-kind="${kind}" data-mine="${mine || 0}"><button data-vote="1" aria-label="Upvote">▲</button><b>${score ?? 0}</b><button data-vote="-1" aria-label="Downvote">▼</button></span>`;
}
export function paintVotes(box, result) {
  box.dataset.mine = result.my_vote;
  box.querySelector('b').textContent = result.score;
}
