# H-0096: The Nexus room — portal art, and a look at the room

- From: claude → To: muse (cc zac)
- Date: 2026-11-08
- Related: DEC-0130 (the Nexus), DEC-0017 (Muse owns the look), DEC-0002 (nothing personal), H-0093 (area
  atmosphere values), `docs/design/NEXUS_PLAN.md`

## Context

Zac, 2026-11-08 04:47, with two concept images (a round chamber of flaming portals arcing behind MIA's orb on a
glowing platform; a "HUBS" screen of oval portals on pedestals with an info card beside the chosen one): he wants the
Nexus to feel like standing in a room, "almost game like and animated, flowing, seamless", with everything orbiting
MIA. At 04:51: **Muse makes the portal pictures.**

What's built (claude, this session): the Nexus is now a real-time 3D room (`web/nexus3d.js`, WebGL 2, no library,
offline). MIA's orb with tilted orbits on a ringed platform; the areas' portals on an oval ring behind her, each framed
in its hue with fire and smoke rising off it; a glossy floor reflecting everything; drifting motes; bloom. Drag, swipe,
the arrows or a click turn the ring; the chosen portal grows, its card (name, line, what needs you, Enter) sits at the
left; Enter flies the camera through it into the area's hub. Labels and the card are page text (clean, per DEC-0130).
Phones stand closer in. Reduced motion and machines without WebGL 2 keep the flat Nexus; `nexus.html?flat` forces it.

Today each portal shows a placeholder: its hue, deep, with its icon. **The pictures are what make it look like the
concepts.**

## What's needed from muse

### 1. Sixteen portal pictures

- **Files:** `web/img/portals/<area id>.jpg`, one per area below. Core only offers a picture that's there
  (`core/web_nexus.portal_art`), so they can land one at a time; the portal switches from placeholder to picture by
  itself.
- **Size and shape:** portrait 2:3, 768 × 1152, JPG under 300 KB. The portal shows the picture inside an **oval that
  touches the middle of each edge**, so the four corners are cut off: keep the subject in the centre, nothing that
  matters in the corners.
- **Style:** painterly-cinematic like Zac's first concept image (the Homestead and Knowledge portals): one clear
  subject, rich light, dusk or night, dark edges so the frame's glow reads. The area's hue should be somewhere in the
  light (the fire around the frame is that hue).
- **Never:** text, logos, brands, plates, house numbers, recognisable faces, or anything of Zac's real home, land,
  vehicles or people (DEC-0002). Illustrations, not photos of real places.

| File | Area | Hue | A first idea (yours to change) |
|---|---|---|---|
| `home.jpg` | Home | #35d4ff | A modern house at dusk, warm windows, its reflection in still water |
| `garage.jpg` | Garage | #8fa7bf | A clean garage at night, a car under work lights, tools on the wall |
| `plants_animals.jpg` | Plants and Animals | #35d4ff | A glowing greenhouse in a meadow at dusk, a few hens by the door |
| `kitchen.jpg` | Kitchen | #e9d4a8 | A warm counter, herbs and a steaming pot, golden window light |
| `health.jpg` | Health and Fitness | #ff8a3d | A home gym at sunset, a barbell racked, light through a big window |
| `recreation.jpg` | Recreation | #9b6bff | A trail to a mountain lake under a purple sky, a balloon far off |
| `security.jpg` | Security | #c0c8d4 | A shield of light over a dark house, a camera's soft beam |
| `browser.jpg` | Browser | #bfefff | Earth from orbit with light threads between cities |
| `system.jpg` | Settings and Diagnostics | #dfe9f2 | A clean core of light, gears and circuitry, calm and precise |
| `finances.jpg` | Finances | #3f7bff | A wide valley at dusk, a path climbing to a lit summit |
| `business.jpg` | Business | #7f95ff | A small maker's shop at night, a packed box under a lamp |
| `personal.jpg` | Personal | #ff8ad8 | A journal and a warm mug by a window, evening rain outside |
| `learning.jpg` | Learning | #6a5cff | An open book with a glowing brain of light above it |
| `missions.jpg` | Missions | #c86bff | A lantern on a rock at the start of a trail into the mountains |
| `projects.jpg` | Projects | #b9a8ff | A workbench with a blueprint, a gear and a half-built frame |
| `communications.jpg` | Communications | #6fc6ff | Paper letters turning into light as they fly into the night |

### 2. A look at the room, when you can

Your call on everything that's look: fire and smoke strength, the floor's rings, the bloom, the card. The scene's knobs
are named in `web/nexus3d.js` (`R`, `FOCUS_GROW`, the portal shader's fire and rim lines, the bloom pass weights);
tell claude what to change, or change them.

### 3. One question for Zac that touches your values

Zac's concepts burn Garage orange and Plants and Animals green. H-0093 kept homestead cyan (no green) and DEC-0130
keeps area hues off amber and red, so "needs you" stays unmistakable. If Zac wants the fiery colours, the amber "needs
you" badge on the labels still separates them; your read on that is welcome.

## Added 06:30: themes (DEC-0135, DEC-0136)

Zac asked for two looks (Spatial and Cards, per person) and themes on top of both. Four first cuts are built as data in
`core/themes.py` (Stark, Y2K Cyber, Cyberpunk, Glass), with panel materials in `web/themes.css` and the room's light
following the theme. They're yours to refine like everything else that's look; the plan, the theme contract (what a
theme may and may not change) and the Theme Studio steps are in `docs/design/EXPERIENCES_AND_THEMES.md`. The portal
pictures stay the same in every theme, so they should read on cyan, magenta and soft white light alike.

## Acceptance

- Each picture in `web/img/portals/` with its exact file name; nothing personal in any of them.
- The room in the preview shows it (no code change needed).
