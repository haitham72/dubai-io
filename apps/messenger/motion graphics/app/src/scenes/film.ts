// FILM: the Messenger redesign film (VIDEO-PLAN.md), 60 s. Clean and elegant, but it moves: a cursor that hovers and
// clicks, the camera pushing in on every click and pulling out on every reveal, lists and messages revealing row
// by row, soft transitions between workspaces (rise, glass push, blur dissolve, match dissolve, depth pull).
// The screens are the real redesign (../../Messenger-redesign.md, the 15 references) drawn in code: Lucide icons
// (icons.ts), the app's own photos, avatars and sample data (app/public/photos/, fetched once), and the
// weather stills (weather-*.jpg). Will's lines are placed by analysis/film_mix.py at VO below.
import type * as THREE from 'three';
import { Scene, type Frame, type PostOverrides } from '../engine/scene';
import { Layer2D, clearRT } from '../engine/gl';
import { LIN } from '../engine/palette';
import { F, font } from '../engine/type';
import { clamp, ease, lerp, hash } from '../engine/util';
import { drawIcon } from './icons';

type X = CanvasRenderingContext2D;
const SW = 1920, SH = 1080, WW = 1720, WH = 960;
const NAV = 208, SIDE = 380, MX = NAV + SIDE;
const BLUE = '#1677FF', PURPLE = '#7C3AED', INK = '#101828', GREY = '#667085', LINE = 'rgba(50,80,130,0.10)', GREEN = '#22C55E';
/** When Will speaks (seconds); film_mix.py uses the same table. */
export const VO = [0.8, 4.4, 10.6, 17.2, 23.4, 34.4, 41.4, 51.4, 56.4];

const sat = (v: number) => clamp(v);
const io = ease.inOutCubic, oc = ease.outCubic, ob = ease.outBack;
const pr = (t: number, a: number, b: number) => clamp((t - a) / Math.max(1e-4, b - a));
/** A staggered reveal: 0 -> 1 over `d` seconds starting at t0 + i * step. */
const rv = (t: number, t0: number, i = 0, step = 0.06, d = 0.4) => oc(sat((t - t0 - i * step) / d));
/** Hover in [a, b] (soft edges). */
const hv = (t: number, a: number, b: number) => sat((t - a) / 0.18) * (1 - sat((t - b) / 0.18));
/** A press: 1 -> 0.92 -> 1 around a click. */
const press = (t: number, tc: number) => 1 - 0.08 * Math.sin(sat((t - tc) / 0.2) * Math.PI) * (t >= tc ? 1 : 0);
const rr = (c: X, x: number, y: number, w: number, h: number, r: number) => { c.beginPath(); c.roundRect(x, y, w, h, r); };
function T(c: X, s: string, x: number, y: number, size: number, o: { w?: number; col?: string; align?: CanvasTextAlign; base?: CanvasTextBaseline } = {}) {
  c.font = font(F.inter(o.w ?? 400), size);
  c.fillStyle = o.col ?? INK; c.textAlign = o.align ?? 'left'; c.textBaseline = o.base ?? 'alphabetic';
  c.fillText(s, x, y);
  c.textAlign = 'left'; c.textBaseline = 'alphabetic';
}
function wrap(c: X, s: string, maxW: number, size: number, w = 400) {
  c.font = font(F.inter(w), size);
  const out: string[] = []; let cur = '';
  for (const word of s.split(' ')) { const n = cur ? `${cur} ${word}` : word; if (c.measureText(n).width > maxW && cur) { out.push(cur); cur = word; } else cur = n; }
  if (cur) out.push(cur);
  return out;
}
function card(c: X, x: number, y: number, w: number, h: number, r = 20, o: { fill?: string; shadow?: number; border?: string } = {}) {
  c.save();
  if (o.shadow !== 0) { c.shadowColor = `rgba(30,60,110,${0.08 * (o.shadow ?? 1)})`; c.shadowBlur = 40; c.shadowOffsetY = 12; }
  c.fillStyle = o.fill ?? 'rgba(255,255,255,0.96)'; rr(c, x, y, w, h, r); c.fill();
  c.restore();
  c.strokeStyle = o.border ?? LINE; c.lineWidth = 1; rr(c, x + 0.5, y + 0.5, w - 1, h - 1, r); c.stroke();
}
function photo(c: X, im: HTMLImageElement, x: number, y: number, w: number, h: number, r = 16, zoom = 1, fx = 0.5, fy = 0.5) {
  const s = Math.max(w / im.width, h / im.height) * zoom, iw = im.width * s, ih = im.height * s;
  c.save(); rr(c, x, y, w, h, r); c.clip();
  c.drawImage(im, x + (w - iw) * fx, y + (h - ih) * fy, iw, ih);
  c.restore();
}
function avatar(c: X, im: HTMLImageElement, cx: number, cy: number, r: number, online = false) {
  c.save(); c.beginPath(); c.arc(cx, cy, r, 0, 7); c.clip();
  const s = (2 * r) / Math.min(im.width, im.height);
  c.drawImage(im, cx - (im.width * s) / 2, cy - (im.height * s) / 2, im.width * s, im.height * s);
  c.restore();
  if (online) { c.fillStyle = '#fff'; c.beginPath(); c.arc(cx + r * 0.72, cy + r * 0.72, r * 0.26, 0, 7); c.fill(); c.fillStyle = GREEN; c.beginPath(); c.arc(cx + r * 0.72, cy + r * 0.72, r * 0.18, 0, 7); c.fill(); }
}
function pill(c: X, s: string, x: number, y: number, h: number, o: { fill?: string; col?: string; size?: number; w?: number; icon?: string; pad?: number; align?: 'left' | 'center' } = {}) {
  const size = o.size ?? 15; c.font = font(F.inter(o.w ?? 600), size);
  const iw = o.icon ? size + 8 : 0, pad = o.pad ?? 18, w = c.measureText(s).width + pad * 2 + iw;
  const x0 = o.align === 'center' ? x - w / 2 : x;
  c.fillStyle = o.fill ?? BLUE; rr(c, x0, y, w, h, h / 2); c.fill();
  if (o.icon) drawIcon(c, o.icon, x0 + pad + size / 2, y + h / 2, size + 2, o.col ?? '#fff', 2);
  T(c, s, x0 + pad + iw, y + h / 2 + 1, size, { w: o.w ?? 600, col: o.col ?? '#fff', base: 'middle' });
  return w;
}
/** Scale the drawing about (x, y): for press and hover lifts. */
function about(c: X, x: number, y: number, s: number, draw: () => void) { c.save(); c.translate(x, y); c.scale(s, s); c.translate(-x, -y); draw(); c.restore(); }

type Key = [number, number, number, number]; // [time, focus x, focus y (window coords), zoom]
function camAt(keys: Key[], t: number): [number, number, number] {
  if (t <= keys[0]![0]) return [keys[0]![1], keys[0]![2], keys[0]![3]];
  for (let i = 1; i < keys.length; i++) {
    const b = keys[i]!;
    if (t > b[0]) continue;
    const a = keys[i - 1]!, k = io(pr(t, a[0], b[0]));
    return [lerp(a[1], b[1], k), lerp(a[2], b[2], k), Math.exp(lerp(Math.log(a[3]), Math.log(b[3]), k))];
  }
  const l = keys[keys.length - 1]!;
  return [l[1], l[2], l[3]];
}
/** The cursor's path: [time, x, y] in window coords, eased between keys. */
type PKey = [number, number, number];
function pathAt(keys: PKey[], t: number): [number, number] {
  if (t <= keys[0]![0]) return [keys[0]![1], keys[0]![2]];
  for (let i = 1; i < keys.length; i++) {
    const b = keys[i]!;
    if (t > b[0]) continue;
    const a = keys[i - 1]!, k = io(pr(t, a[0], b[0]));
    return [lerp(a[1], b[1], k), lerp(a[2], b[2], k)];
  }
  const l = keys[keys.length - 1]!;
  return [l[1], l[2]];
}
interface Cursor { path: PKey[]; clicks: number[]; show: [number, number] }

type Into = 'none' | 'rise' | 'glass' | 'blur' | 'match' | 'depth';
interface Shot { id: string; t0: number; into: Into; dur: number; draw: (c: X, t: number) => void }

// weather states (the stills in app/public/photos/)
const WX = [
  { id: 'summer', tab: 'Summer', temp: 41, cond: 'Sunny', feels: 'Feels like 44°', icon: 'sun', iconCol: '#F59E0B', hum: '38%', wind: '14 km/h NE' },
  { id: 'winter', tab: 'Winter', temp: 14, cond: 'Light snow', feels: 'Feels like 11°', icon: 'snowflake', iconCol: '#60A5FA', hum: '71%', wind: '9 km/h N' },
  { id: 'rain', tab: 'Rain', temp: 22, cond: 'Heavy rain', feels: 'Feels like 20°', icon: 'cloud-rain', iconCol: '#3B82F6', hum: '92%', wind: '26 km/h SE' },
  { id: 'wind', tab: 'Wind', temp: 29, cond: 'Windy, dust', feels: 'Gusts 58 km/h', icon: 'wind', iconCol: '#B45309', hum: '24%', wind: '48 km/h NW' },
];
const WX_T = [40.6, 41.9, 42.9, 43.9]; // when each state is clicked

export default class Film extends Scene {
  ui = new Layer2D();
  A = new Layer2D();
  B = new Layer2D();
  sky!: HTMLCanvasElement;
  ph: Record<string, HTMLImageElement> = {};
  shots: Shot[] = [];
  thumbs: Record<string, HTMLCanvasElement> = {};
  msgEnd = 0;

  override async init() {
    const load = async (k: string, src: string) => { const im = new Image(); im.src = src; try { await im.decode(); this.ph[k] = im; } catch { /* a missing optional image falls back below */ } };
    const P = (id: string) => `photos/photo-${id}.jpg`;
    await Promise.all([
      load('beach', P('1507525428034-b723cf961d3e')), load('dubai', P('1512453979798-5ea266f8880c')), load('family', P('1511895426328-dc8714191300')),
      load('gaming', P('1542751371-adc38448a05e')), load('study', P('1522202176988-66273c2fd55f')), load('blossom', P('1522383225653-ed111181a951')),
      load('bali', P('1537996194471-e657df975ab4')), load('kyoto', P('1493976040374-85c8e12f0c0e')), load('london', P('1513635269975-59663e0ac1ad')),
      ...[12, 15, 47, 53, 44, 59, 32, 7, 9, 22].map((n) => load(`av${n}`, `photos/av${n}.jpg`)),
      ...WX.map((w) => load(`wx-${w.id}`, `photos/weather-${w.id}.jpg`)),
    ]);
    for (const w of WX) if (!this.ph[`wx-${w.id}`]) this.ph[`wx-${w.id}`] = this.ph.dubai!;
    this.sky = this.makeSky();
    this.shots = [
      { id: 'logo', t0: -1, into: 'none', dur: 0, draw: (c, t) => this.logoShot(c, t) },
      { id: 'chats', t0: 2.9, into: 'rise', dur: 0.9, draw: (c, t) => this.chatsShot(c, t) },
      { id: 'ai', t0: 20.6, into: 'glass', dur: 0.8, draw: (c, t) => this.aiShot(c, t) },
      { id: 'flights', t0: 31.4, into: 'match', dur: 0.5, draw: (c, t) => this.flightsShot(c, t) },
      { id: 'calendar', t0: 36.7, into: 'match', dur: 0.45, draw: (c, t) => this.calendarShot(c, t) },
      { id: 'weather', t0: 40.0, into: 'blur', dur: 0.6, draw: (c, t) => this.weatherShot(c, t) },
      { id: 'stocks', t0: 44.6, into: 'blur', dur: 0.55, draw: (c, t) => this.stocksShot(c, t) },
      { id: 'mail', t0: 46.4, into: 'blur', dur: 0.55, draw: (c, t) => this.mailShot(c, t) },
      { id: 'profile', t0: 50.9, into: 'glass', dur: 0.7, draw: (c, t) => this.profileShot(c, t) },
      { id: 'finale', t0: 55.5, into: 'depth', dur: 1.0, draw: (c, t) => this.finaleShot(c, t) },
    ];
  }

