import { openServiceRequest } from './service-workflow.js';
// Host-owned previews for fictional website/marketplace rows. Order validation
// and sandboxed merchant mini-apps remain owned by the separate bridge task.
import { SERVICE_GROUPS } from './offers.js';
import { registerPageTrigger } from './page-host.js';
import { svg } from './ui.js';
export function initProviderPages() {
  registerPageTrigger('#offers [data-visit]', button => {
    const category = SERVICE_GROUPS.find(g => g.providers.some(p => p.id === button.dataset.visit));
    const provider = category?.providers.find(p => p.id === button.dataset.visit);
    if (!provider || provider.entry) return false;
    openServiceRequest(category.id,{provider});
    return true;
  });
  // Keep the renderer/bridge untouched while giving each provider one native
  // button, rather than a clickable wrapper with another button nested inside.
  const list = document.querySelector('#offersList');
  const makeCardsClickable = () => {
    list.querySelectorAll('article.offer-row').forEach(row => {
      const action = row.querySelector('[data-open], [data-visit]');
      if (!action) return;
      const id = action.dataset.open || action.dataset.visit;
      const provider = SERVICE_GROUPS.flatMap(g => g.providers).find(p => p.id === id);
      if (!provider) return;
      const card = document.createElement('button');
      card.type = 'button'; card.className = row.className + ' provider-card';
      card.setAttribute(provider.entry ? 'data-open' : 'data-visit', id);
      card.setAttribute('aria-label', 'Open ' + provider.name);
      const cue = document.createElement('span');
      cue.className = 'btn primary sm'; cue.setAttribute('aria-hidden', 'true');
      cue.innerHTML = 'Open ' + svg('chev', 'ic xs'); action.replaceWith(cue);
      // Button content is phrasing content; preserve all existing layout classes.
      row.querySelectorAll('div').forEach(div => {
        const span = document.createElement('span');
        for (const attribute of div.attributes) span.setAttribute(attribute.name, attribute.value);
        span.append(...div.childNodes); div.replaceWith(span);
      });
      const details = row.querySelector('.or-meta');
      if (details) { details.id = 'provider-details-' + id; card.setAttribute('aria-describedby', details.id); }
      card.append(...row.childNodes); row.replaceWith(card);
    });
  };
  new MutationObserver(makeCardsClickable).observe(list, { childList: true });
  makeCardsClickable();
  // The current offers renderer owns this footer; keep it aligned after sorts.
  const fine = document.querySelector('#offersFine');
  const text = 'Demo providers, prices and times. Tap anywhere on a card to open it. Opening a card sends nothing. Partner mini-app orders go to a sandbox merchant only after your one approval; website and marketplace rows are not connected.';
  const alignFooter = () => { if (fine.textContent !== text) fine.textContent = text; };
  new MutationObserver(alignFooter).observe(fine, { childList: true });
  alignFooter();
}
