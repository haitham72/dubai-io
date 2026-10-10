# Dubai-io — Design

**Reference implementation:** `demo/` (open `demo/index.html` via a local server).

## Style

iOS light mode with a cyan tint. It should feel like a native iPhone app, not a government portal.

| Token | Value |
|---|---|
| Background (grouped) | `#F2F2F7` |
| Card | `#FFFFFF`, radius 16px, soft shadow |
| Separator | `#E5E5EA` |
| Text / secondary / tertiary | `#000000` / `#3C3C43` / `#8E8E93` |
| Tint (cyan) | `#0A9CC2`, soft `#E3F6FB` |
| Bot bubble / user bubble | `#E9E9EB` / tint with white text |
| Font | System (SF Pro on iOS), large bold titles |

Merchant mini-apps keep **their own** branding. That contrast is what makes the mini-app idea visible.

## Layout

- Tabs: **Companion · Services · Me** (Civic is LATER; no tab in the contest build)
- Companion is a chat timeline holding messages, cards and proactive messages
- Mini-apps and maps open as **bottom sheets** over the chat; closing one returns you to the conversation

## Trust labels (always visible where relevant)

`Demo data` · `Estimate` · `You told me` (UI label for `user_supplied`) · `Sandbox` · `Official source` · `Proactive` / `Demo trigger` · `Merchant update` · `Scripted demo` · `Merchant role, simulated`
Approval cards show **Will be shared** and **Never shared** before anything leaves the phone.

## Visual status (10 Oct 2026)

**Functional, not final.** The demo has the right structure: the chat, the cyan host approval, mini-apps branded per merchant, trust pills and three tabs. It hasn't had a visual design pass yet. That pass is **deferred to later, and the founder will start it**. Until then:

- Don't restyle anything, add palettes or tweak spacing. Tokens above stay as they are.
- What the visual pass will cover: arrival-side airport maps (replacing `demo/maps/*`), the mini-app look for each of the three laundries and the generated template, card polish, and the Services and Me screens.
- Hard rules still apply during the pass: no DubaiNow look, trust labels stay visible, and merchant branding never appears on the host approval card.

## Screens

| File | Status |
|---|---|
| `screens/Dubai Concierge Companion Interface.jpg` | Layout reference (old gold style) |
| `screens/Dubai Laundry Quote App Mockup.jpg` | Mini-app sheet layout only (old gold style). Its quote flow is rejected: fixed prices only |
| `screens/Dubai-io Services and Civic Dashboard.jpg` | Services reference only (old gold style). Civic half is LATER |
| `screens/4 styles.png` | Superseded by iOS light + cyan |
| `screens/archive/…Montage…jpg` | Do not use: copies the official DubaiNow app |
| `demo/maps/*` | **Placeholders.** Replaced during the visual pass with arrival-side maps (immigration, baggage, arrivals hall) |
| `demo/` (10 Oct) | Locked arc, functional. Visual pass pending |