  // ================================================================ stage, window, cursor
  makeSky() {
    const cv = document.createElement('canvas'); cv.width = 2400; cv.height = 1400;
    const c = cv.getContext('2d')!;
    const g = c.createLinearGradient(0, 0, 0, 1400);
    g.addColorStop(0, '#BFD6F2'); g.addColorStop(0.55, '#DCE8F6'); g.addColorStop(1, '#EEF3FA');
    c.fillStyle = g; c.fillRect(0, 0, 2400, 1400);
    c.filter = 'blur(70px)';
    for (let i = 0; i < 26; i++) {
      c.fillStyle = `rgba(255,255,255,${0.35 + 0.4 * hash(i, 2)})`;
      c.beginPath(); c.ellipse(hash(i, 3) * 2400, 300 + hash(i, 4) * 1000, 160 + 260 * hash(i, 5), 70 + 110 * hash(i, 6), 0, 0, 7); c.fill();
    }
    c.filter = 'blur(40px)'; c.fillStyle = 'rgba(120,150,190,0.18)';
    c.beginPath(); c.moveTo(0, 1250); for (let x = 0; x <= 2400; x += 80) c.lineTo(x, 1080 + 120 * Math.sin(x / 260) + 60 * Math.sin(x / 97)); c.lineTo(2400, 1400); c.lineTo(0, 1400); c.fill();
    return cv;
  }
  stage(c: X, t: number) { c.drawImage(this.sky, -200 - t * 3, -140 - t * 1.2); }

  /** The app window under the camera; then the cursor, drawn in screen space at a constant size. */
  win(c: X, cam: [number, number, number], t: number, draw: () => void, cur?: Cursor) {
    const [fx, fy, z] = cam;
    c.save();
    c.translate(SW / 2, SH / 2); c.scale(z, z); c.translate(-fx, -fy);
    c.save(); c.shadowColor = 'rgba(30,60,110,0.16)'; c.shadowBlur = 90; c.shadowOffsetY = 30;
    c.fillStyle = 'rgba(255,255,255,0.92)'; rr(c, 0, 0, WW, WH, 26); c.fill(); c.restore();
    c.save(); rr(c, 0, 0, WW, WH, 26); c.clip();
    draw();
    c.restore();
    c.strokeStyle = 'rgba(255,255,255,0.7)'; c.lineWidth = 1.5; rr(c, 0.75, 0.75, WW - 1.5, WH - 1.5, 26); c.stroke();
    c.restore();
    if (cur && t >= cur.show[0] && t <= cur.show[1]) {
      const [px, py] = pathAt(cur.path, t);
      const sx = SW / 2 + (px - fx) * z, sy = SH / 2 + (py - fy) * z;
      const a = sat((t - cur.show[0]) / 0.25) * (1 - sat((t - cur.show[1] + 0.25) / 0.25));
      this.pointer(c, sx, sy, t, cur.clicks, a);
    }
  }

  /** A macOS-style pointer with a click ripple. */
  pointer(c: X, x: number, y: number, t: number, clicks: number[], a: number) {
    let s = 1.15;
    for (const tc of clicks) {
      const d = t - tc;
      if (d >= 0 && d < 0.5) {
        c.save(); c.globalAlpha = a * (1 - d / 0.5);
        c.strokeStyle = 'rgba(22,119,255,0.55)'; c.lineWidth = 3; c.beginPath(); c.arc(x, y, 10 + 46 * oc(d / 0.5), 0, 7); c.stroke();
        c.fillStyle = 'rgba(22,119,255,0.12)'; c.beginPath(); c.arc(x, y, 10 + 30 * oc(d / 0.5), 0, 7); c.fill();
        c.restore();
      }
      if (d >= -0.05 && d < 0.2) s *= 1 - 0.18 * Math.sin(sat((d + 0.05) / 0.25) * Math.PI);
    }
    c.save(); c.globalAlpha = a; c.translate(x, y); c.scale(s, s);
    c.shadowColor = 'rgba(0,0,0,0.3)'; c.shadowBlur = 8; c.shadowOffsetY = 3;
    c.beginPath(); c.moveTo(0, 0); c.lineTo(0, 26); c.lineTo(6.5, 20); c.lineTo(11, 30); c.lineTo(15, 28); c.lineTo(10.5, 18.5); c.lineTo(19, 18.5); c.closePath();
    c.fillStyle = '#111'; c.fill(); c.shadowColor = 'transparent'; c.strokeStyle = '#fff'; c.lineWidth = 2; c.stroke();
    c.restore();
  }

  nav(c: X, active: string, avatarHover = 0) {
    c.fillStyle = 'rgba(244,247,252,0.94)'; c.fillRect(0, 0, NAV, WH);
    c.fillStyle = LINE; c.fillRect(NAV - 1, 0, 1, WH);
    ['#FF5F57', '#FEBC2E', '#28C840'].forEach((col, i) => { c.fillStyle = col; c.beginPath(); c.arc(26 + i * 20, 26, 6, 0, 7); c.fill(); });
    this.mTile(c, 44, 82, 40);
    T(c, 'Messenger', 74, 90, 20, { w: 700 });
    const items: [string, string][] = [['Chats', 'message-circle'], ['Flights', 'plane'], ['Stocks', 'chart-line'], ['Weather', 'cloud-sun'], ['Mail', 'mail'], ['Calendar', 'calendar'], ['Files', 'folder'], ['', ''], ['AI Chat', 'sparkles'], ['Research', 'telescope'], ['', ''], ['History', 'history'], ['Settings', 'settings']];
    let y = 140;
    for (const [label, icon] of items) {
      if (!label) { c.fillStyle = LINE; c.fillRect(24, y + 6, NAV - 48, 1); y += 18; continue; }
      const on = label === active;
      if (on) { c.fillStyle = 'rgba(22,119,255,0.10)'; rr(c, 14, y, NAV - 28, 42, 12); c.fill(); }
      drawIcon(c, icon, 40, y + 21, 20, on ? BLUE : '#475467');
      T(c, label, 62, y + 27, 15, { w: on ? 600 : 500, col: on ? BLUE : '#344054' });
      y += 48;
    }
    if (avatarHover > 0) { c.fillStyle = `rgba(22,119,255,${0.1 * avatarHover})`; rr(c, 12, WH - 76, NAV - 24, 60, 14); c.fill(); }
    avatar(c, this.ph.av12!, 42, WH - 46, 20, true);
    T(c, 'Haitham', 72, WH - 40, 15, { w: 600 });
  }

  mTile(c: X, cx: number, cy: number, s: number) {
    c.save();
    const g = c.createLinearGradient(cx - s / 2, cy - s / 2, cx + s / 2, cy + s / 2);
    g.addColorStop(0, '#4D9BFF'); g.addColorStop(1, '#1062E0');
    c.shadowColor = 'rgba(22,119,255,0.3)'; c.shadowBlur = s * 0.5; c.shadowOffsetY = s * 0.15;
    c.fillStyle = g; rr(c, cx - s / 2, cy - s / 2, s, s, s * 0.27); c.fill();
    c.restore();
    T(c, 'M', cx, cy + s * 0.03, s * 0.58, { w: 800, col: '#fff', align: 'center', base: 'middle' });
  }

  composer(c: X, x: number, y: number, w: number, text: string, o: { placeholder?: string; caret?: boolean; t?: number; ai?: boolean; sendPress?: number; working?: number } = {}) {
    card(c, x, y, w, 56, 28, { shadow: 0.6 });
    const wk = o.working ?? 0;
    if (wk > 0.01) {
      const per = 2 * (w - 56) + Math.PI * 56;
      c.save(); c.strokeStyle = `rgba(124,58,237,${0.8 * wk})`; c.lineWidth = 2.5; c.lineCap = 'round';
      c.setLineDash([per * 0.2, per * 0.8]); c.lineDashOffset = -(o.t ?? 0) * per * 0.7; rr(c, x, y, w, 56, 28); c.stroke(); c.restore();
    }
    drawIcon(c, o.ai ? 'plus' : 'paperclip', x + 30, y + 28, 20, GREY);
    c.save(); c.beginPath(); c.rect(x + 50, y, w - 220, 56); c.clip();
    c.font = font(F.inter(400), 17);
    const tw = text ? c.measureText(text).width : 0, off = Math.max(0, tw - (w - 240));
    if (text) T(c, text, x + 58 - off, y + 34, 17);
    else T(c, o.placeholder ?? 'Type a message…', x + 58, y + 34, 17, { col: '#98A2B3' });
    if (o.caret && ((o.t ?? 0) % 1 < 0.6 || text)) { c.fillStyle = BLUE; c.fillRect(x + 60 + tw - off, y + 16, 2, 24); }
    c.restore();
    const icons = o.ai ? ['globe', 'paperclip', 'mic'] : ['smile', 'mic'];
    icons.forEach((ic, i) => drawIcon(c, ic, x + w - 70 - (icons.length - 1 - i) * 40 - 36, y + 28, 20, GREY));
    about(c, x + w - 32, y + 28, o.sendPress ?? 1, () => {
      c.fillStyle = BLUE; c.beginPath(); c.arc(x + w - 32, y + 28, 19, 0, 7); c.fill();
      drawIcon(c, o.ai ? 'arrow-up' : 'send', x + w - 32, y + 28, 18, '#fff', 2);
    });
  }

  // ================================================================ 1. the logo (0-3.4 s)
  logoShot(c: X, t: number) {
    this.stage(c, t);
    const k = ob(sat((t - 0.15) / 0.6), 1.4), wordA = sat((t - 0.55) / 0.5), out = io(pr(t, 2.7, 3.6));
    c.save();
    c.translate(SW / 2, SH / 2); const z = 1 + 0.04 * sat(t / 3) + out * 0.5; c.scale(z, z);
    c.globalAlpha = 1 - out;
    const shift = 170 * oc(wordA);
    c.save(); c.translate(-shift, 0); c.scale(k, k); this.mTile(c, 0, 0, 170); c.restore();
    c.globalAlpha = (1 - out) * wordA;
    T(c, 'Messenger', -shift + 130 + (1 - oc(wordA)) * 30, 6, 132, { w: 600, base: 'middle' });
    c.restore();
  }

  // ================================================================ 2. Chats -> Updates -> Image ready -> Use in chat (2.9-21 s)
  chatsShot(c: X, t: number) {
    this.stage(c, t);
    const cam = camAt([
      [2.9, 860, 480, 0.96], [4.1, 860, 480, 1.0], [4.9, 520, 330, 1.4], [5.7, 520, 330, 1.4], [6.6, 1140, 450, 1.12],
      [9.3, 1140, 480, 1.13], [10.1, 520, 250, 1.4], [10.7, 520, 250, 1.4], [11.6, 1100, 320, 1.16], [13.4, 1040, 420, 1.2],
      [15.3, 1000, 560, 1.28], [16.5, 1000, 600, 1.3], [17.6, 1180, 640, 1.18], [21.5, 1200, 640, 1.16],
    ], t);
    const cur: Cursor = {
      show: [3.9, 16.9],
      clicks: [5.3, 10.4, 13.2, 16.25],
      path: [[3.9, 1300, 760], [5.0, 470, 280], [5.6, 470, 280], [9.4, 470, 280], [10.2, 470, 192], [10.7, 470, 192], [12.4, 760, 300], [13.0, 735, 245], [13.6, 735, 245], [15.3, 992, 755], [16.6, 992, 755]],
    };
    this.win(c, cam, t, () => this.chatsApp(c, t), cur);
  }

