# design/ — what's inside (guide for LLMs)

Visual references only. Nothing in this folder is shipped code, and no image here is evidence that a feature is built.

## Layout

| Path | What it is | Origin |
|---|---|---|
| `screens/` | Earliest AI-generated explorations for Dubai-io (`4 styles.png`, `Dubai Concierge Companion Interface.jpg`, `Dubai-io Services and Civic Dashboard.jpg`). Historical — the `01–06` series below superseded them for layout/copy. | AI image tool, early commits (ex root `screens/`) |
| `references/01-home.png … 06-backstage.png`, `x-*.png/jpg` | The working screen set: Home, chat takeover, guide states, provider rows, partner sheet, approvals, lost-item flow, Services/Me, backstage. Generated from the prompt series in `docs/references/redesign.md`. Note: prompts `01b` and `02b` have no PNG files. Visitor-first framing is superseded (22 Oct) — use for visual anatomy only where consistent with `PLAN.md`. | AI image tool (GPT Image 2) for this app |
| `references/claude duet/` | 12 timestamped JPG video frames of a Claude Duet presentation. Interaction references (approvals, artifacts, briefings) — not app assets, not freely licensed. Has its own `README.md` with a frame-by-frame review guide. Preserved with this review checkpoint. | Founder-supplied, 22 Oct |
| `references/carousel/` | Holographic/cards effect reference: 4 JPGs + `holographi ccards.mp4`. Technique ref for glow/metal card work, pointed to from `docs/references/visuals-libraries.md` (ShipSwift update). | Founder-supplied effect ref |
| `references/services/` | Founder's structured service refs. `shops/` = user buys an item (cloth, coffee, restaurants); `service/` = someone does something for the user (pets). Mirrors the groups in `docs/services/intake.md`. The `Pulled data services for agents - app.jpg` sits at the group root. | Founder-taken, filed with structure |
| `references/01 - Visitor onboarding/` | Single file (`01 - visitor wifi.jpg`). Purpose unconfirmed — ask the founder before using it for anything. | Unknown |

## Rules for LLMs working here

1. **Never move, rename or delete the founder's files** (`docs/services/intake.md` §1). If a ref was dropped loose, propose its folder and ask.
2. **References are not functionality.** Never claim a screen or flow is implemented because a PNG exists.
3. **Don't resurrect deleted refs.** The 19 Oct cleanup deliberately removed a real-brands rows variation, a `_rejected/` take, a laundry *quote* mockup (quotes are forbidden) and a civic-services montage (no DubaiNow clones, no official branding). Don't recreate them.
4. **Check scope before building from a ref.** If `PLAN.md` lists what a ref shows as LATER or NEVER, stop and ask — don't build a "small version" of it.
5. **Cite provenance.** When referencing an image, say whether it is AI-generated-for-this-app, founder-supplied, or unknown.

## Linked docs

- Prompts for the root PNGs: `docs/references/redesign.md`
- Effects/carousel mapping: `docs/references/visuals-libraries.md`
- Service-ref filing: `docs/services/intake.md`, `docs/services/cases.md`
- Frame review guide: `references/claude duet/README.md`
