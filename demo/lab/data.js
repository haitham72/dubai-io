// Lab fixtures. Everything here is demo data (provenance: demo_fixture).
// Cases mirror demo/_ref/services/cases.md; categories are the registry behind
// the Services surface (a new category is a row here, not code).

export const PALETTES = {
  // sRGB hex; converted to linear light in gl.js.
  // ramp: dark -> light body of every shader band. fringe: thin-film edge colours.
  cyan: {
    ramp: ['#04293A', '#07607D', '#0A9CC2', '#79D2E8', '#E3F6FB'],
    fringe: ['#2FC4E6', '#6C7BEA', '#8E44AD'],
    chroma: 0,
    bg: '#F3F6F8',
  },
  chromatic: {
    ramp: ['#0E0730', '#3A16B0', '#C0168C', '#FF6B3D', '#FFEBDD'],
    fringe: ['#20D3FF', '#9B5CFF', '#FF4FA3'],
    chroma: 1,
    bg: '#F4F3F7',
  },
};

// Card kinds map to shader variants in shaders.js.
export const ONBOARDING = [
  {
    id: 'o1', kind: 'silk', eyebrow: 'Dubai-io', title: "I'm Dubai-io.",
    body: 'A companion for living in Dubai. I remember what matters to you, I follow through with local shops, and I show you what I am doing.',
    meta: ['[Companion]', '[1 / 4]'], next: 'Next',
  },
  {
    id: 'o2', kind: 'photo', img: 'media/marina.jpg', eyebrow: 'Memory', title: 'Tell me once.',
    body: 'Your area, your deadlines, the places you like. I keep them, and you can see, change or forget every one.',
    meta: ['[You told me]', '[2 / 4]'], next: 'Next',
  },
  {
    id: 'o3', kind: 'photo', img: 'media/home.jpg', eyebrow: 'Agents', title: 'I send agents. You approve.',
    body: 'They check providers in parallel and come back with one thing for you to approve. Nothing leaves your phone before that.',
    meta: ['[Parallel]', '[3 / 4]'], next: 'Next',
  },
  {
    id: 'o4', kind: 'foil', eyebrow: 'Prices', title: 'Published prices. Never haggled.',
    body: 'Every price is the one the shop published. Offers are the shop’s own. Nothing is invented, nothing is negotiated.',
    meta: ['[Fixed]', '[4 / 4]'], next: 'Start',
  },
];

// "Try" cards on Home come from the services list. Only cases with lab media.
export const CASES = [
  { id: 'C1', kind: 'photo', holo: 0.55, img: 'media/home.jpg', category: 'home-help',
    eyebrow: 'Try · C1', title: '“A new maid with visa, before 1 Nov.”',
    body: 'Three agents check maids, offices and visa services at once. From AED 7,443 (demo).',
    meta: ['[3 lanes]', '[idea]'], caption: 'Best price wears foil. Fastest wears aluminium.' },
  { id: 'C13', kind: 'photo', img: 'media/food.jpg', category: 'food',
    eyebrow: 'Try · C13', title: '“I’m craving koshari.”',
    body: 'Make it, watch it, go there or get it delivered, ordered by what you usually do at this hour.',
    meta: ['[4 answers]', '[idea]'], because: 'order_in_weeknight' },
  { id: 'C12', kind: 'photo', img: 'media/pets.jpg', category: 'pets',
    eyebrow: 'Try · C12', title: '“Grooming and a check-up this week.”',
    body: 'One ask, two providers, one route. Vets, 24h, grooming and boarding on one map.',
    meta: ['[Bundle]', '[idea]'], caption: 'Opens the Services map on Pets.' },
  { id: 'C3', kind: 'photo', img: 'media/barber.jpg', category: 'barber',
    eyebrow: 'Try · C3', title: '“I need a haircut.”',
    body: 'Nearby shops by rating, see the style on you, add a beard trim, the shop’s own bundle applies.',
    meta: ['[AED 90 (demo)]', '[idea]'], caption: 'Cut + beard: 110 → 90, the shop’s published bundle.' },
  { id: 'C2', kind: 'photo', img: 'media/cloth.jpg', category: 'clothing',
    eyebrow: 'Try · C2', title: '“A summer outfit.”',
    body: 'Browse by who and what, not by shop. Try it on from a photo; the preview is labelled AI.',
    meta: ['[Try it on]', '[idea]'] },
  { id: 'C11', kind: 'photo', img: 'media/coffee.jpg', category: 'coffee',
    eyebrow: 'Try · C11', title: 'Share a coffee video.',
    body: 'I read the frames and the voice-over, find the places, and pin them on a map.',
    meta: ['[Video → map]', '[idea]'], because: 'specialty_coffee' },
];

