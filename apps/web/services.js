// Services landing: reference-led cards; offers stay one level down.
import { SERVICE_GROUPS } from './offers.js';
import { svg, esc } from './ui.js';

const GROUPS = [
  { label: 'For your day', ids: ['laundry', 'carwash', 'pharmacy'] },
  { label: 'At home', ids: ['cleaning', 'ac', 'maid'] },
  { label: 'For your pet', ids: ['grooming'] },
];
const LABELS = { laundry: 'Laundry', carwash: 'Car wash', pharmacy: 'Pharmacy', cleaning: 'Cleaning', ac: 'AC repair', maid: 'Maid hire', grooming: 'Grooming' };

function category(g) {
  const prices = g.providers.map(p => p.from).filter(Number.isFinite);
  const from = prices.length ? 'From AED ' + Math.min(...prices).toLocaleString('en-US') + ' (demo)' : 'Published prices';
  return '<button class="service-category" data-svc="' + esc(g.id) + '">' +
    '<span class="service-photo" style="' + (g.img ? 'background-image:url(&quot;' + esc(g.img) + '&quot;)' : '') + '"></span>' +
    '<span class="service-icon">' + svg(g.glyph, 'ic sm') + '</span>' +
    '<span class="service-label"><b>' + esc(LABELS[g.id] || g.label) + '</b><span>' + esc(from) + '</span></span>' +
    '<span class="service-arrow">' + svg('chev', 'ic sm') + '</span></button>';
}

export function renderServicesLanding(el, area) {
  const used = new Set();
  const sections = GROUPS.map(group => {
    const rows = group.ids.map(id => SERVICE_GROUPS.find(g => g.id === id)).filter(Boolean);
    rows.forEach(g => used.add(g.id));
    return { label: group.label, rows };
  });
  const extra = SERVICE_GROUPS.filter(g => !used.has(g.id));
  if (extra.length) sections.push({ label: 'More services', rows: extra });
  el.innerHTML = 
    '<header class="services-brand"><div><b>Dubai<span>-io</span></b><p>Your Dubai companion</p></div><span class="visitor-pill">' + svg('person', 'ic sm') + ' Visitor</span></header>' +
    '<article class="services-hero"><div class="services-skyline"></div>' +
      '<div class="hero-top"><span>' + svg('orb', 'ic sm') + ' Dubai-io</span><span class="pill demo">Demo data</span></div>' +
      '<div class="hero-copy"><h1>Hello, visitor.</h1><p>One companion.<br>Your next step in Dubai.</p>' +
      '<button class="hero-guide" data-services-say="Guide me through the airport">' + svg('plane', 'ic sm') + ' Guide me to arrivals ' + svg('chev', 'ic sm') + '</button></div></article>' +
    '<section class="services-stay" aria-label="Your area"><span class="services-orb">' + svg('orb') + '</span><div><h2>Where are you staying?</h2>' +
      '<div class="stay-options">' + ['Business Bay', 'Dubai Marina'].map(a => '<button data-area="' + esc(a) + '" aria-pressed="' + (area === a) + '">' + svg(a === 'Dubai Marina' ? 'nav' : 'home', 'ic sm') + esc(a) + '</button>').join('') + '</div>' +
      (area ? '<p class="services-area">' + svg('check', 'ic xs') + ' ' + esc(area) + ' · you told me</p>' : '') + '</div></section>' +
    '<section class="services-try" aria-label="Try asking"><h2>Try asking</h2><div class="services-shortcuts">' +
      [{ icon: 'drop', title: 'Press a shirt', ask: 'I need a shirt pressed by 9 tomorrow', hint: 'Compare laundries' }, { icon: 'map', title: 'Find nearby', ask: 'Coffee near me', hint: 'Explore the map' }, { icon: 'wallet', title: 'Lost something', ask: 'I left my bag in the taxi', hint: 'Get the next steps' }].map(x =>
        '<button data-services-say="' + esc(x.ask) + '"><span>' + svg(x.icon) + '</span><b>' + esc(x.title) + '</b><small>' + esc(x.hint) + '</small>' + svg('chev', 'ic sm') + '</button>').join('') + '</div></section>' +
    '<div class="services-categories"><div class="services-section-head"><h2>Services</h2><span>Fixed prices · demo</span></div>' +
    sections.filter(g => g.rows.length).map(g => '<section class="services-group"><h3>' + esc(g.label) + '</h3><div class="service-category-grid">' + g.rows.map(category).join('') + '</div></section>').join('') +
    '<button class="services-anything" data-services-ask="1">' + svg('spark') + '<span><b>Something else?</b><small>Ask your companion.</small></span>' + svg('chev', 'ic sm') + '</button></div>';
}
