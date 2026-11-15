---
id: K-0238
kind: implementation
title: World Intelligence W2 and W1b: relevance from his records, watches MIA makes
status: confirmed
by: claude
created: 2026-11-15T16:35:54+00:00
concerns: core/relevance.py, core/world_intel.py, core/web_world_intel.py, web/intel.js
from: dec:DEC-0170, dec:DEC-0171, dec:DEC-0173
---
What: core/relevance.py builds anchors from the person's open goals (3, the main one 4), live projects (3), active missions (2), the homestead plan's next step (4) and its goal (3), learning paths (2) and owned equipment (1, by maker and model). relevance() counts an anchor when a find holds all of a one- or two-word anchor's significant words, or two of a longer one's; points are weight x words matched; each fit is a reason naming the record ("fits your project “Greenhouse” (greenhouse, panel)") and its kind:id is kept on the find (refs). WorldBook.ingest takes the anchors; tick reads them fresh each time and rescore() re-ranks finds not yet offered, so a finished project stops pulling. The gate's message leads with the fit.

W1b: WorldBook.sync_own_watches(anchors) once a day makes one watch per anchor with a name (made_by mia, reason "For your project ...", refs), strongest first, up to 12, every 12 hours; removes hers whose record is gone; a watch of hers the person removes puts its record in declined and it's never made again. Her watches never search: feeds are fetched whole and matched on the PC, so none of their words leave it (DEC-0122, DEC-0053).

Also: run_watches fetches each feed once per run and shares it between all the watches reading it (twelve own watches over 40 feeds would otherwise be 480 fetches a round); a refusal is remembered and raised for each watch as it would be alone.

Why words, not a model: facts in code (CLAUDE.md); a 3B model can't judge relevance reliably, and every point has to be explainable.

Next: the source loop (store:world_intel), cross-domain objective ranking with these anchors (DEC-0173 G4), procurement P1 (requirements per project).
