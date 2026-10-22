// Interactive Google map inside the app. Google Places results stay on a Google
// map (Maps Platform terms); nothing hands the user to another app. The key comes
// from /api/maps/config (a browser key, or the local-preview fallback).
import { esc } from './ui.js';

let loading = null;
export function loadGoogleMaps() {
  loading ||= fetch('/api/maps/config', { credentials: 'same-origin' })
    .then(r => r.ok ? r.json() : Promise.reject(new Error('The interactive map is not configured.')))
    .then(cfg => new Promise((resolve, reject) => {
      window.__dubaiioMapsReady = () => resolve(window.google.maps);
      window.gm_authFailure = () => reject(new Error('Google Maps rejected the key.'));
      const script = document.createElement('script');
      script.async = true;
      script.src = 'https://maps.googleapis.com/maps/api/js?key=' + encodeURIComponent(cfg.key) + '&v=weekly&loading=async&callback=__dubaiioMapsReady';
      script.onerror = () => reject(new Error('Google Maps could not load.'));
      document.head.append(script);
    }));
  loading.catch(() => { loading = null; });
  return loading;
}

function pin(label, selected) {
  const el = document.createElement('div');
  el.className = 'gpin' + (selected ? ' on' : '');
  el.innerHTML = `<span>${esc(label)}</span>`;
  return el;
}

// One live map per container. show() redraws pins; onPick(id) opens a place.
export async function createLiveMap(el, { onPick, compact = false } = {}) {
  const maps = await loadGoogleMaps();
  const [{ Map }, { AdvancedMarkerElement }] = await Promise.all([maps.importLibrary('maps'), maps.importLibrary('marker')]);
  const map = new Map(el, {
    center: { lat: 25.08, lng: 55.14 }, zoom: 14, mapId: 'DEMO_MAP_ID',
    disableDefaultUI: true, zoomControl: !compact, clickableIcons: false,
    gestureHandling: compact ? 'cooperative' : 'greedy',
  });
  let markers = [];
  const clear = () => { for (const m of markers) m.map = null; markers = []; };
  return {
    map,
    show(places, { one = null, center = null } = {}) {
      clear();
      if (center) {
        const me = document.createElement('div'); me.className = 'gme'; me.title = center.label || 'Your area';
        markers.push(new AdvancedMarkerElement({ map, position: { lat: center.lat, lng: center.lng }, content: me, zIndex: 1 }));
      }
      const list = one ? [one] : places;
      list.forEach((p, i) => {
        const m = new AdvancedMarkerElement({ map, position: { lat: p.lat, lng: p.lng }, title: p.name, content: pin(one ? p.name : String(i + 1), !!one), zIndex: 10 + (list.length - i), gmpClickable: true });
        m.addListener('click', () => onPick?.(p.id));
        markers.push(m);
      });
      if (one) { map.panTo({ lat: one.lat, lng: one.lng }); map.setZoom(16); return; }
      if (!list.length) { if (center) map.setCenter({ lat: center.lat, lng: center.lng }); return; }
      const bounds = new maps.LatLngBounds();
      for (const p of list) bounds.extend({ lat: p.lat, lng: p.lng });
      if (center) bounds.extend({ lat: center.lat, lng: center.lng });
      map.fitBounds(bounds, compact ? 24 : { top: 70, right: 30, bottom: 260, left: 30 });
    },
  };
}
