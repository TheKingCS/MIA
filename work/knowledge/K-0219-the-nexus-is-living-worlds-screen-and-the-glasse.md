---
id: K-0219
kind: implementation
title: The Nexus is Living Worlds' screen, and the glasses have three screens
status: confirmed
by: claude
created: 2026-11-11T08:01:26+00:00
concerns: core/web_nexus.py, core/portal_pictures.py, core/glasses.py, web/glasses.js, web/nexus.js
from: dec:DEC-0153, file:core/web_nexus.py, file:core/glasses.py
---
DEC-0153: the Nexus stopped being navigation. core/web_nexus.worlds() makes a portal per Living Worlds campaign (in play first, each group latest played first, hued by its world) plus 'Make a World'; a portal opens worlds.html?campaign=<id>. The 3D room (web/nexus3d.js) and the flat ring draw it unchanged, because a portal is still {id, name, icon, hue, line, page, needs, art}. On the PC and phone it is reached only from Living Worlds in Recreation (that page's member is nexus.html) and by voice; MIA opens on the Dashboard in every look (the Nexus-first redirect in web/welcome.js is gone). Portal Pictures keys paintings by a story's id; old area-keyed choices are ignored, never deleted. The glasses: the orb, the menu (the eight, then subdashboards, then apps; web/glasses.js keeps a `trail` so Back goes up one level, and a spoken 'open X' steps into X's owner) and the Nexus (glasses_worlds; choosing a story says how to play it by voice, play_world_turn).
