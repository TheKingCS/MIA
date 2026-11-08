# The Nexus and MIA's spatial interface: assessment and plan

*Claude, 2026-11-08, from Zac's handoff "MIA — Spatial Interface & Nexus Design Architecture" (pasted 00:41).
Follows its section 10: inspect, map, find what's reused, plan milestones, then build. Nothing is replaced yet.*

## 1. What exists today that the Nexus builds on

| The handoff's part | What's already in MIA | Reuse |
|---|---|---|
| Life-centered architecture | DEC-0129 (Zac, earlier tonight): the Dashboard and fifteen areas, each with a hub screen (`core/web_areas.py`, `hub.html?area=`), apps in more than one area | **The portal list.** The Nexus reads the same table; nothing new to keep in sync |
| NexusHub | The Dashboard (`index.html`) and the Apps page | The Nexus becomes the first thing you see, with the Dashboard's cards in reach (decision 4) |
| SpatialPortal | Hub links in the sidebar and Apps page | Replaced, on the Nexus, by portals; the sidebar stays as the fast path |
| EnvironmentContainer | `hub.html` (a grid of app tiles today) | Becomes each environment's own layout, one at a time (Garage first) |
| HolographicPanel, cards | `.glass` panels, `web/tokens.css` (graphite layers, one cyan) | Gets depth: layered translucency, edge light, a little parallax, from new tokens |
| SpatialMenu, Search | The frame's search dialog (Ctrl+K), the Talk panel | Opened and closed with the spatial motion rules |
| SpatialNotification | The toast (`MIAShell.say`), the celebration overlay | Materialize and dissolve instead of slide |
| CharacterHUD, XPProgression | `MIAShell.levelCard`, Character, Skills, Missions, the Witness Principle (DEC-0014) | The HUD's profile block; achievements link to Character |
| MIAOrb | The orb (`#mia-orb`, the reactor mark), Talk | Stays; becomes the Nexus's centre |
| AmbientBackground, LiquidTransition | A few CSS animations, all honouring reduced motion | New: one shared background and one transition, both off under reduced motion |
| Phone, PC, glasses | One web front end; the glasses page (600 × 600, black is see-through) | Each device gets the Nexus at its own depth (section 4) |

## 2. How the handoff's environments map to DEC-0129's areas

| Handoff | DEC-0129 area | Note |
|---|---|---|
| Home | Home | |
| Garage | Garage | Workshop, CNC, 3D printing, laser engraving, inventory: Workshop and Toolbox are already here or in Business/Projects |
| Plants & Animals | Plants and Animals | Greenhouse, Chickens, Pets; aquaponics lives in the Greenhouse's Grow Lab |
| Health & Fitness | Health and Fitness | Health (sleep, visits, medications, records), Workout, Kitchen's meal plans |
| Adventures | Recreation | Zac renamed it Recreation at 00:25 (with Music); decision 1 |
| Finances | Finances | |
| Business | Business | |
| Kitchen | (in Home and Health) | The handoff makes it its own portal; decision 1 |
| Personal | Personal | |
| Learning | Learning | |
| Projects | Projects | |
| Browser | Browser | Also in the HUD's top bar |
| Settings & Diagnostics | Settings and Diagnostics | Also in the HUD's top bar |
| (not in the handoff) | Security, Missions, Communications | Missions likely lives in the HUD (level, XP, missions); decision 1 |

## 3. Decisions needed before building the look

1. **The portal list.** The handoff (13, with Adventures and Kitchen) and DEC-0129 (15, with Recreation, Security,
   Missions, Communications) differ. Proposed: DEC-0129's areas are the portals; Missions moves into the HUD; Kitchen
   stays inside Home and Health.
2. **Environment colors vs DEC-0023.** DEC-0023 set one cyan accent and replaced DEC-0018's per-screen neon colors.
   The handoff brings per-environment hues back, and two collide with status colors that carry meaning (DEC-0014,
   the design standards: amber = needs you, red = errors and destructive). Proposed amendment: each area gets a hue
   for its portal's border, its light and its environment's ambient glow **only**; buttons, selection and focus stay
   cyan; status colors are never used as area hues (Garage copper-orange, not attention amber; Health rose-magenta,
   not error red).
