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

- Tabs: **Companion · Services · Civic · Me**
- Companion is a chat timeline holding messages, cards and proactive messages
- Mini-apps and maps open as **bottom sheets** over the chat; closing one returns you to the conversation

## Trust labels (always visible where relevant)

`Demo data` · `Demo estimate` · `You told me` · `Proactive` / `Demo trigger` · `Merchant update` · `Pilot`
Approval cards show **Will be shared** and **Never shared** before anything leaves the phone.

## Screens

| File | Status |
|---|---|
| `screens/Dubai Concierge Companion Interface.jpg` | Layout reference (old gold style) |
| `screens/Dubai Laundry Quote App Mockup.jpg` | Mini-app sheet reference (old gold style) |
| `screens/Dubai-io Services and Civic Dashboard.jpg` | Services + civic reference (old gold style) |
| `screens/4 styles.png` | Superseded by iOS light + cyan |
| `screens/archive/…Montage…jpg` | Do not use: copies the official DubaiNow app |
| `demo/maps/*` | **Placeholders.** Replace with arrival-side maps (immigration, baggage, arrivals hall) |