  chatsApp(c: X, t: number, still = false) {
    this.nav(c, 'Chats');
    c.fillStyle = 'rgba(250,252,255,0.96)'; c.fillRect(NAV, 0, SIDE, WH);
    c.fillStyle = LINE; c.fillRect(MX - 1, 0, 1, WH);
    T(c, 'Chats', NAV + 24, 72, 30, { w: 700 });
    drawIcon(c, 'square-pen', MX - 70, 62, 20, '#344054'); drawIcon(c, 'list-filter', MX - 36, 62, 20, '#344054');
    c.fillStyle = '#EEF2F8'; rr(c, NAV + 20, 96, SIDE - 40, 42, 21); c.fill();
    drawIcon(c, 'search', NAV + 44, 117, 18, '#98A2B3'); T(c, 'Search chats, tasks, files…', NAV + 64, 123, 15, { col: '#98A2B3' });
    const uh = still ? 0 : hv(t, 9.9, 10.9);
    const U = { x: NAV + 16, y: 152, w: SIDE - 32, h: 74 };
    about(c, U.x + U.w / 2, U.y + U.h / 2, (1 + 0.03 * uh) * (still ? 1 : press(t, 10.4)), () => {
      c.save(); c.shadowColor = `rgba(124,58,237,${0.15 + 0.35 * uh})`; c.shadowBlur = 20 + 30 * uh;
      const lg = c.createLinearGradient(U.x, U.y, U.x + U.w, U.y); lg.addColorStop(0, '#F3EDFF'); lg.addColorStop(1, '#E6DBFF');
      c.fillStyle = lg; rr(c, U.x, U.y, U.w, U.h, 18); c.fill(); c.restore();
      drawIcon(c, 'sparkles', U.x + 30, U.y + 37, 22, PURPLE);
      T(c, 'Messenger Updates', U.x + 56, U.y + 32, 16, { w: 600 });
      T(c, 'Image ready, flight found, 5 more…', U.x + 56, U.y + 54, 14, { col: GREY });
      pill(c, '9+', U.x + U.w - 82, U.y + 24, 24, { fill: PURPLE, size: 12, pad: 9 });
      drawIcon(c, 'chevron-right', U.x + U.w - 22, U.y + 37, 18, GREY);
    });
    const rows: [string, string, string, string, number, boolean?][] = [
      ['av15', 'Arif Khan', 'Sounds great! See you soon.', '7:42 PM', 2, true], ['av47', 'Sara Ali', 'That’s amazing! 😍', '6:28 PM', 1],
      ['beach', 'Travel Buddies', 'Shared a link: Bali itinerary', '5:17 PM', 4], ['av53', 'Mazen', 'Haha good one!', '3:50 PM', 0],
      ['family', 'Family', 'Mom: Dinner is ready! 🍲', '2:03 PM', 3], ['gaming', 'Gaming Squad', 'Let’s play later tonight?', '12:21 PM', 0],
      ['av44', 'Lina', 'Okay, see you tomorrow!', 'Yesterday', 0], ['av59', 'Omar', 'Thanks! 🙏', 'Yesterday', 1],
      ['av32', 'Hana', 'This is awesome!', 'Mon', 0], ['study', 'Study Group', 'New notes are up', 'Sun', 6],
    ];
    const newMsg = still ? 1 : sat((t - 7.8) / 0.3);
    const opened = still || t > 5.3, rh = still ? 0 : hv(t, 4.8, 5.6);
    rows.forEach(([im, name, prev, time, n, on], i) => {
      const k = still ? 1 : rv(t, 3.2, i, 0.05, 0.35), y = 240 + i * 74 + (1 - k) * 16;
      c.save(); c.globalAlpha = k;
      if (i === 0 && (opened || rh > 0)) { c.fillStyle = `rgba(22,119,255,${opened ? 0.08 : 0.05 * rh})`; rr(c, NAV + 12, y + 2, SIDE - 24, 70, 14); c.fill(); }
      about(c, NAV + 190, y + 37, i === 0 && !still ? (1 + 0.015 * rh) * press(t, 5.3) : 1, () => {
        avatar(c, this.ph[im]!, NAV + 46, y + 37, 24, on);
        T(c, name, NAV + 82, y + 31, 16, { w: 600 });
        T(c, i === 0 && newMsg > 0.5 ? 'Free on Saturday? 🏖️' : prev, NAV + 82, y + 54, 14, { col: GREY });
        T(c, time, MX - 24, y + 31, 12, { col: GREY, align: 'right' });
        const cnt = i === 0 ? (opened ? 0 : n) : n;
        if (cnt) { c.fillStyle = BLUE; c.beginPath(); c.arc(MX - 36, y + 50, 11, 0, 7); c.fill(); T(c, String(cnt), MX - 36, y + 51, 12, { w: 700, col: '#fff', align: 'center', base: 'middle' }); }
      });
      c.restore();
    });
    c.fillStyle = 'rgba(255,255,255,0.97)'; c.fillRect(MX, 0, WW - MX, WH);
    const head = still ? 1 : rv(t, 5.4);
    c.save(); c.globalAlpha = head;
    avatar(c, this.ph.av15!, MX + 44, 46, 22, true);
    T(c, 'Arif Khan', MX + 80, 42, 18, { w: 600 });
    c.fillStyle = GREEN; c.beginPath(); c.arc(MX + 85, 62, 4, 0, 7); c.fill(); T(c, 'Online', MX + 95, 67, 13, { col: GREY });
    ['phone', 'video', 'search', 'ellipsis'].forEach((ic, i) => drawIcon(c, ic, WW - 196 + i * 52, 46, 20, '#344054'));
    c.restore();
    c.fillStyle = LINE; c.fillRect(MX, 90, WW - MX, 1);
    if (!opened) {
      drawIcon(c, 'message-circle', (MX + WW) / 2, 440, 44, '#CBD5E1');
      T(c, 'Select a chat to start messaging', (MX + WW) / 2, 500, 16, { col: '#98A2B3', align: 'center' });
    } else {
      c.save(); c.beginPath(); c.rect(MX, 91, WW - MX, 790); c.clip();
      const sent = still ? 0 : io(pr(t, 16.9, 17.6));
      c.translate(0, -sent * 300 - newMsg * 70);
      this.messages(c, t, still);
      c.restore();
    }
    this.composer(c, MX + 24, WH - 80, WW - MX - 48, '');
    if (!still) this.updates(c, t);
  }

  bubble(c: X, s: string, mine: boolean, y: number, time: string, k = 1) {
    const lines = wrap(c, s, 420, 16), w = Math.max(...lines.map((l) => c.measureText(l).width)) + 36, h = lines.length * 23 + 40;
    if (k <= 0) return h;
    const x = mine ? WW - 40 - w : MX + 80, dy = (1 - k) * 18;
    c.save(); c.globalAlpha *= sat(k);
    about(c, mine ? x + w : x, y + h, 0.9 + 0.1 * k, () => {
      c.save(); if (!mine) { c.shadowColor = 'rgba(30,60,110,0.06)'; c.shadowBlur = 12; c.shadowOffsetY = 3; }
      c.fillStyle = mine ? '#E3EEFF' : '#F3F6FA'; rr(c, x, y + dy, w, h, 18); c.fill(); c.restore();
      lines.forEach((l, i) => T(c, l, x + 18, y + dy + 27 + i * 23, 16));
      T(c, time, x + w - 16 - (mine ? 18 : 0), y + dy + h - 10, 11, { col: '#98A2B3', align: 'right' });
      if (mine) drawIcon(c, 'check-check', x + w - 22, y + dy + h - 14, 14, BLUE);
    });
    if (!mine) avatar(c, this.ph.av15!, MX + 52, y + h - 16, 16);
    c.restore();
    return h;
  }

  messages(c: X, t: number, still: boolean) {
    const K = (i: number) => (still ? 1 : ob(sat((t - 5.6 - i * 0.28) / 0.4), 1.2));
    let y = 116;
    y += this.bubble(c, 'Hey! Are you free this weekend? We could go to the beach or something.', true, y, '2:14 PM', K(0)) + 14;
    y += this.bubble(c, 'Sounds great! See you soon.', false, y, '2:14 PM', K(1)) + 14;
    y += this.bubble(c, 'Yeah! That sounds perfect. Let’s do it! 🏝️', true, y, '2:18 PM', K(2)) + 18;
    const ki = K(3);
    if (ki > 0) { c.save(); c.globalAlpha *= sat(ki); const y0 = y; about(c, MX + 80, y0 + 260, 0.92 + 0.08 * ki, () => photo(c, this.ph.dubai!, MX + 80, y0, 420, 260, 18)); avatar(c, this.ph.av15!, MX + 52, y0 + 244, 16); c.restore(); }
    y += 274;
    y += this.bubble(c, 'This place looks amazing 😍', false, y, '3:03 PM', K(4)) + 14;
    y += this.bubble(c, 'Wow! That looks incredible. I wish I was there already 😅', true, y, '3:16 PM', K(5)) + 14;
    const nm = still ? 1 : ob(sat((t - 7.8) / 0.45), 1.3);
    y += this.bubble(c, 'Free on Saturday? 🏖️', false, y, '7:43 PM', nm) + 14;
    const im = still ? 0 : sat((t - 17.15) / 0.15);
    if (im > 0) {
      c.globalAlpha = im;
      photo(c, this.ph.beach!, WW - 40 - 420, y + 6, 420, 260, 18);
      T(c, '7:44 PM', WW - 64, y + 290, 11, { col: '#98A2B3', align: 'right' }); drawIcon(c, 'check-check', WW - 48, y + 286, 14, BLUE);
      c.globalAlpha = 1;
      y += 300;
      this.bubble(c, 'Wow, perfect for Saturday! 😍', false, y, '7:44 PM', ob(sat((t - 18.4) / 0.4), 1.2));
    }
    this.msgEnd = y;
  }

  updates(c: X, t: number) {
    const open = io(pr(t, 10.5, 11.2)), close = io(pr(t, 16.4, 16.9));
    if (open <= 0 || close >= 1) return;
    const A = { x: NAV + 16, y: 152, w: SIDE - 32, h: 74 }, Bx = { x: MX + 16, y: 100, w: WW - MX - 40, h: 214 };
    const x = lerp(A.x, Bx.x, open), y = lerp(A.y, Bx.y, open), w = lerp(A.w, Bx.w, open), h = lerp(A.h, Bx.h, open);
    c.save();
    c.globalAlpha = 1 - close;
    c.shadowColor = 'rgba(80,40,160,0.16)'; c.shadowBlur = 50; c.shadowOffsetY = 16;
    c.fillStyle = 'rgba(247,243,255,0.97)'; rr(c, x, y, w, h, 24); c.fill(); c.shadowColor = 'transparent';
    c.strokeStyle = 'rgba(124,58,237,0.16)'; c.lineWidth = 1; rr(c, x, y, w, h, 24); c.stroke();
    c.save(); rr(c, x, y, w, h, 24); c.clip();
    c.globalAlpha *= sat((open - 0.55) / 0.45);
    drawIcon(c, 'sparkles', Bx.x + 34, Bx.y + 38, 24, PURPLE);
    T(c, 'Messenger Updates', Bx.x + 62, Bx.y + 36, 20, { w: 700 });
    pill(c, '9+', Bx.x + 220, Bx.y + 20, 24, { fill: 'rgba(124,58,237,0.14)', col: PURPLE, size: 12, pad: 9 });
    T(c, 'Stay updated with your latest results, insights and drafts.', Bx.x + 62, Bx.y + 60, 14, { col: GREY });
    drawIcon(c, 'x', Bx.x + Bx.w - 34, Bx.y + 34, 20, GREY);
    const cards: [string, string, string, string][] = [['image', 'Image ready', 'Your social post visual is ready', '2:14 PM'], ['plane', 'Flight found', '3 flights to London from AED 2,450', '2:14 PM'], ['file-text', 'Research ready', '5 key insights on market trends', '12:36 PM'], ['mail', 'Email draft ready', 'Your follow-up draft is prepared', '11:20 AM']];
    const cw = (Bx.w - 48 - 3 * 14) / 4;
    cards.forEach(([ic, title, body, time], i) => {
      const k = rv(t, 10.9, i, 0.1, 0.4);
      if (k <= 0) return;
      const hov = i === 0 ? hv(t, 12.7, 13.6) : 0, sel = i === 0 && t > 13.2;
      const cx = Bx.x + 24 + i * (cw + 14) + (1 - k) * 60, cy = Bx.y + 88 - 4 * hov;
      c.save(); c.globalAlpha *= k;
      about(c, cx + cw / 2, cy + 52, (1 + 0.03 * hov) * press(t, 13.2), () => {
        card(c, cx, cy, cw, 104, 18, { fill: 'rgba(255,255,255,0.94)', shadow: 0.4 + hov, border: sel || hov > 0.5 ? 'rgba(22,119,255,0.6)' : LINE });
        c.fillStyle = 'rgba(124,58,237,0.10)'; rr(c, cx + 16, cy + 16, 40, 40, 12); c.fill(); drawIcon(c, ic, cx + 36, cy + 36, 20, PURPLE);
        T(c, title, cx + 68, cy + 32, 15, { w: 600 });
        wrap(c, body, cw - 84, 13).slice(0, 2).forEach((l, j) => T(c, l, cx + 68, cy + 52 + j * 18, 13, { col: GREY }));
        T(c, time, cx + 68, cy + 92, 12, { col: '#98A2B3' });
      });
      c.restore();
    });
    c.restore();
    c.restore();
    this.imageReady(c, t, close);
  }

