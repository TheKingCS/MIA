---
id: K-0137
kind: implementation
title: Portal Pictures: your own painting in a Nexus portal
status: confirmed
by: claude
created: 2026-11-08T16:35:36+00:00
concerns: core/portal_pictures.py, core/art_studio.py, core/web_nexus.py, web/portals.js, web/nexus.js, core/assistant_art_actions.py
from: dec:DEC-0140, dec:DEC-0130
---
core/portal_pictures.py keeps {area id: art id} as a personal setting (nexus.portal_pictures), so each person's Nexus is their own and undo works through atomic_write. picture() is what the Nexus draws: the person's painting as /api/art/<id>/image, else Muse's web/img/portals file, else '' for the placeholder. A choice whose painting was deleted is ignored rather than cleaned up, so the portal quietly falls back. art_studio.start gained `area`: a portal painting asked for an area goes in that portal at settle() instead of becoming the backdrop. On the client, an /api/ picture needs the sign-in, so nexus.js and nexus3d go through MIA.image (opt.art) while Muse's page paths load directly; the flat Nexus used to put the url inline in a style, which can't carry the bearer token, so it now fills the picture in when MIA.image resolves.