export const PROFILE_CARD = {
  id: 'you', kind: 'mesh', eyebrow: 'Profile', title: 'You, over time',
  body: '', meta: ['[Visible]', '[Forgettable]'], caption: 'Everything I believe about you, with the evidence. Tap to open.',
};

// ---------- Services surface ----------
// glyph ids map to SVG paths in app.js. keywords let the search route any ask.
export const CATEGORIES = [
  { id: 'pets', group: 'service', label: 'Pets', glyph: 'paw', case: 'C12',
    subs: ['Vet', '24h', 'Pet shop', 'Boarding', 'Grooming', 'Photo'],
    keywords: ['pet', 'dog', 'cat', 'puppy', 'vet', 'groom', 'boarding', 'kennel'] },
  { id: 'food', group: 'shops', label: 'Food', glyph: 'fork', case: 'C13',
    subs: ['Restaurants', 'Delivery'],
    keywords: ['food', 'eat', 'hungry', 'koshari', 'restaurant', 'lunch', 'dinner', 'shawarma', 'hummus'] },
  { id: 'coffee', group: 'shops', label: 'Coffee', glyph: 'cup', case: 'C11',
    subs: [], keywords: ['coffee', 'latte', 'espresso', 'cafe', 'flat white'] },
  { id: 'barber', group: 'service', label: 'Barber', glyph: 'scissors', case: 'C3',
    subs: [], keywords: ['haircut', 'barber', 'beard', 'fade', 'hair'] },
  { id: 'home-help', group: 'service', label: 'Home help', glyph: 'home', case: 'C1',
    subs: ['Maid', 'Cleaning', 'Visa services'], keywords: ['maid', 'nanny', 'cleaner', 'housekeeper', 'visa', 'helper'] },
  { id: 'laundry', group: 'service', label: 'Laundry', glyph: 'drop', case: 'C4',
    subs: [], keywords: ['laundry', 'iron', 'press', 'dry clean', 'wash'] },
  { id: 'clothing', group: 'shops', label: 'Clothing', glyph: 'bag', case: 'C2',
    subs: [], keywords: ['clothes', 'outfit', 'shirt', 'dress', 'shoes', 'fashion'] },
  { id: 'fix-it', group: 'service', label: 'Fix it', glyph: 'wrench', case: 'C8',
    subs: ['AC', 'Plumbing', 'Electrical'], keywords: ['ac', 'fix', 'plumber', 'leak', 'electric', 'repair', 'broken'] },
];