  imageReady(c: X, t: number, close: number) {
    const k = oc(pr(t, 13.3, 13.9));
    if (k <= 0) return;
    const x = MX + 40, y = 330, w = 560, h = 460;
    const fly = io(pr(t, 16.4, 17.15));
    c.save();
    c.globalAlpha = k * (1 - close);
    about(c, x + w / 2, y, 0.94 + 0.06 * k, () => {
      card(c, x, y, w, h, 24, { shadow: 1.4 });
      c.fillStyle = 'rgba(124,58,237,0.10)'; rr(c, x + 24, y + 22, 40, 40, 12); c.fill(); drawIcon(c, 'image', x + 44, y + 42, 20, PURPLE);
      T(c, 'Image ready', x + 76, y + 40, 18, { w: 600 }); T(c, 'Your social post visual is ready', x + 76, y + 60, 14, { col: GREY });
      drawIcon(c, 'ellipsis', x + w - 36, y + 42, 20, GREY);
      if (fly < 0.05) {
        const ik = oc(pr(t, 13.6, 14.4));
        c.save(); c.globalAlpha *= ik; c.filter = `blur(${(1 - ik) * 14}px)`; photo(c, this.ph.beach!, x + 24, y + 82, w - 48, 270, 16, 1.06 - 0.06 * ik); c.restore();
      }
      drawIcon(c, 'clock', x + 34, y + 378, 16, GREY); T(c, 'Generated 2 minutes ago', x + 50, y + 383, 13, { col: GREY });
      c.save(); c.globalAlpha *= sat((t - 14.2) / 0.3); pill(c, 'Ready', x + w - 120, y + 366, 30, { fill: 'rgba(34,197,94,0.12)', col: '#15803D', size: 13, icon: 'check', pad: 12 }); c.restore();
      pill(c, 'Open', x + 24, y + 404, 40, { icon: 'external-link', size: 15 });
      pill(c, 'Share', x + 150, y + 404, 40, { fill: 'rgba(16,24,40,0.05)', col: INK, icon: 'share', size: 15 });
      const bh = hv(t, 15.4, 16.6), on = t > 16.25;
      about(c, x + 380, y + 424, (1 + 0.05 * bh) * press(t, 16.25), () => {
        pill(c, 'Use in chat', x + 290, y + 404, 40, { fill: on ? BLUE : `rgba(22,119,255,${0.10 + 0.12 * bh})`, col: on ? '#fff' : BLUE, icon: 'message-circle', size: 15 });
      });
    });
    c.restore();
    if (fly > 0 && fly < 1) {
      const tx = lerp(x + 24, WW - 40 - 420, fly), ty = lerp(y + 82, 560, fly), tw = lerp(w - 48, 420, fly), th = lerp(270, 260, fly);
      c.save(); c.shadowColor = 'rgba(30,60,110,0.25)'; c.shadowBlur = 40; c.shadowOffsetY = 16;
      c.fillStyle = '#fff'; rr(c, tx, ty, tw, th, 18); c.fill(); c.restore();
      photo(c, this.ph.beach!, tx, ty, tw, th, 18);
    }
  }

  // ================================================================ 3. AI Chat: close-up typing, thinking, the burst (20.6-31.4 s)
  aiShot(c: X, t: number) {
    this.stage(c, t);
    const cam = camAt([
      [20.6, 880, 900, 2.2], [23.0, 1200, 900, 2.2], [24.0, 1000, 450, 1.18], [25.5, 1000, 450, 1.15], [26.4, 1000, 470, 1.04],
      [29.4, 1000, 480, 1.06], [30.2, 780, 720, 1.38], [31.6, 780, 720, 1.38],
    ], t);
    const cur: Cursor = { show: [22.6, 31.4], clicks: [23.2, 30.5], path: [[22.6, 1420, 960], [23.05, 1332, 904], [23.4, 1332, 904], [24.4, 1500, 600], [29.6, 760, 800], [30.2, 704, 756], [31.4, 704, 756]] };
    this.win(c, cam, t, () => this.aiApp(c, t), cur);
  }

  aiApp(c: X, t: number, still = false) {
    this.nav(c, 'AI Chat');
    c.fillStyle = 'rgba(250,252,255,0.96)'; c.fillRect(NAV, 0, SIDE, WH); c.fillStyle = LINE; c.fillRect(MX - 1, 0, 1, WH);
    T(c, 'Messenger AI', NAV + 24, 72, 28, { w: 700 }); drawIcon(c, 'square-pen', MX - 36, 62, 20, '#344054');
    c.fillStyle = 'rgba(22,119,255,0.08)'; rr(c, NAV + 14, 100, SIDE - 28, 46, 12); c.fill();
    drawIcon(c, 'message-circle', NAV + 40, 123, 20, BLUE); T(c, 'New Chat', NAV + 62, 129, 15, { w: 600, col: BLUE });
    T(c, 'RECENT', NAV + 26, 186, 12, { w: 600, col: '#98A2B3' });
    ['Spring weekend in Kyoto', 'Dubai beach image', 'Flights to London', 'Market summary', 'Follow-up email to IDC', 'Weekend plans'].forEach((s, i) => {
      const k = still ? 1 : rv(t, 20.9, i, 0.05);
      c.save(); c.globalAlpha = k; c.translate((1 - k) * -16, 0);
      drawIcon(c, 'message-circle', NAV + 40, 222 + i * 46, 18, GREY); T(c, s, NAV + 62, 228 + i * 46, 15, { col: '#344054' });
      c.restore();
    });
    c.fillStyle = 'rgba(255,255,255,0.97)'; c.fillRect(MX, 0, WW - MX, WH);
    drawIcon(c, 'sparkles', MX + 36, 46, 20, PURPLE); T(c, 'Messenger AI', MX + 56, 52, 17, { w: 600 }); T(c, 'GPT-5', MX + 140, 52, 15, { col: GREY });
    drawIcon(c, 'share', WW - 96, 46, 20, '#344054'); drawIcon(c, 'ellipsis', WW - 52, 46, 20, '#344054');
    c.fillStyle = LINE; c.fillRect(MX, 90, WW - MX, 1);
    const CX0 = MX + 44, CX1 = WW - 356;
    const prompt = 'Plan a spring weekend in Kyoto, with photos of the cherry blossoms';
    const sent = still || t > 23.25;
    const typed = still ? prompt.length : Math.floor(sat((t - 21.0) / 2.0) * prompt.length);
    if (!sent && t < 21.5) {
      c.globalAlpha = 1 - sat((t - 21.2) / 0.3);
      drawIcon(c, 'sparkles', (CX0 + CX1) / 2, 360, 46, PURPLE); T(c, 'What can I help with?', (CX0 + CX1) / 2, 430, 28, { w: 600, align: 'center' });
      c.globalAlpha = 1;
    }
    if (sent) {
      const k = still ? 1 : ob(sat((t - 23.3) / 0.4), 1.2);
      c.font = font(F.inter(400), 16); const w = c.measureText(prompt).width + 40;
      c.save(); c.globalAlpha = sat(k); about(c, CX1, 140, 0.9 + 0.1 * k, () => { c.fillStyle = '#E3EEFF'; rr(c, CX1 - w, 112, w, 52, 18); c.fill(); T(c, prompt, CX1 - w + 20, 144, 16); }); c.restore();
    }
    const think = still ? 0 : sat((t - 23.6) / 0.25) * (1 - sat((t - 25.6) / 0.3));
    const doneLine = still || t > 25.6;
    if (think > 0.01) {
      c.save(); c.globalAlpha = think;
      c.save(); c.translate(CX0 + 14, 206); c.rotate(t * 4); drawIcon(c, 'sparkles', 0, 0, 22, PURPLE); c.restore();
      const gx = CX0 + 40 + ((t * 300) % 400) - 200;
      const g = c.createLinearGradient(gx, 0, gx + 200, 0);
      g.addColorStop(0, '#98A2B3'); g.addColorStop(0.5, PURPLE); g.addColorStop(1, '#98A2B3');
      c.font = font(F.inter(600), 16); c.fillStyle = g; c.fillText('Thinking…', CX0 + 38, 212);
      ['Searching 8 sources', 'Checking the blossom forecast', 'Choosing photos', 'Planning the days'].forEach((s, i) => {
        const a = sat((t - 23.8 - i * 0.4) / 0.25), done = t > 24.2 + i * 0.4;
        if (a <= 0) return;
        c.save(); c.globalAlpha *= a;
        if (done) { c.fillStyle = GREEN; c.beginPath(); c.arc(CX0 + 46, 246 + i * 30, 8, 0, 7); c.fill(); drawIcon(c, 'check', CX0 + 46, 246 + i * 30, 11, '#fff', 2.6); }
        else { c.save(); c.translate(CX0 + 46, 246 + i * 30); c.rotate(t * 8); drawIcon(c, 'loader-circle', 0, 0, 16, BLUE); c.restore(); }
        T(c, s, CX0 + 64, 251 + i * 30, 14, { col: GREY });
        c.restore();
      });
      for (let i = 0; i < 4; i++) {
        const x = CX0 + i * ((CX1 - CX0 + 14) / 4), w = (CX1 - CX0 - 42) / 4, sh = 0.5 + 0.5 * Math.sin(t * 5 - i);
        c.fillStyle = `rgba(226,232,240,${0.5 + 0.3 * sh})`; rr(c, x, 380, w, 200, 18); c.fill();
      }
      [0.92, 0.8, 0.66].forEach((fr, i) => { c.fillStyle = `rgba(226,232,240,${0.6 + 0.3 * Math.sin(t * 5 - i)})`; rr(c, CX0, 610 + i * 28, (CX1 - CX0) * fr, 14, 7); c.fill(); });
      c.restore();
    }
    if (doneLine) {
      const a = still ? 1 : sat((t - 25.6) / 0.3);
      c.globalAlpha = a; drawIcon(c, 'sparkles', CX0 + 14, 206, 20, PURPLE); T(c, 'Searched 8 sources · 6s', CX0 + 36, 212, 14, { col: GREY }); c.globalAlpha = 1;
      const pics: [string, number, number, number][] = [['kyoto', 1, 0.5, 0.5], ['blossom', 1, 0.5, 0.5], ['kyoto', 1.7, 0.85, 0.2], ['blossom', 2.0, 0.2, 0.8]];
      const pw = (CX1 - CX0 - 42) / 4;
      pics.forEach(([im, z, fx, fy], i) => {
        const k = still ? 1 : oc(sat((t - 25.75 - i * 0.12) / 0.55));
        if (k <= 0) return;
        const x = CX0 + i * (pw + 14), y = 236;
        c.save(); c.globalAlpha = k; c.filter = `blur(${(1 - k) * 16}px)`;
        about(c, x + pw / 2, y + 110, 0.9 + 0.1 * k, () => photo(c, this.ph[im]!, x, y, pw, 220, 18, z, fx, fy));
        c.restore();
      });
      const plan = ['Day 1 · Higashiyama: Kiyomizu-dera at sunrise, then the lanes of Sannenzaka.', 'Day 2 · Philosopher’s Path in full bloom, lunch by the canal, Nanzen-ji.', 'Day 3 · Maruyama Park at night, when the big cherry tree is lit.'];
      plan.forEach((s, i) => {
        const t0 = 26.3 + i * 0.55, n = still ? s.length : Math.floor(sat((t - t0) / 0.6) * s.length);
        if (n <= 0) return;
        c.fillStyle = BLUE; c.beginPath(); c.arc(CX0 + 6, 491 + i * 32, 3.5, 0, 7); c.fill();
        T(c, s.slice(0, n), CX0 + 20, 496 + i * 32, 16, { col: '#1D2939' });
      });
      const days: [string, string, string][] = [['kyoto', 'Day 1', 'Higashiyama'], ['blossom', 'Day 2', 'Philosopher’s Path'], ['kyoto', 'Day 3', 'Maruyama Park']];
      const dw = (CX1 - CX0 - 28) / 3;
      days.forEach(([im, d, s], i) => {
        const k = still ? 1 : rv(t, 27.8, i, 0.12, 0.45);
        if (k <= 0) return;
        const x = CX0 + i * (dw + 14), y = 600 + (1 - k) * 24;
        c.save(); c.globalAlpha = k;
        card(c, x, y, dw, 120, 18, { shadow: 0.6 });
        photo(c, this.ph[im]!, x + 12, y + 12, 96, 96, 14, 1.2 + i * 0.2);
        T(c, d, x + 124, y + 48, 13, { w: 600, col: BLUE }); T(c, s, x + 124, y + 72, 16, { w: 600 });
        drawIcon(c, 'map-pin', x + 132, y + 94, 14, GREY); T(c, 'Kyoto', x + 144, y + 99, 13, { col: GREY });
        c.restore();
      });
      const chips: [string, string][] = [['Book flights', 'plane'], ['Find hotels', 'bed'], ['Add to calendar', 'calendar-plus']];
      let cx = CX0;
      chips.forEach(([s, ic], i) => {
        const k = still ? 1 : ob(sat((t - 28.7 - i * 0.1) / 0.35), 1.3);
        c.font = font(F.inter(600), 15);
        const w = c.measureText(s).width + 36 + 23;
        if (k > 0) {
          const hov = i === 0 && !still ? hv(t, 29.9, 31.0) : 0, on = i === 0 && !still && t > 30.5, x0 = cx;
          c.save(); c.globalAlpha = sat(k);
          about(c, x0 + w / 2, 756, k * (1 + 0.05 * hov) * (i === 0 && !still ? press(t, 30.5) : 1), () => {
            pill(c, s, x0, 734, 44, { fill: on ? BLUE : `rgba(22,119,255,${0.08 + 0.1 * hov})`, col: on ? '#fff' : BLUE, icon: ic, size: 15 });
          });
          c.restore();
        }
        cx += w + 12;
      });
    }
    const sx = WW - 330;
    c.fillStyle = 'rgba(248,250,253,0.9)'; c.fillRect(sx - 14, 91, 344, WH - 91);
    if (still || t > 25.9) {
      T(c, 'Sources', sx + 8, 132, 16, { w: 600 });
      const src: [string, string, string][] = [['kyoto', 'Visit Kyoto', 'japan.travel'], ['blossom', 'Kiyomizu-dera Temple', 'en.wikipedia.org'], ['blossom', 'Cherry blossom forecast 2026', 'jnto.go.jp'], ['kyoto', 'Kyoto Travel Guide', 'lonelyplanet.com'], ['blossom', 'Best hanami spots', 'weathernews.jp']];
      src.forEach(([im, title, dom], i) => {
        const k = still ? 1 : rv(t, 26.0, i, 0.1, 0.4);
        if (k <= 0) return;
        c.save(); c.globalAlpha = k; c.translate((1 - k) * 30, 0);
        const y = 156 + i * 74;
        photo(c, this.ph[im]!, sx + 8, y, 54, 54, 12, 1 + 0.3 * i);
        T(c, title, sx + 76, y + 24, 14, { w: 600 }); T(c, dom, sx + 76, y + 44, 13, { col: GREY });
        drawIcon(c, 'external-link', sx + 296, y + 27, 16, '#98A2B3');
        c.restore();
      });
    }
    this.composer(c, CX0, WH - 84, CX1 - CX0, sent ? '' : prompt.slice(0, typed), { placeholder: 'Ask anything…', caret: !sent, t, ai: true, sendPress: still ? 1 : press(t, 23.2), working: still ? 0 : think });
  }

