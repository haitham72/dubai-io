import { apiPost } from "./api";

/** Live Google Places row — provenance is always provider_confirmed from the API. */
export interface Place {
  id?: string;
  name: string;
  rating?: number | null;
  ratings?: number | null;
  lat?: number | null;
  lng?: number | null;
  address?: string | null;
  short_address?: string | null;
  open_now?: boolean | null;
  maps_url?: string | null;
  photo?: string | null;
  photo_by?: string[];
  phone?: string | null;
  website?: string | null;
  provenance?: string;
}

export interface PlacesSearchResult {
  places: Place[];
  attribution: string;
  as_of: string;
  cache?: string;
}

export interface PlacesTurnSlots {
  intent?: string;
  category?: string | null;
  subcategory?: string | null;
  query?: string | null;
}

const CATEGORY_LABEL: Record<string, string> = {
  pets: "pet services",
  food: "restaurants",
  coffee: "coffee shops",
  barber: "barbers",
  "home-help": "home help",
  laundry: "laundry",
  clothing: "clothing stores",
  "fix-it": "home repair",
};

/** Dubai Marina — same bias as the API HOME center when the user has not shared a pin. */
export const MARINA = { lat: 25.0805, lng: 55.1403, label: "Dubai Marina" };

/** True when the ask is clearly “find places nearby” even if Luna misfires the intent. */
export function wantsNearbyPlaces(text: string, intent?: string): boolean {
  if (intent === "places_near") return true;
  return /\b(near(by)?|around|close to|open now)\b/i.test(text)
    && /\b(gyms?|fitness|coffee|cafes?|cafés?|restaurants?|vets?|barbers?|laundry|clinics?|pharmac(?:y|ies)|parks?|mosques?|schools?)\b/i.test(text);
}

/** Build the Places text query from Luna slots + the user's words. */
export function placesQueryFromTurn(slots: PlacesTurnSlots, userText: string): string {
  const specific = (slots.query || "").trim();
  if (specific) return `${specific} near ${MARINA.label}`;
  const cat = (slots.category || "").trim();
  const sub = (slots.subcategory || "").trim();
  if (cat && CATEGORY_LABEL[cat]) {
    const base = sub ? `${sub} ${CATEGORY_LABEL[cat]}` : CATEGORY_LABEL[cat];
    return `${base} near ${MARINA.label}`;
  }
  const clipped = userText.replace(/\s+/g, " ").trim().slice(0, 80);
  if (!clipped) return `places near ${MARINA.label}`;
  if (/\bmarina\b|\bdubai\b/i.test(clipped)) return clipped;
  return `${clipped} near ${MARINA.label}`;
}

export function searchPlaces(
  query: string,
  center: { lat: number; lng: number } = MARINA,
): Promise<PlacesSearchResult> {
  return apiPost<PlacesSearchResult>("/api/places/search", {
    query: query.slice(0, 120),
    lat: center.lat,
    lng: center.lng,
  });
}

/** Jumeirah Lakes Towers — school-run bias for KHDA shortlist. */
export const JLT = { lat: 25.0693, lng: 55.1415, label: "JLT" };

export function mapsHref(url: string | null | undefined): string | null {
  if (!url || !/^https:\/\/(www\.)?google\.com\/maps\b|^https:\/\/maps\.google\.com\b|^https:\/\/maps\.app\.goo\.gl\b/i.test(url)) {
    return null;
  }
  return url;
}