// x, y are positions on the stylised lab map (0..1). Not real coordinates.
const ph = '+971 4 000 0000';
export const PLACES = [
  { id: 'p1', cat: 'pets', sub: 'Grooming', name: 'Paws & Co. Grooming', partner: true, rating: 4.8, count: 214, area: 'Dubai Marina', km: 0.7, x: 0.30, y: 0.42, img: 'media/pets.jpg', price: 'Bath + trim, medium dog · AED 180 (demo)', actions: ['directions', 'call', 'book'] },
  { id: 'p2', cat: 'pets', sub: 'Vet', name: 'Marina Vet Clinic', partner: true, rating: 4.7, count: 389, area: 'Dubai Marina', km: 1.1, x: 0.22, y: 0.55, img: null, price: 'Wellness check · AED 250 (demo)', actions: ['directions', 'call', 'book'] },
  { id: 'p3', cat: 'pets', sub: '24h', name: '24h Pet Care', partner: false, rating: 4.5, count: 97, area: 'JLT', km: 2.3, x: 0.47, y: 0.33, img: null, actions: ['directions', 'call'] },
  { id: 'p4', cat: 'pets', sub: 'Pet shop', name: 'Pet Corner', partner: false, rating: 4.4, count: 152, area: 'JLT', km: 2.0, x: 0.55, y: 0.40, img: null, actions: ['directions', 'call'] },
  { id: 'p5', cat: 'pets', sub: 'Boarding', name: 'Happy Tails Boarding', partner: false, rating: 4.6, count: 61, area: 'Al Barsha', km: 4.8, x: 0.74, y: 0.58, img: null, actions: ['directions', 'call'] },
  { id: 'p6', cat: 'barber', name: 'Fade Factory', partner: true, rating: 4.8, count: 312, area: 'Dubai Marina', km: 0.6, x: 0.34, y: 0.50, img: 'media/barber.jpg', price: 'Cut + beard · AED 90 (demo, published bundle)', actions: ['directions', 'call', 'book'] },
  { id: 'p7', cat: 'barber', name: 'Al Barsha Gents', partner: false, rating: 4.6, count: 128, area: 'Al Barsha', km: 1.1, x: 0.66, y: 0.52, img: null, actions: ['directions', 'call'] },
  { id: 'p8', cat: 'barber', name: 'Marina Blade', partner: false, rating: 4.7, count: 205, area: 'Dubai Marina', km: 2.0, x: 0.26, y: 0.36, img: null, actions: ['directions', 'call'] },
  { id: 'p9', cat: 'food', sub: 'Restaurants', name: 'Koshari Corner', partner: true, rating: 4.6, count: 540, area: 'Al Barsha', km: 3.1, x: 0.70, y: 0.45, img: 'media/food.jpg', price: 'Koshari, large · AED 32 (demo)', actions: ['directions', 'call', 'order'] },
  { id: 'p10', cat: 'food', sub: 'Delivery', name: 'Plate Run', partner: false, rating: 4.3, count: 2100, area: 'Delivery app', km: null, x: 0.50, y: 0.62, img: null, price: '15% off first order · as of 13 Oct (demo)', actions: ['app'] },
  { id: 'p11', cat: 'coffee', name: 'Bean Theory', partner: true, rating: 4.7, count: 433, area: 'Al Quoz', km: 6.2, x: 0.86, y: 0.40, img: 'media/coffee.jpg', price: 'Flat white · AED 22 (demo)', actions: ['directions', 'call', 'order'] },
  { id: 'p12', cat: 'coffee', name: 'Third Wave Lab', partner: false, rating: 4.5, count: 187, area: 'JLT', km: 2.1, x: 0.51, y: 0.27, img: null, actions: ['directions', 'call'] },
  { id: 'p13', cat: 'home-help', sub: 'Maid', name: 'Nest Helpers', partner: true, rating: 4.5, count: 76, area: 'Al Barsha', km: 3.9, x: 0.62, y: 0.66, img: 'media/home.jpg', price: 'Filipina placement · AED 6,400 · 9 days (demo)', actions: ['directions', 'call', 'book'] },
  { id: 'p14', cat: 'home-help', sub: 'Visa services', name: 'Marina Typing', partner: true, rating: 4.4, count: 58, area: 'Dubai Marina', km: 0.9, x: 0.37, y: 0.60, img: null, price: 'Domestic worker visa pack · AED 2,890 · 6 days (demo)', actions: ['directions', 'call', 'book'] },
  { id: 'p15', cat: 'laundry', name: 'Marina Express Laundry', partner: true, rating: 4.6, count: 301, area: 'Dubai Marina', km: 0.4, x: 0.31, y: 0.47, img: null, price: 'Shirt pressed · AED 8 (demo)', actions: ['directions', 'call', 'order'] },
  { id: 'p16', cat: 'clothing', name: 'Centre Style', partner: false, rating: 4.2, count: 860, area: 'Mall (demo)', km: 3.4, x: 0.58, y: 0.48, img: 'media/cloth.jpg', actions: ['directions', 'app'] },
  { id: 'p17', cat: 'fix-it', sub: 'AC', name: 'Al Barsha Cooling', partner: false, rating: 4.5, count: 92, area: 'Al Barsha', km: 3.6, x: 0.68, y: 0.38, img: null, price: 'AC check · from AED 120 (demo)', actions: ['directions', 'call'] },
].map(p => ({ ...p, phone: ph }));