  // ================================================================ 4. Flights -> Calendar (31.4-40 s)
  flightsShot(c: X, t: number) {
    this.stage(c, t);
    const cam = camAt([[31.4, 1100, 320, 1.2], [33.2, 1100, 420, 1.12], [35.4, 1060, 500, 1.18], [36.0, 780, 560, 1.42], [37.2, 800, 560, 1.42]], t);
    const cur: Cursor = { show: [34.6, 37.0], clicks: [36.3], path: [[34.6, 1300, 700], [35.9, 738, 559], [36.9, 738, 559]] };
    this.win(c, cam, t, () => this.flightsApp(c, t), cur);
  }

  flightsApp(c: X, t: number, still = false) {
    this.nav(c, 'Flights');
    c.fillStyle = 'rgba(250,252,255,0.96)'; c.fillRect(NAV, 0, SIDE, WH); c.fillStyle = LINE; c.fillRect(MX - 1, 0, 1, WH);
    T(c, 'Flights', NAV + 24, 72, 28, { w: 700 });
    card(c, NAV + 16, 100, SIDE - 32, 70, 16, { shadow: 0.4 });
    c.fillStyle = BLUE; c.beginPath(); c.arc(NAV + 50, 135, 18, 0, 7); c.fill(); drawIcon(c, 'plus', NAV + 50, 135, 18, '#fff', 2.2);
    T(c, 'New Booking', NAV + 80, 131, 15, { w: 600 }); T(c, 'Search and book your next trip', NAV + 80, 151, 13, { col: GREY });
    T(c, 'My Bookings', NAV + 26, 214, 16, { w: 600 });
    ([['DXB → JED', 'Saudia · 12 Oct 2026', 'Confirmed', GREEN], ['CAI → DXB', 'EgyptAir · 3 Nov 2026', 'Upcoming', BLUE]] as const).forEach(([r, d, s, col], i) => {
      const y = 232 + i * 80;
      card(c, NAV + 16, y, SIDE - 32, 68, 16, { shadow: 0.3 });
      drawIcon(c, 'plane', NAV + 46, y + 34, 20, BLUE); T(c, r, NAV + 74, y + 30, 15, { w: 600 }); T(c, d, NAV + 74, y + 50, 13, { col: GREY });
      pill(c, s, MX - 130, y + 21, 26, { fill: col === GREEN ? 'rgba(34,197,94,0.12)' : 'rgba(22,119,255,0.10)', col: col === GREEN ? '#15803D' : BLUE, size: 12, pad: 10 });
    });
    c.fillStyle = 'rgba(255,255,255,0.97)'; c.fillRect(MX, 0, WW - MX, WH);
    card(c, MX + 28, 30, WW - MX - 56, 64, 32, { shadow: 0.5 });
    drawIcon(c, 'sparkles', MX + 62, 62, 20, PURPLE);
    const q = 'Flights Dubai to London next Wednesday';
    const n = still ? q.length : Math.floor(sat((t - 31.7) / 0.9) * q.length);
    T(c, q.slice(0, n), MX + 88, 68, 17);
    if (!still && n < q.length) { c.font = font(F.inter(400), 17); c.fillStyle = BLUE; c.fillRect(MX + 90 + c.measureText(q.slice(0, n)).width, 50, 2, 24); }
    const dest: [string, string, string][] = [['dubai', 'Dubai', 'From AED 820'], ['london', 'London', 'From AED 1,950'], ['kyoto', 'Kyoto', 'From AED 3,100'], ['bali', 'Bali', 'From AED 2,640']];
    const dw = (WW - MX - 56 - 3 * 16) / 4;
    dest.forEach(([im, name, from], i) => {
      const k = still ? 1 : rv(t, 31.6, i, 0.08, 0.45), x = MX + 28 + i * (dw + 16), y = 120 + (1 - k) * 20, on = i === 1 && (still || t > 32.7);
      c.save(); c.globalAlpha = k;
      photo(c, this.ph[im]!, x, y, dw, 170, 18);
      const g = c.createLinearGradient(0, y + 80, 0, y + 170); g.addColorStop(0, 'rgba(0,0,0,0)'); g.addColorStop(1, 'rgba(0,0,0,0.55)');
      c.fillStyle = g; rr(c, x, y, dw, 170, 18); c.fill();
      T(c, name, x + 18, y + 138, 18, { w: 700, col: '#fff' }); T(c, from, x + 18, y + 158, 13, { col: 'rgba(255,255,255,0.9)' });
      if (on) { c.strokeStyle = BLUE; c.lineWidth = 3; rr(c, x - 1.5, y - 1.5, dw + 3, 173, 19); c.stroke(); }
      c.restore();
    });
    const k = still ? 1 : oc(sat((t - 33.0) / 0.5));
    if (k > 0) {
      const x = MX + 28, y = 322 + (1 - k) * 30, w = WW - MX - 56, h = 300;
      c.save(); c.globalAlpha = k;
      card(c, x, y, w, h, 24, { shadow: 1.2 });
      drawIcon(c, 'plane', x + 40, y + 44, 22, BLUE); T(c, 'Flight found', x + 64, y + 50, 20, { w: 700 }); T(c, '3 flights to London · best price shown', x + 196, y + 50, 14, { col: GREY });
      T(c, 'DXB', x + 40, y + 124, 40, { w: 700 }); T(c, '8:30 AM · Dubai', x + 40, y + 150, 14, { col: GREY });
      c.strokeStyle = '#CBD5E1'; c.setLineDash([5, 6]); c.lineWidth = 2; c.beginPath(); c.moveTo(x + 200, y + 110); c.lineTo(x + 560, y + 110); c.stroke(); c.setLineDash([]);
      const pp = still ? 0.5 : oc(sat((t - 33.3) / 1.2));
      drawIcon(c, 'plane', x + 200 + 360 * pp, y + 110, 24, BLUE); T(c, '7h 25m · Non-stop', x + 380, y + 146, 14, { col: GREY, align: 'center' });
      T(c, 'LHR', x + 600, y + 124, 40, { w: 700 }); T(c, '2:15 PM · London', x + 600, y + 150, 14, { col: GREY });
      T(c, 'AED 2,450', x + w - 40, y + 118, 30, { w: 700, align: 'right' }); T(c, 'Emirates EK007 · Wed 14 Oct', x + w - 40, y + 146, 14, { col: GREY, align: 'right' });
      c.fillStyle = LINE; c.fillRect(x + 32, y + 186, w - 64, 1);
      const bh = still ? 0 : hv(t, 35.7, 36.8), on = !still && t > 36.3;
      about(c, x + 140, y + 237, (1 + 0.05 * bh) * (still ? 1 : press(t, 36.3)), () => pill(c, 'Add to calendar', x + 32, y + 214, 46, { icon: 'calendar', size: 16, fill: on ? '#0F5FD6' : BLUE }));
      pill(c, 'View all flights', x + 260, y + 214, 46, { fill: 'rgba(16,24,40,0.05)', col: INK, icon: 'arrow-right', size: 16 });
      pill(c, 'Use in chat', x + 476, y + 214, 46, { fill: 'rgba(16,24,40,0.05)', col: INK, icon: 'message-circle', size: 16 });
      c.restore();
    }
  }

  calendarShot(c: X, t: number) {
    this.stage(c, t);
    const cam = camAt([[36.7, 1160, 440, 1.42], [38.0, 1160, 450, 1.38], [38.9, 1080, 470, 1.1], [40.4, 1060, 470, 1.08]], t);
    this.win(c, cam, t, () => this.calendarApp(c, t));
  }

