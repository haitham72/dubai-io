import { MARINA } from "./places";

export type UserLocation = {
  lat: number;
  lng: number;
  label: string;
  source: "device" | "fallback";
};

/** Prefer the device location; Marina only if permission fails or times out. */
export function detectUserLocation(timeoutMs = 10000): Promise<UserLocation> {
  if (typeof navigator === "undefined" || !navigator.geolocation) {
    return Promise.resolve({
      lat: MARINA.lat,
      lng: MARINA.lng,
      label: "Dubai Marina (default)",
      source: "fallback",
    });
  }
  return new Promise((resolve) => {
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        resolve({
          lat: pos.coords.latitude,
          lng: pos.coords.longitude,
          label: "Your location",
          source: "device",
        });
      },
      () => {
        resolve({
          lat: MARINA.lat,
          lng: MARINA.lng,
          label: "Dubai Marina (location unavailable)",
          source: "fallback",
        });
      },
      { enableHighAccuracy: true, timeout: timeoutMs, maximumAge: 60_000 },
    );
  });
}

export function placePhotoUrl(photoName: string | null | undefined, w = 320): string | null {
  if (!photoName || !photoName.startsWith("places/")) return null;
  return `/api/places/photo?name=${encodeURIComponent(photoName)}&w=${w}`;
}
