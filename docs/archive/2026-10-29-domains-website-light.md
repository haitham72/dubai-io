# Domains on website (light mode) — Plan A

**Goal:** Website (`apps/site` `/`) groups work by product domains instead of Grok bot channels, polished in **light mode first** against `design/references/chat/grok-bot.jpeg`, `01-home.png`, and `chat/chat.jpg`.

**Constraints:** Do not touch `apps/web|api|ios|supabase`. No shadows. Accent `#357F92`. Default theme **light**.

## Tasks

1. Light default + domain override store (`localStorage`) applied in ThreadsProvider.
2. Composer shows live domain guess; user bubbles show domain label after send.
3. Home: three light starter chips that fill the composer (Household / Places / Services).
4. Thread view: Move to domain control; sidebar regroups immediately.
5. Tests for classify/override/group; e2e domain chip + move.

**Refs used:** grok-bot.jpeg (sidebar sections + composer), 01-home (starter chips), chat.jpg (filter chips → domain sections).