  calendarApp(c: X, t: number, still = false) {
    this.nav(c, 'Calendar');
    c.fillStyle = 'rgba(250,252,255,0.96)'; c.fillRect(NAV, 0, SIDE, WH); c.fillStyle = LINE; c.fillRect(MX - 1, 0, 1, WH);
    T(c, 'Calendar', NAV + 24, 72, 28, { w: 700 });
    pill(c, 'New Event', NAV + 24, 98, 42, { icon: 'plus', size: 15 });
    T(c, 'October 2026', NAV + 26, 186, 16, { w: 600 });
    ['S', 'M', 'T', 'W', 'T', 'F', 'S'].forEach((d, i) => T(c, d, NAV + 44 + i * 46, 220, 12, { col: '#98A2B3', align: 'center' }));
    for (let d = 1; d <= 31; d++) {
      const i = d + 3, col = i % 7, row = Math.floor(i / 7), cx = NAV + 44 + col * 46, cy = 250 + row * 38;
      if (d === 14) { c.fillStyle = BLUE; c.beginPath(); c.arc(cx, cy - 5, 15, 0, 7); c.fill(); }
      T(c, String(d), cx, cy, 14, { col: d === 14 ? '#fff' : '#344054', align: 'center', w: d === 14 ? 700 : 400 });
    }
    T(c, 'My Calendars', NAV + 26, 520, 16, { w: 600 });
    ([['Personal', BLUE], ['Work', PURPLE], ['Travel', GREEN], ['Family', '#F59E0B']] as const).forEach(([n, col], i) => {
      c.fillStyle = col; rr(c, NAV + 26, 540 + i * 40, 20, 20, 6); c.fill(); drawIcon(c, 'check', NAV + 36, 550 + i * 40, 14, '#fff', 2.4);
      T(c, n, NAV + 58, 556 + i * 40, 15, { col: '#344054' });
    });
    c.fillStyle = 'rgba(255,255,255,0.97)'; c.fillRect(MX, 0, WW - MX, WH);
    T(c, 'October 2026', MX + 32, 64, 28, { w: 700 });
    c.fillStyle = 'rgba(16,24,40,0.05)'; rr(c, MX + 330, 36, 340, 40, 20); c.fill();
    ['Day', 'Week', 'Month', 'Agenda'].forEach((s, i) => {
      if (i === 1) { c.fillStyle = BLUE; rr(c, MX + 334 + i * 84, 40, 80, 32, 16); c.fill(); }
      T(c, s, MX + 374 + i * 84, 61, 14, { w: 600, col: i === 1 ? '#fff' : '#344054', align: 'center' });
    });
    pill(c, 'Today', WW - 130, 36, 40, { fill: 'rgba(22,119,255,0.10)', col: BLUE, size: 14 });
    const gx = MX + 90, gw = WW - gx - 30, cw = gw / 7, gy = 150, hh = 68;
    ['Sun 11', 'Mon 12', 'Tue 13', 'Wed 14', 'Thu 15', 'Fri 16', 'Sat 17'].forEach((d, i) => {
      const [a, b] = d.split(' ');
      T(c, a!, gx + i * cw + cw / 2, 108, 13, { col: GREY, align: 'center' });
      if (i === 3) { c.fillStyle = BLUE; c.beginPath(); c.arc(gx + i * cw + cw / 2, 132, 17, 0, 7); c.fill(); }
      T(c, b!, gx + i * cw + cw / 2, 138, 18, { w: 600, col: i === 3 ? '#fff' : INK, align: 'center' });
    });
    for (let h = 0; h <= 11; h++) { const y = gy + h * hh; c.fillStyle = LINE; c.fillRect(gx, y, gw, 1); T(c, `${((h + 7) % 12) + 1} ${h + 8 < 12 ? 'AM' : 'PM'}`, gx - 14, y + 5, 12, { col: '#98A2B3', align: 'right' }); }
    for (let i = 0; i <= 7; i++) { c.fillStyle = LINE; c.fillRect(gx + i * cw, gy, 1, 11 * hh); }
    let ei = 0;
    const ev = (day: number, h0: number, h1: number, title: string, sub: string, col: string) => {
      const k = still ? 1 : rv(t, 37.0, ei++, 0.05, 0.35);
      const x = gx + day * cw + 4, y = gy + (h0 - 8) * hh + 2, h = (h1 - h0) * hh - 4;
      c.save(); c.globalAlpha *= k;
      c.fillStyle = col + '22'; rr(c, x, y, cw - 8, h, 10); c.fill(); c.fillStyle = col; rr(c, x, y, 4, h, 2); c.fill();
      T(c, title, x + 12, y + 22, 13, { w: 600 }); T(c, sub, x + 12, y + 40, 12, { col: GREY });
      c.restore();
    };
    ev(1, 9, 10, 'Team Sync', '9:00 – 10:00', PURPLE); ev(2, 10.5, 11.5, 'Product Review', '10:30 – 11:30', BLUE);
    ev(1, 12, 13, 'Lunch with Omar', '12:00 – 1:00', '#F59E0B'); ev(4, 9, 10, 'Client Call', '9:00 – 10:00', PURPLE);
    ev(4, 13, 15, 'Focus Time', '1:00 – 3:00', BLUE); ev(5, 9.5, 10.5, 'Design Review', '9:30 – 10:30', '#EC4899');
    ev(1, 15, 16, 'Weekly Planning', '3:00 – 4:00', BLUE); ev(5, 12.5, 14, 'Family Time', '12:30 – 2:00', '#F59E0B');
    const k = still ? 1 : ob(sat((t - 37.3) / 0.7), 1.1);
    if (k > 0) {
      const x = gx + 3 * cw + 4, y = gy + 0.5 * hh + 2, w = cw - 8, h = 5.75 * hh - 4;
      const s = lerp(1.8, 1, k), ox = lerp(-200, 0, k), oy = lerp(220, 0, k);
      c.save(); c.translate(x + w / 2 + ox, y + h / 2 + oy); c.scale(s, s); c.translate(-(x + w / 2), -(y + h / 2));
      c.shadowColor = `rgba(34,197,94,${0.35 * (1 - sat(k))})`; c.shadowBlur = 30;
      c.fillStyle = 'rgba(34,197,94,0.16)'; rr(c, x, y, w, h, 10); c.fill(); c.shadowColor = 'transparent';
      c.fillStyle = GREEN; rr(c, x, y, 4, h, 2); c.fill();
      drawIcon(c, 'plane', x + 22, y + 22, 16, '#15803D');
      T(c, 'DXB → LHR', x + 38, y + 27, 14, { w: 700 }); T(c, 'EK007', x + 14, y + 50, 12, { col: GREY }); T(c, '8:30 AM – 2:15 PM', x + 14, y + 68, 12, { col: GREY });
      c.restore();
    }
    const ta = still ? 0 : oc(sat((t - 37.9) / 0.4)) * (1 - sat((t - 39.6) / 0.4));
    if (ta > 0) {
      c.save(); c.globalAlpha = ta;
      card(c, WW / 2 + 60, WH - 96 + (1 - ta) * 16, 300, 54, 27, { shadow: 1.2 });
      c.fillStyle = GREEN; c.beginPath(); c.arc(WW / 2 + 92, WH - 69 + (1 - ta) * 16, 12, 0, 7); c.fill(); drawIcon(c, 'check', WW / 2 + 92, WH - 69 + (1 - ta) * 16, 14, '#fff', 2.6);
      T(c, 'Added to your calendar', WW / 2 + 114, WH - 63 + (1 - ta) * 16, 15, { w: 600 });
      c.restore();
    }
  }

  // ================================================================ 5. Weather: summer, winter, rain, wind (40-44.6 s)
  weatherShot(c: X, t: number) {
    this.stage(c, t);
    const cam = camAt([[40.0, 930, 300, 1.18], [44.8, 950, 290, 1.32]], t); // one slow push: the clicks change the weather, not the framing
    const tabX = (i: number) => NAV + 470 + i * 104;
    const cur: Cursor = { show: [40.9, 44.6], clicks: WX_T.slice(1), path: [[40.9, 1100, 500], [41.75, tabX(1), 118], [42.75, tabX(2), 118], [43.75, tabX(3), 118], [44.6, tabX(3) + 40, 160]] };
    this.win(c, cam, t, () => this.weatherApp(c, t), cur);
  }

  weatherApp(c: X, t: number) {
    this.nav(c, 'Weather');
    const x0 = NAV, w = WW - NAV;
    let si = 0; for (let i = 0; i < WX.length; i++) if (t >= WX_T[i]!) si = i;
    const into = sat((t - WX_T[si]!) / 0.45), prev = WX[Math.max(0, si - 1)]!, cur = WX[si]!;
    photo(c, this.ph[`wx-${prev.id}`]!, x0, 0, w, 520, 0, 1.04);
    if (si > 0 && into < 1) { c.save(); c.globalAlpha = io(into); photo(c, this.ph[`wx-${cur.id}`]!, x0, 0, w, 520, 0, 1.1 - 0.06 * io(into)); c.restore(); }
    else photo(c, this.ph[`wx-${cur.id}`]!, x0, 0, w, 520, 0, 1.04);
    this.weatherFx(c, cur.id, t, x0, w, si > 0 ? io(into) : 1);
    const g = c.createLinearGradient(0, 300, 0, 520); g.addColorStop(0, 'rgba(255,255,255,0)'); g.addColorStop(1, 'rgba(255,255,255,1)');
    c.fillStyle = g; c.fillRect(x0, 300, w, 220); c.fillStyle = '#fff'; c.fillRect(x0, 520, w, WH - 520);
    card(c, NAV + 470 - 62, 92, 3 * 104 + 124, 52, 26, { fill: 'rgba(255,255,255,0.85)', shadow: 0.8 });
    const tx = (i: number) => NAV + 470 + i * 104;
    const px = si > 0 ? lerp(tx(si - 1), tx(si), oc(sat((t - WX_T[si]!) / 0.3))) : tx(0);
    c.fillStyle = BLUE; rr(c, px - 48, 98, 96, 40, 20); c.fill();
    WX.forEach((s, i) => T(c, s.tab, tx(i), 124, 15, { w: 600, col: i === si && sat((t - WX_T[si]!) / 0.15) > 0.5 ? '#fff' : '#344054', align: 'center' }));
    card(c, x0 + 40, 180, 560, 250, 28, { fill: 'rgba(255,255,255,0.82)', shadow: 0.8 });
    T(c, 'Dubai', x0 + 76, 236, 34, { w: 700 }); T(c, 'United Arab Emirates', x0 + 76, 264, 15, { col: GREY });
    const temp = si > 0 ? Math.round(lerp(prev.temp, cur.temp, oc(sat((t - WX_T[si]!) / 0.5)))) : cur.temp;
    c.save(); c.globalAlpha = si > 0 ? 0.3 + 0.7 * oc(into) : 1;
    drawIcon(c, cur.icon, x0 + 120, 336, 64, cur.iconCol, 2.2);
    c.restore();
    T(c, `${temp}°C`, x0 + 180, 366, 78, { w: 600 });
    T(c, cur.cond, x0 + 400, 340, 18, { w: 600 }); T(c, cur.feels, x0 + 400, 364, 15, { col: GREY });
    [['droplets', 'Humidity', cur.hum], ['wind', 'Wind', cur.wind]].forEach(([ic, a, b], i) => { drawIcon(c, ic!, x0 + 86 + i * 220, 404, 18, GREY); T(c, `${a} ${b}`, x0 + 104 + i * 220, 409, 14, { col: '#344054' }); });
    T(c, 'Today', x0 + 40, 560, 20, { w: 700 });
    ['Now', '10 AM', '11 AM', '12 PM', '1 PM', '2 PM', '3 PM', '4 PM', '5 PM', '6 PM'].forEach((h, i) => {
      const k = oc(sat((t - WX_T[si]! - i * 0.03) / 0.3)), x = x0 + 40 + i * 146, y = 586;
      card(c, x, y, 130, 150, 20, { fill: i === 0 ? 'rgba(22,119,255,0.08)' : '#fff', shadow: 0.4 });
      T(c, h, x + 65, y + 34, 14, { col: i === 0 ? BLUE : GREY, align: 'center', w: 600 });
      c.save(); c.globalAlpha = 0.4 + 0.6 * k; drawIcon(c, cur.icon, x + 65, y + 76, 30, cur.iconCol, 2); c.restore();
      T(c, `${cur.temp + Math.round(3 * Math.sin(i * 0.6))}°`, x + 65, y + 128, 22, { w: 600, align: 'center' });
    });
  }

  /** Live weather over the hero: snow, rain streaks, blowing dust, summer glare. */
  weatherFx(c: X, id: string, t: number, x0: number, w: number, a: number) {
    c.save(); c.beginPath(); c.rect(x0, 0, w, 380); c.clip(); c.globalAlpha = a; // inside the picture only (it fades to white below)
    if (id === 'winter') {
      c.fillStyle = 'rgba(255,255,255,0.9)';
      for (let i = 0; i < 160; i++) { const s = 1.5 + 3 * hash(i, 1), y = ((hash(i, 2) * 560 + t * (40 + 60 * hash(i, 3))) % 560) - 20, x = x0 + ((hash(i, 4) * w + 30 * Math.sin(t + i)) % w); c.beginPath(); c.arc(x, y, s, 0, 7); c.fill(); }
    } else if (id === 'rain') {
      c.strokeStyle = 'rgba(220,235,255,0.55)'; c.lineWidth = 1.5;
      for (let i = 0; i < 220; i++) { const y = ((hash(i, 2) * 600 + t * (900 + 300 * hash(i, 3))) % 600) - 40, x = x0 + hash(i, 4) * w; c.beginPath(); c.moveTo(x, y); c.lineTo(x - 6, y + 26); c.stroke(); }
    } else if (id === 'wind') {
      c.strokeStyle = 'rgba(255,230,190,0.45)'; c.lineCap = 'round';
      for (let i = 0; i < 60; i++) { const y = hash(i, 2) * 500, x = x0 + ((hash(i, 4) * w + t * (700 + 500 * hash(i, 3))) % (w + 300)) - 150, l = 60 + 140 * hash(i, 5); c.lineWidth = 1 + 2 * hash(i, 6); c.beginPath(); c.moveTo(x, y); c.quadraticCurveTo(x + l / 2, y - 6, x + l, y); c.stroke(); }
    } else {
      const g = c.createRadialGradient(x0 + w * 0.82, 60, 10, x0 + w * 0.82, 60, 420); g.addColorStop(0, 'rgba(255,240,200,0.55)'); g.addColorStop(1, 'rgba(255,240,200,0)');
      c.fillStyle = g; c.fillRect(x0, 0, w, 520);
    }
    c.restore();
  }

