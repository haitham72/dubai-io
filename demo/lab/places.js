// Places at plausible coordinates in Dubai Marina, JBR, JLT, Media City,
// Barsha Heights, Al Barsha and Al Quoz. Names are fictional (demo data).
// why = where the place was picked up from: partner | google | video | visited.
export const HOME = { lat: 25.0805, lng: 55.1403, label: 'Dubai Marina' };
const phone = '+971 4 000 0000';

export const PLACES = [
  { id: 'p1', cat: 'pets', sub: 'Grooming', name: 'Paws & Co. Grooming', partner: true, rating: 4.8, count: 214, area: 'Dubai Marina', lat: 25.0838, lng: 55.1442, img: 'media/pets.jpg', why: 'partner', price: 'Bath + trim, medium dog · AED 180 (demo)', hours: '09:00–21:00', snippet: 'Fixed prices for bath, trim and nails. Books by slot.', actions: ['book', 'directions', 'call'] },
  { id: 'p2', cat: 'pets', sub: 'Vet', name: 'Marina Vet Clinic', partner: true, rating: 4.7, count: 389, area: 'Dubai Marina', lat: 25.0772, lng: 55.1389, img: 'media/vet.jpg', why: 'partner', price: 'Wellness check · AED 250 (demo)', hours: '08:00–22:00', snippet: 'Vaccinations, check-ups and microchips.', actions: ['book', 'directions', 'call'] },
  { id: 'p3', cat: 'pets', sub: '24h', name: '24h Pet Care', partner: false, rating: 4.5, count: 97, area: 'Barsha Heights', lat: 25.0975, lng: 55.1760, img: 'media/puppy.jpg', why: 'google', hours: 'Open 24 hours', snippet: 'Emergency vet. If it is urgent, call now.', actions: ['call', 'directions'] },
  { id: 'p4', cat: 'pets', sub: 'Pet shop', name: 'Pet Corner', partner: false, rating: 4.4, count: 152, area: 'JLT', lat: 25.0712, lng: 55.1445, img: null, why: 'google', hours: '10:00–22:00', snippet: 'Food, toys and travel crates.', actions: ['directions', 'call'] },
  { id: 'p5', cat: 'pets', sub: 'Boarding', name: 'Happy Tails Boarding', partner: false, rating: 4.6, count: 61, area: 'Al Barsha', lat: 25.1105, lng: 55.1985, img: null, why: 'google', hours: '07:00–20:00', snippet: 'Day care and overnight boarding.', actions: ['directions', 'call'] },
  { id: 'p6', cat: 'pets', sub: 'Photo', name: 'Lens & Paws', partner: false, rating: 4.9, count: 44, area: 'JBR', lat: 25.0790, lng: 55.1345, img: null, why: 'google', hours: 'By appointment', snippet: 'Beach portraits for pets at golden hour.', actions: ['call', 'directions'] },

  { id: 'f1', cat: 'food', sub: 'Restaurants', name: 'Koshari Corner', partner: true, rating: 4.6, count: 540, area: 'Al Barsha', lat: 25.1120, lng: 55.1960, img: 'media/food.jpg', why: 'visited', price: 'Koshari, large · AED 32 (demo)', hours: '11:00–02:00', snippet: 'You had lunch here on Fri 3 Oct.', actions: ['order', 'directions', 'call'] },
  { id: 'f2', cat: 'food', sub: 'Restaurants', name: 'Levant House', partner: false, rating: 4.5, count: 1210, area: 'JBR', lat: 25.0785, lng: 55.1330, img: 'media/spread.jpg', why: 'google', hours: '12:00–00:00', snippet: 'Mezze, grills and fresh bread.', actions: ['directions', 'call'] },
  { id: 'f3', cat: 'food', sub: 'Restaurants', name: 'Ember Grill', partner: false, rating: 4.4, count: 682, area: 'Dubai Marina', lat: 25.0870, lng: 55.1470, img: 'media/grill.jpg', why: 'google', hours: '17:00–01:00', snippet: 'Charcoal grills on the Marina walk.', actions: ['directions', 'call'] },
  { id: 'f4', cat: 'food', sub: 'Restaurants', name: 'Shawarma Street', partner: false, rating: 4.7, count: 2310, area: 'JLT', lat: 25.0698, lng: 55.1420, img: 'media/shawarma.jpg', why: 'video', video: { handle: '@eats.dxb (demo)', at: '0:22' }, hours: '10:00–04:00', snippet: 'In a video you shared: “the garlic sauce is the move”.', actions: ['directions', 'call'] },
  { id: 'f5', cat: 'food', sub: 'Restaurants', name: 'Harbour Table', partner: false, rating: 4.3, count: 905, area: 'Dubai Marina', lat: 25.0815, lng: 55.1365, img: 'media/rest-water.jpg', why: 'google', hours: '08:00–23:00', snippet: 'Breakfast by the water.', actions: ['directions', 'call'] },
  { id: 'f6', cat: 'food', sub: 'Delivery', name: 'Plate Run', partner: false, rating: 4.3, count: 2100, area: 'Delivery app', lat: null, lng: null, img: 'media/rest-room.jpg', why: 'google', price: '15% off first order · as of 13 Oct (demo)', hours: 'Delivers 24 hours', snippet: 'Their own published offer. Opens in their app.', actions: ['app'] },

  { id: 'c1', cat: 'coffee', name: 'Bean Theory', partner: true, rating: 4.7, count: 433, area: 'Al Quoz', lat: 25.1185, lng: 55.2150, img: 'media/coffee.jpg', why: 'video', video: { handle: '@slowpour (demo)', at: '0:14' }, price: 'Flat white · AED 22 (demo)', hours: '07:00–19:00', snippet: 'In a video you shared: single-origin pour-overs.', actions: ['order', 'directions', 'call'] },
  { id: 'c2', cat: 'coffee', name: 'Third Wave Lab', partner: false, rating: 4.5, count: 187, area: 'JLT', lat: 25.0725, lng: 55.1465, img: 'media/cafe-counter.jpg', why: 'video', video: { handle: '@slowpour (demo)', at: '0:41' }, hours: '07:30–22:00', snippet: 'In the same video: the curved bar.', actions: ['directions', 'call'] },
  { id: 'c3', cat: 'coffee', name: 'Bulb & Brew', partner: false, rating: 4.4, count: 260, area: 'Media City', lat: 25.0950, lng: 55.1560, img: 'media/cafe-bulbs.jpg', why: 'google', hours: '07:00–18:00', snippet: 'Quiet tables, good for laptops.', actions: ['directions', 'call'] },

  { id: 'b1', cat: 'barber', name: 'Fade Factory', partner: true, rating: 4.8, count: 312, area: 'Dubai Marina', lat: 25.0828, lng: 55.1418, img: 'media/barber.jpg', why: 'visited', price: 'Cut + beard · AED 90 (demo, published bundle)', hours: '10:00–23:00', snippet: 'You had a haircut here on 9 Oct.', actions: ['book', 'directions', 'call'] },
  { id: 'b2', cat: 'barber', name: 'Al Barsha Gents', partner: false, rating: 4.6, count: 128, area: 'Al Barsha', lat: 25.1095, lng: 55.1950, img: 'media/barber-dark.jpg', why: 'google', hours: '09:00–22:00', snippet: 'Hot towel shaves.', actions: ['directions', 'call'] },
  { id: 'b3', cat: 'barber', name: 'Marina Blade', partner: false, rating: 4.7, count: 205, area: 'Dubai Marina', lat: 25.0760, lng: 55.1360, img: null, why: 'google', hours: '10:00–22:00', snippet: 'Walk-ins after 18:00.', actions: ['directions', 'call'] },

  { id: 'h1', cat: 'home-help', sub: 'Maid', name: 'Nest Helpers', partner: true, rating: 4.5, count: 76, area: 'Al Barsha', lat: 25.1130, lng: 55.2010, img: 'media/home.jpg', why: 'partner', price: 'Filipina placement · AED 6,400 · 9 days (demo)', hours: '09:00–18:00', snippet: 'Fastest published placement time.', actions: ['book', 'directions', 'call'] },
  { id: 'h2', cat: 'home-help', sub: 'Maid', name: 'Maid Match', partner: false, rating: 4.3, count: 140, area: 'Barsha Heights', lat: 25.0990, lng: 55.1740, img: 'media/home-green.jpg', why: 'google', price: 'Filipina placement · AED 5,900 · 21 days (demo)', hours: '09:00–18:00', snippet: 'Published fees by nationality.', actions: ['directions', 'call'] },
  { id: 'h3', cat: 'home-help', sub: 'Visa services', name: 'Marina Typing', partner: true, rating: 4.4, count: 58, area: 'Dubai Marina', lat: 25.0848, lng: 55.1395, img: null, why: 'partner', price: 'Domestic worker visa pack · AED 2,890 · 6 days (demo)', hours: '08:00–20:00', snippet: 'They submit to the authority; Dubai-io never does.', actions: ['book', 'directions', 'call'] },

  { id: 'l1', cat: 'laundry', name: 'Marina Express Laundry', partner: true, rating: 4.6, count: 301, area: 'Dubai Marina', lat: 25.0812, lng: 55.1428, img: 'media/laundry.jpg', why: 'partner', price: 'Shirt pressed · AED 8 (demo)', hours: '07:00–23:00', snippet: 'Ready-time confirmed by the shop.', actions: ['order', 'directions', 'call'] },
  { id: 'l2', cat: 'laundry', name: 'Press & Fold', partner: false, rating: 4.4, count: 118, area: 'JLT', lat: 25.0705, lng: 55.1400, img: 'media/laundry-shelf.jpg', why: 'google', hours: '08:00–22:00', snippet: 'Same-day before 10:00.', actions: ['directions', 'call'] },

  { id: 's1', cat: 'clothing', name: 'Centre Style', partner: false, rating: 4.2, count: 860, area: 'Al Barsha', lat: 25.1180, lng: 55.2000, img: 'media/cloth.jpg', why: 'google', hours: '10:00–00:00', snippet: 'Summer basics.', actions: ['app', 'directions'] },
  { id: 's2', cat: 'clothing', name: 'Sole Society', partner: false, rating: 4.5, count: 233, area: 'JBR', lat: 25.0800, lng: 55.1340, img: 'media/shoes.jpg', why: 'google', hours: '10:00–23:00', snippet: 'Espadrilles and sandals.', actions: ['directions', 'call'] },

  { id: 'x1', cat: 'fix-it', sub: 'AC', name: 'Al Barsha Cooling', partner: false, rating: 4.5, count: 92, area: 'Al Barsha', lat: 25.1080, lng: 55.1930, img: 'media/ac.jpg', why: 'google', price: 'AC check · from AED 120 (demo)', hours: '08:00–20:00', snippet: 'Found nearby.', actions: ['call', 'directions'] },
  { id: 'x2', cat: 'fix-it', sub: 'Plumbing', name: 'FixIt Pros', partner: true, rating: 4.6, count: 410, area: 'Media City', lat: 25.0930, lng: 55.1600, img: null, why: 'partner', price: 'Call-out · AED 150 (demo)', hours: '08:00–22:00', snippet: 'Next slot today 17:00.', actions: ['book', 'call'] },
].map(p => ({ ...p, phone }));

export const AREA_LABELS = [
  ['DUBAI MARINA', 25.0802, 55.1392], ['JBR', 25.0772, 55.1318], ['JLT', 25.0710, 55.1462],
  ['MEDIA CITY', 25.0932, 55.1548], ['BARSHA HEIGHTS', 25.0985, 55.1762], ['AL BARSHA', 25.1112, 55.1992],
  ['PALM JUMEIRAH', 25.1160, 55.1395], ['AL QUOZ', 25.1205, 55.2165],
];

// "Picked up from": the honest version of a creator rail. Every place says
// where it came from.
export const SOURCES = [
  { id: 'video', label: 'Your videos', img: 'media/coffee.jpg' },
  { id: 'partner', label: 'Partners', img: 'media/laundry.jpg' },
  { id: 'visited', label: 'You went', img: 'media/barber.jpg' },
  { id: 'google', label: 'Google', img: 'media/spread.jpg' },
];
