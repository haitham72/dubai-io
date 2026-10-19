// Connection metadata only. No credentials or OAuth grants live in this module.
import { registerPage, openPage } from './page-host.js';
import { esc, svg, toast } from './ui.js';
const defaults = [{ id: 'google', label: 'Google', status: 'not_configured', can_connect: false, scopes: ['openid', 'email', 'profile'] }];
let connections = defaults, authWindow = null, authProvider = null, requestSeq = 0;

async function loadConnections() {
  try {
    const r = await fetch('/api/auth/connections', { credentials: 'same-origin', signal: AbortSignal.timeout(3000) });
    if (!r.ok) return defaults;
    const result = await r.json();
    if (!Array.isArray(result.providers)) return defaults;
    const providers = result.providers.filter(p =>
      /^[a-z][a-z0-9_-]{0,39}$/.test(p?.id || '') && typeof p.label === 'string' &&
      ['not_configured', 'disconnected', 'connected'].includes(p.status)
    ).map(p => ({ id: p.id, label: p.label.slice(0, 60), status: p.status,
      can_connect: p.status === 'disconnected' && p.can_connect === true,
      scopes: Array.isArray(p.scopes) ? p.scopes.filter(s => typeof s === 'string').slice(0, 20) : [],
      account_label: typeof p.account_label === 'string' ? p.account_label.slice(0, 100) : null }));
    return providers.length ? providers : defaults;
  } catch { return defaults; }
}
registerPage('account.connections', {
  title: 'Connected accounts', source: 'Dubai-io · your connections',
  render: () => `<div class="account-page"><h3>Connect once. Reuse with consent.</h3><p>Keep your connected accounts in one place, across the app.</p>${connections.map(p => '<article class="account-card"><span class="account-icon">' + svg('person') + '</span><div><h4>' + esc(p.label) + '</h4><span>' + esc(p.status === 'connected' ? p.account_label || 'Connected' : p.status === 'disconnected' ? 'Not connected' : 'Not configured in this lab') + '</span></div><button class="btn sm" ' + (p.status === 'connected' ? 'data-account-disconnect' : 'data-account-connect') + '="' + p.id + '" ' + (!p.can_connect && p.status !== 'connected' ? 'disabled' : '') + '>' + (p.status === 'connected' ? 'Disconnect' : 'Connect') + '</button></article>').join('')}<p class="fine">A connection is shown only after the server confirms it. First-time sign-in uses the provider’s secure browser flow and returns here. Cards never receive credentials.</p><button class="btn wide" id="accountRefresh">Refresh connections</button></div>`,
  mount: body => {
    body.querySelector('#accountRefresh').addEventListener('click', () => openConnections({ replace: true }));
    body.querySelectorAll('[data-account-disconnect]').forEach(button=>button.addEventListener('click',async()=>{button.disabled=true;try{const response=await fetch('/api/auth/'+encodeURIComponent(button.dataset.accountDisconnect)+'/disconnect',{method:'POST',credentials:'same-origin',signal:AbortSignal.timeout(16000)});if(!response.ok)throw new Error();openConnections({replace:true});}catch{toast('Disconnect did not complete. Try again.');button.disabled=false;}}));
    body.querySelectorAll('[data-account-connect]').forEach(button => button.addEventListener('click', () => connect(button.dataset.accountConnect)));
  },
});
export async function openConnections(options = {}) {
  const request = ++requestSeq;
  openPage('account.connections', {}, options);
  const providers = await loadConnections();
  if (request !== requestSeq || document.querySelector('#sheet').hidden || !document.querySelector('[data-page-id="account.connections"]')) return;
  connections = providers;
  openPage('account.connections', {}, { replace: true });
}
function connect(id) {
  const provider = connections.find(p => p.id === id);
  if (!provider?.can_connect || provider.status === 'connected') return;
  authProvider = id;
  authWindow = window.open('/api/auth/' + encodeURIComponent(id) + '/start', 'dubaiio-auth', 'popup=yes,width=500,height=650');
  if (!authWindow) toast('Allow the sign-in window, then try again.');
}
addEventListener('message', e => {
  // A callback is a refresh signal, never proof of a connection or a token carrier.
  if (!authWindow || e.source !== authWindow || e.origin !== location.origin || e.data?.kind !== 'auth.complete' || e.data?.provider !== authProvider) return;
  authWindow = null; authProvider = null;
  if (document.querySelector('[data-page-id="account.connections"]') && !document.querySelector('#sheet').hidden) openConnections({ replace: true });
});
