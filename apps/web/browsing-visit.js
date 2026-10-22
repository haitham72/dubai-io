// Browsing visits expire while a tab remains open. Storage failure still keeps
// one in-memory visit; event and rank requests each capture their visit once.
export function createBrowsingVisit({ storage, now = Date.now, uuid = () => crypto.randomUUID() }) {
  const key = 'dubaiio.visit', idle = 30 * 60 * 1000, maximum = 24 * 60 * 60 * 1000;
  let visit;
  try { visit = JSON.parse(storage?.getItem(key) || 'null'); } catch { /* blocked storage */ }
  return () => {
    const at = now();
    if (!visit || typeof visit.id !== 'string' || !Number.isFinite(visit.at) || !Number.isFinite(visit.last) ||
        at < visit.last || at - visit.last >= idle || at - visit.at >= maximum) {
      visit = { id: uuid(), at, last: at };
    }
    visit.last = at;
    try { storage?.setItem(key, JSON.stringify(visit)); } catch { /* blocked storage */ }
    return visit.id;
  };
}
