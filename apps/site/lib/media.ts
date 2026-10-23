/**
 * Stock photographs copied from apps/web/media. Source URL and licence are
 * recorded in apps/web/media.json (Unsplash License, provenance: stock) and
 * in public/IMAGE_LICENSES.md. They are illustrative, never presented as a
 * specific Dubai venue, provider or person.
 */
export interface MediaEntry {
  subject: string;
  sourceUrl: string;
}

export const MEDIA: Record<string, MediaEntry> = {
  "marina.jpg": { subject: "Dubai Marina at night, dhows lit on the water", sourceUrl: "https://images.unsplash.com/photo-1761341063556-80cb742411b6" },
  "home.jpg": { subject: "Bright living room (home help, maid hire)", sourceUrl: "https://images.unsplash.com/photo-1631510390389-c1e4fb20ff31" },
  "food.jpg": { subject: "Hummus and flatbread flat-lay", sourceUrl: "https://images.unsplash.com/photo-1697126248437-db26a30024c5" },
  "pets.jpg": { subject: "A small white dog being groomed with scissors", sourceUrl: "https://images.unsplash.com/photo-1719464454959-9cf304ef4774" },
  "barber.jpg": { subject: "Barber trimming a beard", sourceUrl: "https://images.unsplash.com/photo-1599011176306-4a96f1516d4d" },
  "coffee.jpg": { subject: "Espresso pouring from a portafilter", sourceUrl: "https://images.unsplash.com/photo-1609050471053-8636409f9f5b" },
  "cloth.jpg": { subject: "Rack of cyan and pastel t-shirts", sourceUrl: "https://images.unsplash.com/photo-1657651315305-a1b608182927" },
  "airport-plane.jpg": { subject: "Plane taking off at sunset over an airport apron (unbranded)", sourceUrl: "https://images.unsplash.com/photo-1583150647472-d239652a12f5" },
  "cafe-counter.jpg": { subject: "Modern coffee shop with a curved counter", sourceUrl: "https://images.unsplash.com/photo-1567880905822-56f8e06fe630" },
  "cafe-bulbs.jpg": { subject: "Cafe interior with hanging bulbs", sourceUrl: "https://images.unsplash.com/photo-1511081692775-05d0f180a065" },
  "rest-water.jpg": { subject: "Restaurant with a view of the water", sourceUrl: "https://images.unsplash.com/photo-1559339352-11d035aa65de" },
  "rest-room.jpg": { subject: "Restaurant interior", sourceUrl: "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4" },
  "shawarma.jpg": { subject: "Beef shawarma", sourceUrl: "https://images.unsplash.com/photo-1529006557810-274b9b2fc783" },
  "spread.jpg": { subject: "Middle Eastern spread on a table", sourceUrl: "https://images.unsplash.com/photo-1748540459503-19efc015143b" },
  "grill.jpg": { subject: "Mixed grill platter", sourceUrl: "https://images.unsplash.com/photo-1555939594-58d7cb561ad1" },
  "vet.jpg": { subject: "Veterinarian examining a dachshund", sourceUrl: "https://images.unsplash.com/photo-1770836037793-95bdbf190f71" },
  "puppy.jpg": { subject: "Pomeranian puppy on a blue blanket", sourceUrl: "https://images.unsplash.com/photo-1588626863948-1d7978596f17" },
  "laundry.jpg": { subject: "Stack of folded shirts", sourceUrl: "https://images.unsplash.com/photo-1635274605638-d44babc08a4f" },
  "laundry-shelf.jpg": { subject: "Shelf of folded shirts", sourceUrl: "https://images.unsplash.com/photo-1700659392887-0a026c53f8e2" },
  "ac.jpg": { subject: "Wall air conditioner at 22 degrees", sourceUrl: "https://images.unsplash.com/photo-1762341123870-d706f257a12e" },
  "barber-dark.jpg": { subject: "Barber at work, low light", sourceUrl: "https://images.unsplash.com/photo-1503951914875-452162b0f3f1" },
  "home-green.jpg": { subject: "Bright living room with green cushions", sourceUrl: "https://images.unsplash.com/photo-1615800002234-05c4d488696c" },
  "shoes.jpg": { subject: "Espadrilles and a straw hat", sourceUrl: "https://images.unsplash.com/photo-1565953198075-db265882ee68" },
  "marina-night.jpg": { subject: "Dubai Marina towers at night", sourceUrl: "https://images.unsplash.com/photo-1527354711091-dfe0e5f699be" },
};

/** Map an API image path such as "media/coffee.jpg" to the local copy. */
export function mediaSrc(path?: string | null): string | null {
  if (!path) return null;
  const name = path.replace(/^\/?media\//, "");
  return name in MEDIA ? `/images/media/${name}` : null;
}

export function mediaSubject(path?: string | null): string {
  if (!path) return "";
  const name = path.replace(/^\/?media\//, "");
  return MEDIA[name]?.subject ?? "";
}
