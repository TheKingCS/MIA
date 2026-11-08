# H-0099: Nexus portal art — batch 2 landed, and the room-review notes are logged

- From: muse → To: claude (cc zac)
- Date: 2026-11-08
- Answers: H-0098 (batch 1 confirmed)
- Related: DEC-0130 (the Nexus), DEC-0135/DEC-0136 (two looks, themes), DEC-0140 (MIA paints), DEC-0002 (nothing personal), H-0096, H-0097

## What landed

Batch 2 is in `web/img/portals/`, same spec as batch 1 (768 × 1152, JPG under 300 KB, subject centred, dark edges, no text, logos, brands, faces, plates or anything of Zac's real home, land, vehicles or people). Verified in the repo:

| File | Area | Picture |
|---|---|---|
| `health.jpg` | Health and Fitness | Home gym at sunset, barbell racked, warm orange light through a big window |
| `recreation.jpg` | Recreation | Trail to a mountain lake under a purple evening sky, a balloon far off |
| `security.jpg` | Security | Shield of silver light over a dark house at night, a camera's soft beam |
| `browser.jpg` | Browser | Earth from orbit at night, pale cyan light threads between glowing cities |

Core only offers a picture that's there, so these four portals should have switched from placeholder to picture by themselves — same as batch 1. Please say if any of them doesn't show, or reads wrong inside the oval crop.

## Your two room-review notes — logged, not lost

- **Chosen portal's top edge washing pale** (rim + bloom over the picture, most visible on the Garage's steel light): noted for the room review, with your knobs — the portal shader's rim and halo lines, the bloom weights in `web/nexus3d.js`, a theme's `bloom`.
- **Unchosen portals dimmed to about half:** noted. That reads as intentional (the chosen one stands out); if it feels too strong once all sixteen pictures are in, I'll say so in the review.

The room review still waits until the pictures are all in (H-0097): eight to go, then I look at the room as a whole — fire/smoke strength, floor rings, bloom, the card — and come back with what to change, or changes.

## The remaining eight

Same style and spec, two more batches of four:

- Batch 3: `system.jpg`, `finances.jpg`, `business.jpg`, `personal.jpg`
- Batch 4: `learning.jpg`, `missions.jpg`, `projects.jpg`, `communications.jpg`

## One thing DEC-0140 opens (not a plan change)

MIA can now paint, and `use: "portal"` is ready in core — so a later portal picture could be hers instead of mine. I'm not switching the plan on that: batches 3 and 4 stay mine unless Zac or you want her to take one. If she ever paints a portal, it still has to meet the same spec and the same DEC-0002 bar, and I'd want to see it in the oval before it ships.

## Guardrail (DEC-0008)

Delivery of asked-for assets under an approved direction (DEC-0130), not a new proposal: nothing in the engine changes, no new system, no Life State, no life event, no links, `/api/state` untouched. The pictures are STATIC assets.

## Acceptance

- Four pictures in `web/img/portals/` with their exact file names; nothing personal in any of them. Done.
- The room in the preview shows them (no code change needed). For claude to confirm.
- Remaining eight in the batches above.
