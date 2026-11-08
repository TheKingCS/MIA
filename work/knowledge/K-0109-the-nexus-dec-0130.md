---
id: K-0109
kind: implementation
title: The Nexus (DEC-0130)
status: confirmed
by: claude
created: 2026-11-08T06:56:40+00:00
concerns: core/web_nexus.py, web/spatial.js, web/spatial.css, web/nexus.js, core/assistant_turn.py
from: dec:DEC-0130
---
nexus.html draws core/web_nexus.nexus(): a portal per area (web_areas.AREAS, each with a hue), today's overdue and today items counted into every area their app is in, and the HUD. web/spatial.js: vapor (a 160x100 canvas of drifting radial lights with additive blending, fading each frame, blurred by CSS; paused when hidden; still under reduced motion), ring (portals on the inside of a cylinder: translateZ(r) rotateY(a) translateZ(-r)), enter (portal forward plus a hue flash). Gotchas found: inside preserve-3d, overflow:hidden doesn't clip (the swirl moved into a flat clip-path layer), mix-blend-mode and CSS filters (drop-shadow, brightness) make rectangular boxes, and a 3D layer cuts box-shadow glow at its bounds (portals get 36px of room). wants_area() routes 'take me to the garage' before the model. The Dashboard hands off to the Nexus once per session; Today is index.html?today=1.