  // ================================================================ 6. Stocks (44.6-46.4 s) and Mail (46.4-51 s)
  stocksPath: PKey[] = [[45.1, 900, 860], [45.9, 1200, 720], [46.6, 1340, 690]];
  stocksShot(c: X, t: number) {
    this.stage(c, t);
    const cur: Cursor = { show: [45.1, 46.6], clicks: [], path: this.stocksPath };
    this.win(c, camAt([[44.6, 1060, 470, 1.12], [46.6, 1180, 640, 1.32]], t), t, () => this.stocksApp(c, t), cur);
  }
  stocksApp(c: X, t: number) {
    this.nav(c, 'Stocks');
    c.fillStyle = '#fff'; c.fillRect(NAV, 0, WW - NAV, WH);
    T(c, 'Stocks & Markets', NAV + 40, 72, 30, { w: 700 });
    card(c, NAV + 360, 36, 620, 52, 26, { shadow: 0.4 }); drawIcon(c, 'sparkles', NAV + 392, 62, 18, PURPLE); T(c, 'Ask Messenger AI about any stock, market or investment…', NAV + 414, 68, 15, { col: '#98A2B3' });
    [['S&P 500', '5,274.12', '+0.92%'], ['NASDAQ', '16,735.02', '+0.94%'], ['DOW JONES', '39,387.76', '+0.85%'], ['DAX', '18,492.21', '+0.61%']].forEach(([n, v, d], i) => {
      const k = rv(t, 44.8, i, 0.06), x = NAV + 40 + i * 368;
      c.save(); c.globalAlpha = k;
      card(c, x, 116 + (1 - k) * 16, 348, 110, 20, { shadow: 0.5 });
      T(c, n!, x + 22, 150, 13, { col: GREY, w: 600 }); T(c, v!, x + 22, 186, 24, { w: 700 }); T(c, d!, x + 22, 210, 13, { col: '#16A34A', w: 600 });
      c.strokeStyle = '#22C55E'; c.lineWidth = 2; c.beginPath();
      for (let q = 0; q <= 30; q++) { const yy = 190 - 18 * (q / 30) - 8 * Math.sin(q * 0.9 + i) * (hash(q, i) - 0.3); (q ? c.lineTo(x + 220 + q * 3.8, yy) : c.moveTo(x + 220, yy)); }
      c.stroke(); c.restore();
    });
    card(c, NAV + 40, 252, WW - NAV - 80, 660, 24, { shadow: 0.6 });
    const x = NAV + 72, y = 290;
    c.fillStyle = INK; rr(c, x, y, 44, 44, 12); c.fill(); T(c, 'A', x + 22, y + 30, 22, { w: 700, col: '#fff', align: 'center' });
    T(c, 'AAPL', x + 60, y + 20, 18, { w: 700 }); T(c, 'Apple Inc.', x + 60, y + 42, 14, { col: GREY });
    T(c, '224.91', x, y + 116, 54, { w: 700 }); T(c, 'USD', x + 186, y + 116, 18, { col: GREY }); T(c, '+2.13 (+0.95%)', x + 240, y + 116, 20, { col: '#16A34A', w: 600 });
    ['1D', '1W', '1M', '6M', '1Y', 'MAX'].forEach((s, i) => { if (!i) { c.fillStyle = BLUE; rr(c, x + i * 70, y + 146, 60, 32, 16); c.fill(); } T(c, s, x + 30 + i * 70, y + 167, 13, { w: 600, col: i ? GREY : '#fff', align: 'center' }); });
    const cx0 = x, cx1 = WW - 120, cy0 = y + 220, cy1 = y + 580;
    const draw = oc(sat((t - 44.8) / 1.0)), N = 120, pts: [number, number][] = [];
    const val = (u: number, k: number) => 0.35 + 0.45 * u + 0.08 * Math.sin(u * 9) + 0.05 * Math.sin(u * 23) + 0.03 * (hash(k, 5) - 0.5);
    for (let k = 0; k <= N * draw; k++) { const u = k / N; pts.push([lerp(cx0, cx1, u), lerp(cy1, cy0, val(u, k))]); }
    if (pts.length > 1) {
      const g = c.createLinearGradient(0, cy0, 0, cy1); g.addColorStop(0, 'rgba(34,197,94,0.22)'); g.addColorStop(1, 'rgba(34,197,94,0)');
      c.beginPath(); c.moveTo(pts[0]![0], cy1); pts.forEach(([px, py]) => c.lineTo(px, py)); c.lineTo(pts[pts.length - 1]![0], cy1); c.fillStyle = g; c.fill();
      c.beginPath(); pts.forEach(([px, py], i) => (i ? c.lineTo(px, py) : c.moveTo(px, py))); c.strokeStyle = '#22C55E'; c.lineWidth = 3; c.stroke();
    }
    const hA = sat((t - 45.5) / 0.2);
    if (hA > 0 && pts.length > 60) {
      const [hx] = pathAt(this.stocksPath, t);
      const u = clamp((hx - cx0) / (cx1 - cx0)), k = Math.round(u * N), hy = lerp(cy1, cy0, val(u, k));
      c.save(); c.globalAlpha = hA;
      c.strokeStyle = 'rgba(16,24,40,0.25)'; c.setLineDash([4, 5]); c.beginPath(); c.moveTo(hx, cy0); c.lineTo(hx, cy1); c.stroke(); c.setLineDash([]);
      c.fillStyle = '#fff'; c.strokeStyle = '#22C55E'; c.lineWidth = 3; c.beginPath(); c.arc(hx, hy, 7, 0, 7); c.fill(); c.stroke();
      card(c, hx + 16, hy - 74, 168, 60, 14, { shadow: 1.2 });
      T(c, `$${(214 + 14 * val(u, k)).toFixed(2)}`, hx + 32, hy - 46, 17, { w: 700 }); T(c, `${10 + Math.floor(u * 6)}:${String(Math.floor((u * 360) % 60)).padStart(2, '0')} AM`, hx + 32, hy - 26, 12, { col: GREY });
      c.restore();
    }
  }

  mailShot(c: X, t: number) {
    this.stage(c, t);
    const cam = camAt([[46.4, 700, 360, 1.3], [47.6, 560, 300, 1.38], [48.6, 1100, 380, 1.18], [49.4, 1380, 260, 1.36], [51.2, 1380, 280, 1.36]], t);
    const cur: Cursor = { show: [46.8, 50.8], clicks: [47.55, 49.55], path: [[46.8, 760, 500], [47.4, 470, 150], [47.8, 470, 150], [49.3, 1590, 136], [50.0, 1590, 136], [50.8, 1560, 300]] };
    this.win(c, cam, t, () => this.mailApp(c, t), cur);
  }
  mailApp(c: X, t: number) {
    this.nav(c, 'Mail');
    c.fillStyle = 'rgba(250,252,255,0.96)'; c.fillRect(NAV, 0, SIDE, WH); c.fillStyle = LINE; c.fillRect(MX - 1, 0, 1, WH);
    T(c, 'Mail', NAV + 24, 72, 28, { w: 700 });
    const list: [string, string, string, string, string][] = [['Emirates', 'Your booking is confirmed', 'Booking reference EK4Z9H', '9:14 AM', '#D71921'], ['Booking.com', 'Your Dubai stay is confirmed', 'Rove Downtown · 12–16 Dec', '8:47 AM', '#003580'], ['Team Messenger', 'Weekly product update', 'New features and improvements', 'Yesterday', BLUE], ['IDC Technologies', 'QA Automation (Arabic Speaker)', 'Next steps for the interview', 'Mon', '#0EA5E9'], ['NeoHealth', 'Partnership opportunity', 'AI-powered front desk', 'Mon', '#16A34A'], ['LinkedIn', '5 new job recommendations', 'AI Engineer, Dubai', 'Sun', '#0A66C2'], ['GitHub', '[Messenger] 3 new notifications', '2 pull requests, 1 comment', 'Sun', '#24292F']];
    const opened = t > 47.55, rh = hv(t, 47.2, 48.0);
    list.forEach(([f, s, p, tm, col], i) => {
      const k = rv(t, 46.5, i, 0.06, 0.4), y = 104 + i * 92 + (1 - k) * 18;
      c.save(); c.globalAlpha = k;
      if (i === 0 && (opened || rh > 0)) { c.fillStyle = `rgba(22,119,255,${opened ? 0.08 : 0.05 * rh})`; rr(c, NAV + 12, y, SIDE - 24, 86, 14); c.fill(); }
      about(c, NAV + 190, y + 43, i === 0 ? press(t, 47.55) : 1, () => {
        c.fillStyle = col; rr(c, NAV + 28, y + 18, 40, 40, 12); c.fill();
        T(c, f[0]!, NAV + 48, y + 44, 18, { w: 700, col: '#fff', align: 'center' });
        T(c, f, NAV + 82, y + 30, 15, { w: 600 }); T(c, tm, MX - 24, y + 30, 12, { col: GREY, align: 'right' });
        T(c, s, NAV + 82, y + 52, 14); T(c, p, NAV + 82, y + 72, 13, { col: GREY });
      });
      c.restore();
    });
    c.fillStyle = '#fff'; c.fillRect(MX, 0, WW - MX, WH);
    if (!opened) { drawIcon(c, 'mail', (MX + WW) / 2, 440, 44, '#CBD5E1'); T(c, 'Select an email to read', (MX + WW) / 2, 500, 16, { col: '#98A2B3', align: 'center' }); return; }
    const x = MX + 40, rw = WW - MX - 440;
    const R = (i: number) => rv(t, 47.7, i, 0.1, 0.45);
    c.save(); c.globalAlpha = R(0); T(c, 'Your booking is confirmed', x, 76 + (1 - R(0)) * 14, 26, { w: 700 }); c.restore();
    c.save(); c.globalAlpha = R(1);
    c.fillStyle = '#D71921'; rr(c, x, 100, 44, 44, 12); c.fill(); T(c, 'E', x + 22, 130, 20, { w: 700, col: '#fff', align: 'center' });
    T(c, 'Emirates', x + 58, 118, 15, { w: 600 }); T(c, 'noreply@emirates.com · to me', x + 58, 138, 13, { col: GREY });
    c.restore();
    c.save(); c.globalAlpha = R(2); about(c, x + rw / 2, 310, 0.96 + 0.04 * R(2), () => {
      photo(c, this.ph.london!, x, 170, rw, 280, 20);
      const g = c.createLinearGradient(x, 0, x + rw, 0); g.addColorStop(0, 'rgba(12,30,70,0.75)'); g.addColorStop(0.6, 'rgba(12,30,70,0)');
      c.fillStyle = g; rr(c, x, 170, rw, 280, 20); c.fill();
      T(c, 'Your journey', x + 36, 290, 40, { w: 700, col: '#fff' }); T(c, 'is confirmed', x + 36, 338, 40, { w: 700, col: '#fff' });
    }); c.restore();
    c.save(); c.globalAlpha = R(3); c.translate(0, (1 - R(3)) * 16);
    card(c, x, 474, rw, 120, 18, { shadow: 0.4 });
    T(c, 'Dubai (DXB)', x + 28, 516, 14, { col: GREY }); T(c, '10:30', x + 28, 556, 28, { w: 700 });
    drawIcon(c, 'plane', x + rw / 2, 534, 22, BLUE); T(c, 'EK007 · 7h 25m', x + rw / 2, 570, 13, { col: GREY, align: 'center' });
    T(c, 'London (LHR)', x + rw - 28, 516, 14, { col: GREY, align: 'right' }); T(c, '14:55', x + rw - 28, 556, 28, { w: 700, align: 'right' });
    c.restore();
    c.save(); c.globalAlpha = R(4); c.translate(0, (1 - R(4)) * 16);
    [['Passenger', '1 Adult'], ['Class', 'Economy'], ['Reference', 'EK4Z9H']].forEach(([a, b], i) => { const bx = x + i * ((rw + 16) / 3); card(c, bx, 614, (rw - 32) / 3, 74, 16, { shadow: 0.3 }); T(c, a!, bx + 20, 644, 13, { col: GREY }); T(c, b!, bx + 20, 668, 16, { w: 600 }); });
    c.restore();
    const sx = WW - 380, k = R(3);
    c.save(); c.globalAlpha = k; c.translate((1 - k) * 30, 0);
    const opened2 = t > 49.55, sh2 = hv(t, 49.2, 50.2);
    card(c, sx, 100, 340, opened2 ? 290 : 96, 22, { fill: 'rgba(247,243,255,0.96)', shadow: 0.8 + sh2, border: 'rgba(124,58,237,0.16)' });
    drawIcon(c, 'sparkles', sx + 32, 136, 20, PURPLE); T(c, 'Messenger AI', sx + 52, 142, 15, { w: 600 });
    about(c, sx + 260, 136, (1 + 0.06 * sh2) * press(t, 49.55), () => pill(c, 'Summarize', sx + 204, 120, 32, { fill: opened2 ? PURPLE : `rgba(124,58,237,${0.12 + 0.12 * sh2})`, col: opened2 ? '#fff' : PURPLE, size: 13, pad: 12 }));
    if (opened2) {
      const sum = 'Your Emirates flight EK007 from Dubai to London on 12 Dec is confirmed. 1 passenger, Economy. Booking reference EK4Z9H.';
      const n = Math.floor(sat((t - 49.75) / 0.9) * sum.length);
      wrap(c, sum.slice(0, n), 290, 15).forEach((l, i) => T(c, l, sx + 26, 196 + i * 24, 15, { col: '#344054' }));
      c.globalAlpha *= sat((t - 50.6) / 0.3);
      pill(c, 'Add to Calendar', sx + 24, 330, 36, { fill: 'rgba(22,119,255,0.10)', col: BLUE, size: 13, icon: 'calendar-plus' });
      pill(c, 'Track flight', sx + 196, 330, 36, { fill: 'rgba(22,119,255,0.10)', col: BLUE, size: 13, icon: 'plane' });
    }
    c.restore();
  }

