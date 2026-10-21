// Full-screen in-app map (Uber / Talabat style) on MapLibre GL, drawn from a
// bundled OpenStreetMap extract (fixtures/dubai-map.json, ODbL). No tile
// server, no API key: the lab must run inside a sandboxed Artifact page.
// This is an explicitly selected 3D demo. Live Places uses a separate Google 2D view.
import { PLACES, AREA_LABELS, HOME, CATEGORIES } from './data.js';

const LOOK = {
  cyan: { land: '#EDF1F3', sea: '#BDE3EE', water: '#C7E8F1', park: '#DCEAE3', beach: '#F2EBDC', road: '#FFFFFF', casing: '#D2DCE2', accent: '#79D2E8', bld: ['#E4EAED', '#D6E3E9', '#C8E2EC'] },
};

export function createMap(el, paletteName, svg, onPick) {
  if (!window.maplibregl) return null;
  const L = LOOK[paletteName] || LOOK.cyan;
  const map = new maplibregl.Map({
    container: el,
    style: { version: 8, sources: {}, layers: [{ id: 'bg', type: 'background', paint: { 'background-color': L.land } }] },
    center: [55.1505, 25.0880], zoom: 13.4, pitch: 52, bearing: -32,
    minZoom: 12.3, maxZoom: 18.5,
    maxBounds: [[55.07, 25.02], [55.275, 25.17]],
    attributionControl: false,
    dragRotate: true, pitchWithRotate: true, touchPitch: true,
  });
  map.addControl(new maplibregl.AttributionControl({ compact: true, customAttribution: '© OpenStreetMap contributors · lab map' }), 'bottom-left');

  const ready = fetch('fixtures/dubai-map.json').then(r => r.json()).then(data => new Promise(res => {
    const add = () => {
      for (const k of Object.keys(data)) map.addSource(k, { type: 'geojson', data: data[k] });
      map.addLayer({ id: 'sea', type: 'fill', source: 'sea', paint: { 'fill-color': L.sea } });
      map.addLayer({ id: 'islands', type: 'fill', source: 'islands', paint: { 'fill-color': L.land } });
      map.addLayer({ id: 'beach', type: 'fill', source: 'beach', paint: { 'fill-color': L.beach } });
      map.addLayer({ id: 'water', type: 'fill', source: 'water', paint: { 'fill-color': L.water } });
      map.addLayer({ id: 'parks', type: 'fill', source: 'parks', paint: { 'fill-color': L.park } });
      // one zoom interpolation, with the per-class width inside each stop
      const W = (lo, hi) => ['interpolate', ['exponential', 1.6], ['zoom'],
        12, ['match', ['get', 'c'], 'major', lo[0], 'primary', lo[1], 'secondary', lo[2], 'link', lo[3], lo[4]],
        17, ['match', ['get', 'c'], 'major', hi[0], 'primary', hi[1], 'secondary', hi[2], 'link', hi[3], hi[4]]];
      map.addLayer({ id: 'casing', type: 'line', source: 'roads', filter: ['in', ['get', 'c'], ['literal', ['major', 'primary', 'secondary']]],
        layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: { 'line-color': L.casing, 'line-width': W([4, 3, 2, 1, 1], [26, 20, 15, 8, 7]) } });
      map.addLayer({ id: 'roads', type: 'line', source: 'roads',
        layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: { 'line-color': L.road, 'line-width': W([2.6, 2, 1.4, .8, .6], [22, 16, 12, 7, 6]) } });
      map.addLayer({ id: 'major-accent', type: 'line', source: 'roads', filter: ['==', ['get', 'c'], 'major'],
        paint: { 'line-color': L.accent, 'line-width': ['interpolate', ['linear'], ['zoom'], 12, .6, 17, 3], 'line-opacity': .7 } });
      map.addLayer({ id: 'buildings', type: 'fill-extrusion', source: 'buildings', minzoom: 12.5,
        paint: {
          'fill-extrusion-color': ['interpolate', ['linear'], ['get', 'h'], 0, L.bld[0], 80, L.bld[1], 300, L.bld[2]],
          'fill-extrusion-height': ['get', 'h'], 'fill-extrusion-base': 0,
          'fill-extrusion-opacity': ['interpolate', ['linear'], ['zoom'], 12.5, 0, 13.4, .92],
        } });
      map.setLight({ anchor: 'map', color: '#ffffff', intensity: .32, position: [1.3, 210, 35] });
      res();
    };
    if (map.isStyleLoaded()) add(); else map.once('load', add);
  }));

  // area labels as DOM markers (sandboxed pages cannot fetch label fonts)
  for (const [t, lat, lng] of AREA_LABELS) {
    const e = document.createElement('div'); e.className = 'area-label'; e.textContent = t;
    new maplibregl.Marker({ element: e, anchor: 'center' }).setLngLat([lng, lat]).addTo(map);
  }
  // "you" dot: the area you told me, not a live position
  const me = document.createElement('div'); me.className = 'me-dot'; me.title = 'Dubai Marina · demo area';
  me.innerHTML = '<span></span>';
  new maplibregl.Marker({ element: me }).setLngLat([HOME.lng, HOME.lat]).addTo(map);

  const markers = new Map();
  for (const p of PLACES) {
    if (p.lat == null) continue;
    const k = CATEGORIES.find(c => c.id === p.cat);
    const e = document.createElement('button');
    e.className = `mpin ${p.partner ? 'partner' : ''}`;
    e.setAttribute('aria-label', p.name);
    e.innerHTML = p.img
      ? `<span class="mpin-ph" style="background-image:url('${p.img}')"></span><span class="mpin-badge">${svg(k.glyph, 'ic xs')}</span>`
      : `<span class="mpin-ph glyph">${svg(k.glyph, 'ic sm')}</span>`;
    e.addEventListener('click', ev => { ev.stopPropagation(); onPick(p.id); });
    const m = new maplibregl.Marker({ element: e, anchor: 'bottom' }).setLngLat([p.lng, p.lat]).addTo(map);
    markers.set(p.id, { m, e, p });
  }

  return {
    map, ready,
    filter(ids) { for (const [id, r] of markers) r.e.hidden = !ids.has(id); },
    select(id, padBottom) {
      for (const [k, r] of markers) r.e.classList.toggle('sel', k === id);
      const r = markers.get(id); if (!r) return;
      map.easeTo({ center: [r.p.lng, r.p.lat], zoom: Math.max(map.getZoom(), 15.4), duration: matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 650, padding: { bottom: padBottom + 20, top: 150, left: 0, right: 0 } });
    },
    fit(ids, padBottom, withHome = true) {
      const pts = [...ids].map(id => markers.get(id)).filter(Boolean).map(r => [r.p.lng, r.p.lat]);
      if (withHome) pts.push([HOME.lng, HOME.lat]);
      if (!pts.length) return;
      if (pts.length === 1) { map.easeTo({ center: pts[0], zoom: 15, duration: matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 650, padding: { bottom: padBottom + 30, top: 160, left: 0, right: 0 } }); return; }
      const b = pts.reduce((bb, p) => bb.extend(p), new maplibregl.LngLatBounds(pts[0], pts[0]));
      const pad = { top: 160, bottom: padBottom + 30, left: 36, right: 36 };
      const cam = map.cameraForBounds(b, { padding: pad, bearing: -32 });
      const zoom = Math.min(15.5, Math.max(12.9, (cam ? cam.zoom : 13.5) + 0.25));
      map.easeTo({ center: b.getCenter(), zoom, padding: pad, pitch: 45, bearing: -32, duration: matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 650 });
    },
    resize() { map.resize(); },
  };
}

export function km(p) {
  if (p.lat == null) return null;
  const R = 6371, r = x => x * Math.PI / 180;
  const a = Math.sin(r(p.lat - HOME.lat) / 2) ** 2 + Math.cos(r(HOME.lat)) * Math.cos(r(p.lat)) * Math.sin(r(p.lng - HOME.lng) / 2) ** 2;
  return Math.round(R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a)) * 10) / 10;
}
