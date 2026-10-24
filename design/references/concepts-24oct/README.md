# Concepts — 24 Oct (AI-generated for this app)

GPT Image 2.5 (variant sunburst, medium, 1k), prompts in `prompts.txt`. Style refs: the app's own Feed and Chats screens plus Mirsal-redesign `design/ios/chat.html` and `ai.html` (craft only). **Concepts, not functionality** — nothing here is built until a slice ships it.

Product model these illustrate (`docs/request-backlog.md`, 24 Oct): Dubai assistant + r/dubai-style community; private assistant (Grok-bot behaviour, slightly Telegram look); shared "@ hey grok" mention. `@io` is a placeholder handle (decided at SOC-01).

| Frame | Shows | Slice |
|---|---|---|
| 01-community-home | Subreddit-like community, votes, New/Top/Hot, Demo pills | Feed polish |
| 02-thread-mention | `@io` summoned in a thread; AI pill, Estimate pill, source chips with as-of | SOC-01 |
| 03-take-private | Public mention refuses to act, "Continue privately" sheet | SOC-02/03 |
| 04-private-assistant | Private thread with the FIN-01 decision card inline | assistant thread polish |
| 05-taxi-recovery | TAXI-02: quick replies, route confirm, RTA blocker, Staged reply | FIN-04 |
| 06-morning-brief | Brief as a chat message: "2 moving · 1 needs you" | FIN-07 |
| 07-check-back | Consented check-back with quick replies, quiet hours | FIN-05 |
| 08-me-memory | "You told me" + "I noticed" with Confirm/Edit/Not true/Forget | memory |

Known drifts — do not copy: call/video buttons in the assistant header (the assistant is not callable); robot/"O" avatars in 06/07 (use the app's smile orb); "Online"/"Always here to help" subtitles; 04 omits two "Never shared" fields (keep the full list); 03 depicts a group chat (SOC-03 shape). Rejected takes (not kept): an 02 with Reddit's "r/" naming, and a 07 claiming a pickup was "scheduled" (fake status, rule 1).
