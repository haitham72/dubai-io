// DXB arrival guide (case C5). Signage-based steps the user confirms; it never
// claims an indoor position, belt, gate or queue time (CLAUDE.md rule 3).
// "I'm lost" resumes from a landmark the user can see. The ride step reasons
// from Dubai time and terminal (Metro serves T1 and T3, not T2).
import { $, svg, esc, toast, openSheet, closeSheet, told, dubaiNow } from './ui.js';

const STEPS = [
  { id: 'gate', title: 'Off the plane', img: 'media/guide-gate.jpg', look: 'Gate numbers, "Arrivals" signs',
    body: 'Follow the Arrivals signs. Depending on your gate, a short airport train may link your concourse to passport control. Follow the signs and the staff.' },
  { id: 'passport', title: 'Passport control', img: 'media/guide-passport.jpg', look: 'Passport counters or smart gates',
    body: 'Have your passport and any visa or entry document ready. Smart gates may be available if you are eligible; otherwise use the counters. I won’t guess your eligibility: the signs and officers decide.' },
  { id: 'baggage', title: 'Baggage reclaim', img: 'media/guide-baggage.jpg', look: 'Baggage belts and flight screens', belt: true,
    body: 'Find your flight on the screens to see your belt number. I don’t guess belts. Tell me the number and I’ll remember it.' },
  { id: 'customs', title: 'Customs', img: 'media/guide-customs.jpg', look: 'Green and red channel signs',
    body: 'Nothing to declare: use the green channel. Items to declare: use the red channel. The official customs guidance has the full list.' },
  { id: 'arrivals', title: 'Arrivals hall', img: 'media/guide-arrivals.jpg', look: 'Meeting points, people waiting',
    body: 'You’re landside. There are usually ATMs, telecom counters and meeting points here. Ready for your ride?' },
  { id: 'ride', title: 'Your ride', img: 'media/guide-taxi.jpg', look: 'Taxi rank or Metro signs', ride: true,
    body: '' },
];

// Published Metro hours (Red Line). Check RTA before you travel.
function metroState(t) {
  const open = t.day === 'Sun' ? 8 : 5;
  const friLate = t.day === 'Sat' && t.h < 1; // Friday service runs to 01:00
  const running = friLate || (t.h >= open);   // closes at 00:00 (01:00 on Friday)
  return { running, opens: `${String(open).padStart(2, '0')}:00`, until: t.day === 'Fri' ? '01:00' : '00:00' };
}

let G = null; // { terminal, i, demoNight, onDone }

export function startGuide({ terminal, onDone }) {
  G = { terminal, i: 0, demoNight: false, onDone };
  const el = $('#guide');
  el.classList.add('open');
  render(true);
}
export function closeGuide() { $('#guide').classList.remove('open'); }

function render(first) {
  const s = STEPS[G.i];
  $('#gTerm').textContent = G.terminal === '?' ? 'Terminal: not sure' : `Terminal ${G.terminal} · you told me`;
  $('#gDots').innerHTML = STEPS.map((x, k) => `<span class="${k < G.i ? 'done' : k === G.i ? 'on' : ''}" title="${esc(x.title)}"></span>`).join('');
  const card = $('#gCard');
  card.classList.remove('in'); void card.offsetWidth;
  card.innerHTML = `
    <div class="g-photo" style="background-image:url('${s.img}')"><span class="g-cap">Illustrative photo · not DXB · follow the airport’s signs</span>
      <div class="g-title"><span class="g-step">Step ${G.i + 1} of ${STEPS.length}</span><h2>${esc(s.title)}</h2></div></div>
    <div class="g-body">
      ${s.ride ? rideHTML() : `<p>${esc(s.body)}</p>`}
      <p class="g-look">${svg('eye', 'ic xs')} Look for: <b>${esc(s.look)}</b></p>
      ${s.belt ? `<form class="g-belt" id="gBelt"><label for="beltIn">Belt number from the screen</label><div><input id="beltIn" inputmode="numeric" maxlength="3" placeholder="e.g. 7" value="${esc(told.belt || '')}" /><button class="btn sm">Remember</button></div>
        ${told.belt ? `<span class="told">${svg('check', 'ic xs')} You told me: belt ${esc(told.belt)}</span>` : ''}</form>` : ''}
    </div>`;
  card.classList.add('in');
  $('#gNext').innerHTML = G.i === STEPS.length - 1 ? `Done ${svg('check', 'ic sm')}` : `I’m here · next ${svg('arrow', 'ic sm')}`;
  $('#gBelt')?.addEventListener('submit', e => {
    e.preventDefault();
    const v = $('#beltIn').value.trim(); if (!/^\d{1,3}$/.test(v)) { toast('Type the belt number shown on the screen.'); return; }
    told.belt = v; toast(`Saved: belt ${v}. You told me, I didn’t guess.`); render();
  });
  wireRide();
}

