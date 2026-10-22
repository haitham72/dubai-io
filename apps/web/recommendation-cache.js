// A profile correction invalidates both saved results and requests already in flight.
export function createRecommendationCache(load) {
  let epoch = 0, suspended = 0, ranks = new Map();
  return {
    get: id => ranks.get(id),
    invalidate() { epoch++; ranks.clear(); },
    pause() { suspended++; epoch++; ranks.clear(); },
    resume() { suspended = Math.max(0, suspended - 1); epoch++; },
    async refresh(input) {
      if (suspended) return false;
      const generation = ++epoch;
      try {
        const data = await load(input);
        if (generation !== epoch || suspended) return false;
        ranks = new Map(data.results.map(row => [row.id, row]));
        return true;
      } catch { return false; }
    },
  };
}
