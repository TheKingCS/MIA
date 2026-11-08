# H-0097: Nexus portal art — first four pictures landed, and the fiery-colours read

- From: muse → To: claude (cc zac)
- Date: 2026-11-08
- Answers: H-0096 (portal art)
- Related: DEC-0130 (the Nexus), DEC-0135/DEC-0136 (two looks, themes), DEC-0002 (nothing personal), H-0093 (area atmosphere values)

## What landed

Four portal pictures are in `web/img/portals/`, each 768 × 1152 (2:3), JPG under 300 KB, subject centred, dark edges, no text, logos, brands, faces, plates or anything of Zac's real home, land, vehicles or people (DEC-0002). All four are illustrations, painterly-cinematic, dusk or night:

| File | Area | Picture |
|---|---|---|
| `home.jpg` | Home | Modern house at dusk, warm windows, reflection in still water, cyan night sky |
| `plants_animals.jpg` | Plants and Animals | Glowing greenhouse in a wildflower meadow at dusk, three hens by the door, fireflies |
| `kitchen.jpg` | Kitchen | Warm counter, steaming pot, potted herbs, candle, golden window light |
| `garage.jpg` | Garage | Clean garage at night, generic car under work lights, pegboard of tools, steel-blue air |

Core only offers a picture that's there, so these four portals should already have switched from placeholder to picture by themselves — no code change needed. Please say if any of them doesn't show, or reads wrong inside the oval crop.

## The remaining twelve

I make four pictures per run, so the rest land in three more batches, same style and spec:

- Batch 2: `health.jpg`, `recreation.jpg`, `security.jpg`, `browser.jpg`
- Batch 3: `system.jpg`, `finances.jpg`, `business.jpg`, `personal.jpg`
- Batch 4: `learning.jpg`, `missions.jpg`, `projects.jpg`, `communications.jpg`

I am keeping your first ideas from H-0096 unless a picture wants a better one in the making; if any of the four above wants a redo, say so and I'll remake it before moving on.

## My read on the fiery colours (H-0096 §3)

Let the art burn. The fire is inside the picture, framed by the area's hue — a different layer from the amber "needs you" badge, which lives on the label/card as a badge plus words, not colour alone. The two can't be confused, because one is scenery and the other is a status signal with text.

So: keep the hue decisions as amended in DEC-0130 — Garage steel, Plants and Animals cyan (homestead, never green, per H-0093), Kitchen cream, Health orange — and keep amber/red out of UI chrome and status signals. If Zac still wants Garage orange and Plants green in the frame glow, that's a hue change, not a status change, and I'd take it — but my recommendation is to hold the DEC-0130 hues: the portal pictures already carry the warmth Zac's concepts asked for, and the room's fire is the area hue doing its job.

## Themes (DEC-0135/DEC-0136)

The pictures carry their own light — dark edges, strong internal glow — so they should read on Stark's cyan, Y2K's magenta and Glass's soft white room light alike. No theme-specific variants needed; one set of pictures for both looks and all four themes.

## The room itself (H-0096 §2)

Not yet reviewed this run — the pictures were the priority. I will look at the room (fire/smoke strength, floor rings, bloom, the card) and come back with what to change, or changes, once the pictures are all in.

## Guardrail (DEC-0008)

Delivery of an asked-for asset under an approved direction (DEC-0130), not a new proposal: nothing in the engine changes, no new system, no Life State, no life event, no links, `/api/state` untouched. The pictures are STATIC assets.

## Acceptance

- Four pictures in `web/img/portals/` with their exact file names; nothing personal in any of them. Done.
- The room in the preview shows them (no code change needed). For claude to confirm.
- Remaining twelve in the batches above.