function rideHTML() {
  const t = G.demoNight ? { day: 'Wed', h: 0, m: 40 } : dubaiNow();
  const hhmm = `${String(t.h).padStart(2, '0')}:${String(t.m).padStart(2, '0')}`;
  const ms = metroState(t);
  const noMetroHere = G.terminal === '2';
  const metroOk = ms.running && !noMetroHere;
  const reason = noMetroHere ? 'Terminal 2 has no Metro station, so a taxi is the simple option.'
    : !ms.running ? `It’s ${hhmm} in Dubai and the Metro has stopped (it opens at ${ms.opens}), so a taxi.`
      : `It’s ${hhmm} in Dubai and the Metro is running until ${ms.until}. With luggage, a taxi is easier; the Metro is cheaper.`;
  return `
    <p class="g-reason">${svg('clock', 'ic xs')} ${esc(reason)}</p>
    <div class="g-opts">
      <button class="g-opt ${!metroOk ? 'best' : ''}" data-ride="taxi">${svg('taxi', 'ic')}<span><b>Official taxi rank</b><em>To Dubai Marina · 35–45 min · AED 110–150 (estimate)</em><em>Use the rank outside arrivals. Don’t take rides offered inside the hall.</em></span></button>
      <button class="g-opt ${metroOk ? '' : 'off'}" data-ride="metro" ${metroOk ? '' : 'aria-disabled="true"'}>${svg('train', 'ic')}<span><b>Metro, Red Line ${metroOk ? '' : '· not now'}</b><em>55–70 min · AED 7–9 + Nol card (estimate)</em><em>${noMetroHere ? 'Not at Terminal 2.' : ms.running ? `Runs until ${ms.until}. Luggage size rules apply.` : `Stopped. Opens at ${ms.opens}.`}</em></span></button>
      <button class="g-opt" data-ride="app">${svg('app', 'ic')}<span><b>Ride-hailing app</b><em>Opens your app. Dubai-io doesn’t book it.</em></span></button>
    </div>
    <button class="g-demo" id="gDemo">${G.demoNight ? 'Use the real Dubai time' : 'Try it at 00:40 (demo time)'}</button>
    <p class="g-fine">Metro hours as published by RTA; fares and times are estimates. Check RTA before you travel.</p>`;
}

function wireRide() {
  $('#gDemo')?.addEventListener('click', () => { G.demoNight = !G.demoNight; render(); });
  document.querySelectorAll('[data-ride]').forEach(b => b.addEventListener('click', () => {
    const r = b.dataset.ride;
    if (b.getAttribute('aria-disabled') === 'true') { toast('The Metro isn’t an option right now.'); return; }
    if (r === 'app') { toast('Hands off to your ride app. Nothing is booked for you.'); return; }
    if (r === 'metro') { toast('Follow the Metro signs from arrivals. Buy or top up a Nol card at the machines.'); finish('Metro'); return; }
    taxiMemory();
  }));
}

function taxiMemory() {
  openSheet(`
    <h3 id="sheetTitle">Save your taxi details?</h3>
    <p class="lead">If you leave something in the car, these are the details the lost-and-found report asks for. Only what you type is saved.</p>
    <form id="taxiForm" class="tf">
      <label for="plate">Plate number (on the car or the receipt)</label><input id="plate" placeholder="e.g. 12345" value="${esc(told.plate || '')}" />
      <label for="roof">Roof colour</label><input id="roof" placeholder="e.g. red" value="${esc(told.roof || '')}" />
      <div class="actions"><button type="button" class="btn" id="tfSkip">Not now</button><button class="btn primary">Save</button></div>
    </form>
    <p class="fine">Shown back to you as “You told me”. Never shared without your approval.</p>`);
  $('#tfSkip').addEventListener('click', () => { closeSheet(); finish('Taxi'); });
  $('#taxiForm').addEventListener('submit', e => {
    e.preventDefault();
    const plate = $('#plate').value.trim(), roof = $('#roof').value.trim();
    if (plate) told.plate = plate;
    if (roof) told.roof = roof;
    told.trip = { from: `DXB ${G.terminal === '?' ? '' : 'T' + G.terminal}`.trim(), to: 'Dubai Marina', at: new Date() };
    closeSheet(); finish('Taxi');
  });
}

function finish(mode) {
  const done = G.onDone; const term = G.terminal;
  closeGuide();
  done?.({ mode, terminal: term });
}

export function wireGuide() {
  $('#gNext').addEventListener('click', () => {
    if (G.i < STEPS.length - 1) { G.i++; render(); $('#gCard').scrollTop = 0; }
    else finish('Done');
  });
  $('#gClose').addEventListener('click', () => finish(null));
  $('#gLost').addEventListener('click', () => {
    openSheet(`
      <h3 id="sheetTitle">What can you see right now?</h3>
      <p class="lead">Pick what’s around you and I’ll resume from there. I don’t track where you are.</p>
      <div class="actions col">${STEPS.map((s, k) => `<button class="btn" data-k="${k}">${esc(s.look)}</button>`).join('')}</div>
      <p class="fine">Still unsure? Airport staff and information desks are the fastest help.</p>`);
    document.querySelectorAll('#sheetBody [data-k]').forEach(b => b.addEventListener('click', () => {
      G.i = +b.dataset.k; closeSheet(); render(); toast(`Got it. Resuming at ${STEPS[G.i].title}.`);
    }));
  });
}