  // ================================================================ 7. Profile (50.9-55.5 s)
  profileShot(c: X, t: number) {
    this.stage(c, t);
    const cam = camAt([[50.9, 260, 780, 1.5], [51.6, 260, 790, 1.5], [52.4, 860, 480, 1.1], [55.5, 860, 470, 1.14]], t);
    const cur: Cursor = { show: [50.9, 54.6], clicks: [51.35], path: [[50.9, 300, 760], [51.25, 44, 912], [51.7, 44, 912], [53.4, 1150, 470], [54.6, 1200, 520]] };
    this.win(c, cam, t, () => {
      const open = oc(sat((t - 51.5) / 0.55));
      c.save(); if (open > 0) c.filter = `blur(${10 * open}px)`;
      this.chatsApp(c, 19.5, true);
      this.nav(c, 'Chats', hv(t, 51.0, 51.7));
      c.restore();
      if (open <= 0) return;
      c.fillStyle = `rgba(240,245,252,${0.45 * open})`; c.fillRect(0, 0, WW, WH);
      const mw = 980, mh = 680, mx = (WW - mw) / 2, my = (WH - mh) / 2 + (1 - open) * 30;
      c.save(); c.globalAlpha = open;
      about(c, WW / 2, WH / 2, 0.96 + 0.04 * open, () => {
        card(c, mx, my, mw, mh, 28, { fill: 'rgba(255,255,255,0.94)', shadow: 2 });
        c.fillStyle = 'rgba(246,248,252,0.9)'; rr(c, mx, my, 240, mh, 28); c.fill(); c.fillRect(mx + 200, my, 40, mh);
        T(c, 'Profile', mx + 28, my + 52, 20, { w: 700 });
        [['user', 'Profile'], ['shield', 'Account'], ['star', 'Subscription'], ['house', 'Devices'], ['folder', 'Storage'], ['lock', 'Data & Privacy'], ['bell', 'Notifications'], ['sparkles', 'AI Preferences']].forEach(([ic, s], i) => {
          const y = my + 86 + i * 48, k = rv(t, 51.8, i, 0.04);
          c.save(); c.globalAlpha *= k;
          if (!i) { c.fillStyle = 'rgba(22,119,255,0.10)'; rr(c, mx + 14, y, 212, 40, 12); c.fill(); }
          drawIcon(c, ic!, mx + 40, y + 20, 18, i ? '#475467' : BLUE); T(c, s!, mx + 62, y + 26, 15, { w: i ? 500 : 600, col: i ? '#344054' : BLUE });
          c.restore();
        });
        const px = mx + 280;
        T(c, 'Profile', px, my + 56, 26, { w: 700 }); T(c, 'Manage your personal information and account details.', px, my + 82, 14, { col: GREY });
        drawIcon(c, 'x', mx + mw - 40, my + 44, 20, GREY);
        card(c, px, my + 106, mw - 320, 120, 20, { shadow: 0.3 });
        avatar(c, this.ph.av12!, px + 64, my + 166, 40, true);
        T(c, 'Haitham', px + 124, my + 158, 22, { w: 700 });
        c.fillStyle = GREEN; c.beginPath(); c.arc(px + 130, my + 182, 4, 0, 7); c.fill(); T(c, 'Online', px + 140, my + 187, 14, { col: GREY });
        pill(c, 'Edit', mx + mw - 120, my + 146, 36, { fill: 'rgba(16,24,40,0.05)', col: INK, size: 14 });
        [['user', 'Full name', 'Haitham'], ['mail', 'Email', 'haitham@messenger.app'], ['phone', 'Phone', '+971 50 123 4567'], ['map-pin', 'Location', 'Dubai, UAE'], ['globe', 'Language', 'English']].forEach(([ic, a, b], i) => {
          const y = my + 262 + i * 58, kk = rv(t, 52.0, i, 0.07), hov = i === 3 ? hv(t, 53.3, 54.5) : 0;
          c.save(); c.globalAlpha *= kk; c.translate(0, (1 - kk) * 12);
          if (hov > 0) { c.fillStyle = `rgba(22,119,255,${0.06 * hov})`; rr(c, px - 10, y - 4, mw - 300, 46, 12); c.fill(); }
          drawIcon(c, ic!, px + 20, y + 18, 18, GREY); T(c, a!, px + 46, y + 24, 15, { col: '#344054' }); T(c, b!, px + 300, y + 24, 15);
          drawIcon(c, 'chevron-right', mx + mw - 54, y + 18, 16, '#98A2B3');
          c.fillStyle = LINE; c.fillRect(px, y + 44, mw - 320, 1);
          c.restore();
        });
        T(c, 'Status', px, my + 580, 15, { w: 600 }); T(c, 'This will be visible to your contacts.', px, my + 602, 13, { col: GREY });
        pill(c, 'Online', mx + mw - 150, my + 574, 34, { fill: 'rgba(34,197,94,0.12)', col: '#15803D', size: 13 });
      });
      c.restore();
    }, cur);
  }

  // ================================================================ 8. the finale (55.5-60 s)
  thumb(id: string) {
    let cv = this.thumbs[id];
    if (!cv) {
      cv = document.createElement('canvas'); cv.width = WW; cv.height = WH;
      const c = cv.getContext('2d')!;
      c.fillStyle = '#fff'; rr(c, 0, 0, WW, WH, 26); c.fill(); c.save(); rr(c, 0, 0, WW, WH, 26); c.clip();
      if (id === 'chats') this.chatsApp(c, 19.5, true);
      if (id === 'ai') this.aiApp(c, 31, true);
      if (id === 'flights') this.flightsApp(c, 36, true);
      if (id === 'calendar') this.calendarApp(c, 40, true);
      if (id === 'weather') this.weatherApp(c, 43.0);
      if (id === 'stocks') this.stocksApp(c, 46.4);
      c.restore();
      this.thumbs[id] = cv;
    }
    return cv;
  }
  finaleShot(c: X, t: number) {
    this.stage(c, t);
    const ids = ['chats', 'ai', 'calendar', 'weather', 'flights', 'stocks'];
    const pos: [number, number, number][] = [[-560, -250, 0.30], [560, -250, 0.30], [-640, 230, 0.26], [640, 240, 0.27], [0, -380, 0.22], [0, 400, 0.22]];
    const recede = io(pr(t, 55.5, 60)), fade = 1 - io(pr(t, 57.4, 59.0));
    ids.forEach((id, i) => {
      const [px, py, s] = pos[i]!;
      const k = s * (1 - 0.18 * recede), dx = px * (1 + 0.12 * recede), dy = py * (1 + 0.12 * recede);
      c.save(); c.globalAlpha = fade * (0.55 + 0.45 * (s / 0.3));
      c.translate(SW / 2 + dx, SH / 2 + dy); c.scale(k, k);
      c.shadowColor = 'rgba(30,60,110,0.20)'; c.shadowBlur = 60; c.shadowOffsetY = 20;
      c.drawImage(this.thumb(id), -WW / 2, -WH / 2);
      c.restore();
    });
    const a = oc(sat((t - 56.3) / 0.9));
    c.save(); c.globalAlpha = a;
    c.translate(SW / 2, SH / 2); const z = 0.94 + 0.06 * a; c.scale(z, z);
    this.mTile(c, -230, -10, 130);
    T(c, 'Messenger', -140, -4, 110, { w: 600, base: 'middle' });
    c.globalAlpha = sat((t - 57.2) / 0.9);
    T(c, 'Your chats, with a private assistant.', 0, 120, 32, { col: GREY, align: 'center' });
    c.restore();
  }

  // ================================================================ compositing and transitions
  override render(f: Frame, out: THREE.WebGLRenderTarget): PostOverrides {
    const { renderer, comp } = this.ctx;
    const t = f.t;
    let i = 0;
    for (let k = 0; k < this.shots.length; k++) if (t >= this.shots[k]!.t0) i = k;
    const cur = this.shots[i]!, prev = this.shots[i - 1];
    const lt = t - cur.t0, inT = cur.dur > 0 && prev ? sat(lt / cur.dur) : 1;
    clearRT(renderer, out, LIN.bone);
    const U = this.ui; U.clear('#EEF3FA');
    const x = U.ctx;
    if (inT >= 1 || !prev) cur.draw(x, t);
    else {
      const k = io(inT);
      this.A.clear('#EEF3FA'); prev.draw(this.A.ctx, t);
      this.B.clear('#EEF3FA'); cur.draw(this.B.ctx, t);
      const a = this.A.canvas, b = this.B.canvas;
      const put = (cv: HTMLCanvasElement, alpha: number, o: { blur?: number; s?: number; dx?: number; dy?: number } = {}) => {
        x.save(); x.globalAlpha = alpha; if (o.blur) x.filter = `blur(${o.blur}px)`;
        const s = o.s ?? 1; x.translate(SW / 2 + (o.dx ?? 0), SH / 2 + (o.dy ?? 0)); x.scale(s, s);
        x.drawImage(cv, -SW / 2, -SH / 2, SW, SH); x.restore();
      };
      switch (cur.into) {
        case 'rise': put(a, 1); put(b, k, { s: lerp(0.94, 1, k), dy: lerp(160, 0, k) }); break;
        case 'glass': put(a, 1, { blur: 22 * k }); x.fillStyle = `rgba(255,255,255,${0.35 * Math.sin(Math.PI * k)})`; x.fillRect(0, 0, SW, SH); put(b, k, { dx: lerp(420, 0, k) }); break;
        case 'blur': put(a, 1 - k, { blur: 26 * k }); put(b, k, { blur: 26 * (1 - k), s: lerp(1.02, 1, k) }); break;
        case 'match': put(a, 1); put(b, k); break;
        case 'depth': put(a, 1 - k, { s: lerp(1, 0.82, k), blur: 8 * k }); put(b, k, { s: lerp(1.06, 1, k) }); break;
        default: put(b, 1);
      }
    }
    comp.draw(renderer, U.upload(), out);
    return {};
  }
}
