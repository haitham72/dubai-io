// Transient display snapshots only. Keep a visible list stable while observing
// feedback; refresh on deliberate navigation/filter changes. Corrections clear
// snapshots and prevent both old requests and overlapping mutations restoring them.
export function createDiscoveryCache(load) {
  let epoch = 0, paused = 0;
  const entries = new Map();
  return {
    get: key => entries.get(key),
    invalidate() { epoch++; entries.clear(); },
    pause() { paused++; epoch++; entries.clear(); },
    resume() { paused = Math.max(0, paused - 1); epoch++; },
    async refresh(key, input, force = false) {
      if (paused) return false;
      if (!force && entries.has(key)) return false;
      const generation = epoch, entry = { status: 'loading' };
      entries.set(key, entry);
      if (entries.size > 16) entries.delete(entries.keys().next().value);
      try {
        const data = await load(input);
        if (generation !== epoch || paused || entries.get(key) !== entry) return false;
        entries.set(key, { status: 'ok', ...data });
      } catch {
        if (generation !== epoch || paused || entries.get(key) !== entry) return false;
        entries.set(key, { status: 'error' });
      }
      return true;
    },
  };
}