// ---------- Profile episodes (scripted timeline, Oct 2026) ----------
// kind: told | choice | view | order | visit | share. ev: evidence for hypotheses.
// told episodes set a fact; a later told with the same key supersedes it.
export const HYPOTHESES = [
  { id: 'order_in_weeknight', label: 'Late on weeknights you order in', facet: 'food · channel', halfLifeDays: 90 },
  { id: 'eat_out_friday', label: 'On Friday lunch you eat out', facet: 'food · channel', halfLifeDays: 90 },
  { id: 'price_unless_deadline', label: 'You pick the cheapest, unless a deadline is at risk', facet: 'decision style', halfLifeDays: 90 },
  { id: 'specialty_coffee', label: 'You like specialty coffee around Al Quoz', facet: 'interests', halfLifeDays: 60 },
  { id: 'haircut_4w', label: 'You get a haircut about every 4 weeks', facet: 'routine', halfLifeDays: 120 },
];

export const EPISODES = [
  { at: '2026-10-01T09:12:04', kind: 'told', key: 'area', value: 'JLT', text: 'You said you live in JLT' },
  { at: '2026-10-02T22:41:10', kind: 'view', text: 'Looked at delivery apps, Tue 22:41', ev: [{ h: 'order_in_weeknight', w: 0.5 }] },
  { at: '2026-10-03T13:05:33', kind: 'visit', text: 'Lunch at Koshari Corner, Fri', ev: [{ h: 'eat_out_friday', w: 2 }] },
  { at: '2026-10-05T16:20:00', kind: 'share', text: 'Shared a coffee video (Al Quoz)', ev: [{ h: 'specialty_coffee', w: 1 }] },
  { at: '2026-10-06T10:02:45', kind: 'told', key: 'area', value: 'Dubai Marina', text: 'You said you moved to Dubai Marina' },
  { at: '2026-10-07T23:04:51', kind: 'order', text: 'Ordered in, Tue 23:04', ev: [{ h: 'order_in_weeknight', w: 2 }] },
  { at: '2026-10-09T18:30:00', kind: 'visit', text: 'Haircut at Fade Factory', ev: [{ h: 'haircut_4w', w: 1 }] },
  { at: '2026-10-10T13:12:20', kind: 'visit', text: 'Lunch out, Fri', ev: [{ h: 'eat_out_friday', w: 2 }] },
  { at: '2026-10-11T08:40:12', kind: 'told', key: 'maid_by', value: '1 Nov', text: 'You said you need a maid by 1 Nov' },
  { at: '2026-10-11T19:15:02', kind: 'share', text: 'Shared another coffee video', ev: [{ h: 'specialty_coffee', w: 1 }] },
  { at: '2026-10-12T11:03:41', kind: 'choice', text: 'Chose the faster office (deadline at risk)', ev: [{ h: 'price_unless_deadline', w: 2 }] },
  { at: '2026-10-12T11:09:27', kind: 'choice', text: 'Chose the cheaper visa office (deadline still fits)', ev: [{ h: 'price_unless_deadline', w: 2 }] },
  { at: '2026-10-13T22:40:00', kind: 'order', text: 'Ordered in, Tue 22:40', ev: [{ h: 'order_in_weeknight', w: 2 }] },
];

export const TOLD_LABELS = { area: 'Area', maid_by: 'Maid needed by' };
