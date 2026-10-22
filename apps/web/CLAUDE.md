# Web — `apps/web`

Plain HTML/CSS + ES modules PWA. No framework, no invented palettes: cyan theme in `stage.css`, `stage-v3.css`, `data.js`.

## Test

```sh
for t in apps/web/tests/*.test.mjs; do node "$t"; done
```

## Map

`app.js` shell/tabs · `chat.js` ask · `hub.js` chat hub · `feed.js` + `social-ui.js` community · `stories.js` · `tasks.js` · `services.js` + `service-workflow.js` · `orders.js`/`offers.js`/`result.js` · `reading.js` news · `guide.js`/`arrival.js` · `map.js`/`gmap.js`/`places.js` · `profile.js` + `profile-store.js` · `merchant.js` · `miniapps/` · `page-host.js` · `ui.js` helpers.

## Rules

- UI: no shadows; plain AI text, tinted user box, white rounded action boxes.
- Provider HTML runs only from the widget origin in `<iframe sandbox="allow-scripts">`, `connect-src 'none'`, via the allowlisted `postMessage` bridge (`ARCHITECTURE.md` §5).
- Fixture/demo content renders a visible Demo pill with `demo_fixture`/`ai_demo` provenance.
- `apps/web/media/` holds binary demo assets; don't read them as text.
