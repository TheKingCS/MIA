---
id: K-0113
kind: implementation
title: The Nexus as a 3D room, in WebGL 2 without a library
status: confirmed
by: claude
created: 2026-11-08T11:03:22+00:00
concerns: web/nexus3d.js, web/nexus.js, web/spatial.css, core/web_nexus.py
from: dec:DEC-0130
---
Zac wanted the Nexus to feel like standing in a room, game-like and flowing (2026-11-08, two concept images). Package installs are off in the cloud session, so three.js couldn't be vendored; web/nexus3d.js draws the scene directly in WebGL 2 (about 600 lines): billboard quads facing the camera for portals, orb and beam; a floor quad with the platform's rings and each portal's pedestal (uniform arrays, max 16); a full-screen chamber pass; points for motes; a full-screen mist; then bloom (bright pass at half size, Gaussian blur at half and a quarter) and an ACES tone map into the canvas. Portals draw back to front, split by the orb's depth; the floor's reflection is the same draws with y mirrored and faded, under a 74%-opaque floor. Premultiplied blending (ONE, ONE_MINUS_SRC_ALPHA): the art inside a portal covers, light adds. Lessons: first pass blew every frame to white (fire and rim too hot, bloom threshold 0.55): raise the threshold to 0.8 and keep the fire under 1.5x; a deep round ring made the chosen (back-centre) portal the smallest, so the ring is an oval (x 1.1R, z 0.62R) and the chosen one grows 30%; the orb hid the chosen portal until it moved low and forward. The DOM keeps the facts: labels and the card are page text projected each frame, MIASpatial.ring still owns the links, keys and turning, and nexus.js routes picks and drags to it. Headless screenshots work with --use-gl=angle --use-angle=swiftshader --enable-unsafe-swiftshader.
