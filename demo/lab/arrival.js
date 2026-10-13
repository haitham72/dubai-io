// Visitor arrival (case C14), told the way an iPhone does it: Wi-Fi settings
// -> join the airport network -> the captive sign-in sheet appears -> "Get
// online now" -> the sponsored page offers the app -> install sheet (GET ->
// progress -> OPEN) -> the icon expands into the app.
// Unbranded on purpose: no airport, telecom or store names or logos
// (CLAUDE.md rule 5; a look-alike of a real company's page is impersonation).
import { $, svg, esc, toast, wait, reduced } from './ui.js';

const SHOTS = ['media/guide-gate.jpg', 'media/marina.jpg', 'media/laundry.jpg'];

export function mountArrival(root) {
  root.innerHTML = `
    <div class="ar-screen ar-settings" id="arSettings">
      <div class="ios-nav"><span class="ios-back">${svg('back', 'ic sm')} Settings</span><b>Wi-Fi</b><span></span></div>
      <div class="ios-group"><div class="ios-row"><span>Wi-Fi</span><span class="ios-switch on"></span></div></div>
      <p class="ios-caption">NETWORKS</p>
      <div class="ios-group" id="arNets">
        <button class="ios-row net" id="arJoin"><span class="net-name">Airport Free Wi-Fi (demo)</span><span class="net-ic" id="arSpin">${svg('wifi', 'ic sm')}</span></button>
        <div class="ios-row net dim"><span class="net-name">Lounge Guest (demo)</span><span class="net-ic">${svg('lock', 'ic xs')} ${svg('wifi', 'ic sm')}</span></div>
        <div class="ios-row net dim"><span class="net-name">Gate Services (demo)</span><span class="net-ic">${svg('lock', 'ic xs')} ${svg('wifi', 'ic sm')}</span></div>
      </div>
      <p class="ios-hint">You just landed. Join the free airport Wi-Fi to continue.</p>
    </div>

    <div class="ar-sheet ar-captive" id="arCaptive" aria-label="Wi-Fi sign-in">
      <div class="cap-bar"><button id="capCancel">Cancel</button><b>Airport Free Wi-Fi</b><span></span></div>
      <div class="cap-page" id="capPage">
        <div class="cap-sponsor"><span class="app-ic sm"></span><span>Free Wi-Fi · sponsored by <b>Dubai-io</b></span></div>
        <div class="cap-hero" style="background-image:url('media/airport-plane.jpg')">
          <p class="cap-kicker">Welcome to Dubai</p>
          <h1>Free Wi-Fi for arriving passengers</h1>
        </div>
        <div class="cap-body" id="capBody">
          <button class="cap-btn" id="capOnline">Get online now</button>
          <p class="cap-terms">By continuing you accept the terms of use (demo).</p>
        </div>
      </div>
    </div>

    <div class="ar-sheet ar-install" id="arInstall" aria-label="Install Dubai-io">
      <div class="ins-grab"></div>
      <div class="ins-head">
        <span class="app-ic lg" id="arIcon"></span>
        <div class="ins-title"><b>Dubai-io</b><span>Your Dubai companion</span>
          <button class="get" id="arGet"><span class="get-txt">GET</span><svg class="ring" viewBox="0 0 36 36" aria-hidden="true"><circle cx="18" cy="18" r="15" /><circle class="prog" cx="18" cy="18" r="15" /></svg></button></div>
      </div>
      <div class="ins-chips"><span>Free</span><span>Travel</span><span>Works offline for the arrival guide</span></div>
      <div class="ins-shots">${SHOTS.map(s => `<span style="background-image:url('${s}')"></span>`).join('')}</div>
      <p class="ins-desc">Gate to hotel, step by step. Remembers your taxi in case you leave something behind. Shops nearby at their published prices, and you approve anything that leaves your phone.</p>
      <p class="ins-fine">Install flow mock for the demo. No store is involved.</p>
    </div>
    <div class="ar-launch" id="arLaunch"></div>`;
}

export function startArrival(onDone) {
  const P = $('#portal');
  P.hidden = false; P.className = 'portal';
  document.getElementById('app').classList.add('mode-portal');
  mountArrival(P);
  requestAnimationFrame(() => P.classList.add('in'));

  $('#arJoin').addEventListener('click', async () => {
    $('#arSpin').innerHTML = '<span class="spin"></span>';
    await wait(900);
    $('#arSpin').innerHTML = svg('check', 'ic sm');
    P.classList.add('captive');
  });
  $('#capCancel').addEventListener('click', () => { P.classList.remove('captive'); toast('Without signing in, the Wi-Fi stays offline.'); $('#arSpin').innerHTML = svg('wifi', 'ic sm'); });
  $('#capOnline').addEventListener('click', async () => {
    const b = $('#capOnline'); b.disabled = true; b.innerHTML = '<span class="spin light"></span> Connecting';
    await wait(1100);
    $('#capBody').innerHTML = `
      <div class="cap-ok">${svg('check', 'ic sm')} You’re online (demo)</div>
      <div class="cap-promo">
        <span class="app-ic"></span>
        <div><b>Get through arrivals faster</b><p>Dubai-io guides you from the gate to your taxi, remembers the taxi for you, and finds shops nearby at their published prices.</p></div>
      </div>
      <button class="cap-btn primary" id="capGet">Get the Dubai-io app</button>
      <button class="cap-link" id="capSkip">Not now</button>`;
    $('#capGet').addEventListener('click', () => P.classList.add('install'));
    $('#capSkip').addEventListener('click', () => toast('You can get the app any time. This demo continues with it.'));
  });

  let state = 'get';
  $('#arGet').addEventListener('click', async () => {
    const g = $('#arGet');
    if (state === 'get') {
      state = 'loading'; g.classList.add('loading'); g.querySelector('.get-txt').textContent = '';
      await wait(1900);
      state = 'open'; g.classList.remove('loading'); g.classList.add('open'); g.querySelector('.get-txt').textContent = 'OPEN';
      return;
    }
    if (state === 'open') launch(onDone);
  });
}

// The icon grows from its place in the sheet to fill the screen, then the app shows.
async function launch(onDone) {
  const P = $('#portal');
  const from = $('#arIcon').getBoundingClientRect(), app = document.getElementById('app').getBoundingClientRect();
  const L = $('#arLaunch');
  Object.assign(L.style, { left: from.left - app.left + 'px', top: from.top - app.top + 'px', width: from.width + 'px', height: from.height + 'px', borderRadius: '22%' });
  L.classList.add('go');
  await wait(30);
  Object.assign(L.style, { left: '0px', top: '0px', width: app.width + 'px', height: app.height + 'px', borderRadius: '0px' });
  await wait(reduced ? 0 : 520);
  P.classList.add('out');
  onDone?.();
  await wait(reduced ? 0 : 650);
  P.hidden = true; P.className = 'portal'; P.innerHTML = '';
  document.getElementById('app').classList.remove('mode-portal');
}