3. **The 90s/2000s underground, graffiti, liquid layer.** DEC-0023's Stark language is precise and restrained. Proposed:
   the liquid motion lives in transitions and the Nexus's ambient layer (portals forming from particles, an
   environment flowing in), graffiti only as texture in the Nexus backdrop; panels and text stay Stark-clean for
   legibility.
4. **What opens first.** The Nexus as the home screen with the Dashboard's cards one step in, or the Dashboard first
   with the Nexus one tap away.
5. **Who designs.** DEC-0017 gives the look to Muse and the working screens to Claude. Proposed: Claude builds the
   spatial components and the Nexus working end to end in the current tokens; Muse refines the art direction.

## 4. Technical approach

- **2.5D first** (superseded 2026-11-08 for the Nexus itself: Zac wanted a room you stand in). The Nexus is drawn in
  WebGL 2 by `web/nexus3d.js`, written without a library so nothing is downloaded; the CSS ring stays as the fallback
  and the keyboard and screen-reader path. three.js stays the plan for generated places (H-0095).
- **Shared, not per screen.** `web/spatial.css` (depth, glow, motion tokens and the components' classes) and
  `web/spatial.js` (portal ring, ambient background, transitions, materialize and dissolve), used by the frame.
- **Each device at its own depth.** PC: the full ring with parallax. Phone: a vertical arc you scroll, lighter
  particles, tap instead of hover. Glasses: the portals as a flat ring of icons on black, no particles (the display
  shows light; black is see-through). Reduced motion: everything still, transitions become fades.
- **Budgets.** The Nexus under 50 KB of new script and style; 60 fps on the PC; particles capped and off on battery
  saver; every portal reachable by keyboard and screen reader in sidebar order.

## 5. Milestones

*Status 2026-11-08 01:30: M0 done (DEC-0130: 15 areas plus Kitchen, hues on portals and glow only, the Nexus first,
the liquid style in motion and backdrop). M1 and M2 built: `web/spatial.css`, `web/spatial.js` (vapor, ring, enter),
`web/nexus.html` with `core/web_nexus.py`, the Nexus opening first, "take me to the garage" by voice. M3 built
02:15: the Garage environment (`core/web_environments.py`; hub.html draws it): bays with depth, needs-you, parts
running low across assets, the bench, lit in copper. M4's glasses part built 04:40: a Nexus card first among the glasses' cards opens the areas as a
flat ring of names on black (`web/glasses.js` nexusRing; `core/glasses.glasses_areas`), each lit faintly in its hue with
an amber dot where something needs you; stepping in shows only that area's apps; ▼ goes back to the ring, then out. Then 05:30, after Zac's concept images ("like you're in a room", "game like and
animated, flowing, seamless", everything orbiting MIA): the Nexus became a real-time 3D room, `web/nexus3d.js` (WebGL 2,
no library, offline): the orb with orbits on a ringed platform, the portals on an oval ring behind her with fire and
smoke in their hues, a reflecting floor, motes, bloom; drag, swipe, arrows or click to turn, the chosen one's card, and
a flight through the portal on Enter. The flat Nexus stays for reduced motion and machines without WebGL 2 (`?flat`).
Portal pictures: Muse (H-0096). Next: the pictures, Zac's look on the real PC, then each area's own space in 3D
(entering the Garage lands in a workshop, not a page), then the other environments one at a time.*

| # | What | Done when |
|---|---|---|
| M0 | This assessment, Zac's answers to section 3 recorded as a decision | DEC written |
| M1 | Spatial tokens and components (`spatial.css`, `spatial.js`): panel depth, edge light, materialize and dissolve, ambient background, reduced motion | The frame uses them; every page still passes the error sweep |
| M2 | The Nexus (`nexus.html`): portals from `core/web_areas.py` with each area's status (what needs you), the HUD (Browser, Settings, MIA, Search; portrait, level, XP, missions), the orb at the centre, the transition into an environment | Works by mouse, touch, keyboard and voice ("take me to the garage") on PC and phone |
| M3 | One environment, Garage, in its own spatial layout (its hub becomes a workshop space, not a grid) | Zac reviews it |
| M4 | Validated on phone, PC and the glasses page | Screenshots of each, a reduced-motion pass, a performance pass |
| M5 | The rest of the environments, one at a time | Each reviewed |
