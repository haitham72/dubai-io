/** On-device coarse snap — raw lat/lng never leave the browser (S3). */

const DUBAI_AREAS: Record<string, { lat: number; lng: number }> = {
  "Dubai Marina": { lat: 25.0805, lng: 55.1403 },
  JLT: { lat: 25.0721, lng: 55.1463 },
  DIFC: { lat: 25.212, lng: 55.2806 },
  "Downtown Dubai": { lat: 25.1972, lng: 55.2744 },
  "Business Bay": { lat: 25.1851, lng: 55.2665 },
  Jumeirah: { lat: 25.2084, lng: 55.247 },
  "Al Quoz": { lat: 25.1372, lng: 55.2289 },
  Deira: { lat: 25.2713, lng: 55.3175 },
  "Bur Dubai": { lat: 25.2528, lng: 55.2974 },
  "Palm Jumeirah": { lat: 25.1124, lng: 55.139 },
  "Internet City": { lat: 25.0956, lng: 55.1561 },
};

function haversineKm(aLat: number, aLng: number, bLat: number, bLng: number): number {
  const toRad = (d: number) => (d * Math.PI) / 180;
  const dLat = toRad(bLat - aLat);
  const dLng = toRad(bLng - aLng);
  const lat1 = toRad(aLat);
  const lat2 = toRad(bLat);
  const h =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) ** 2;
  return 6371 * 2 * Math.asin(Math.min(1, Math.sqrt(h)));
}

/** Snap browser coordinates to the nearest Dubai district label. */
export function snapCoordinatesToArea(lat: number, lng: number): string {
  let best = "Downtown Dubai";
  let bestDist = Number.POSITIVE_INFINITY;
  for (const [name, c] of Object.entries(DUBAI_AREAS)) {
    const d = haversineKm(lat, lng, c.lat, c.lng);
    if (d < bestDist) {
      bestDist = d;
      best = name;
    }
  }
  return best;
}
