---
id: K-0150
kind: lesson
title: A sealed store's history line says what happened, never its details
status: confirmed
by: claude
created: 2026-11-08T21:17:59+00:00
concerns: core/creations.py, core/art_studio.py, core/world_map.py, core/life_events.py
from: dec:DEC-0126, dec:DEC-0108
---
DEC-0108 interconnection audit, 2026-11-08: creations, art and the world map gained life events. The person's life_events.jsonl is not sealed yet (it's appended, and CLAUDE.md says never rewrite it), but those three stores are (DEC-0126), so a line copying a creation's title, a painting's words, a check-in's place or the cleared tiles would put sealed content into a plain file. The first commit did exactly that for creation titles; the next one took them out. Rule: when a store is in at_rest.SEALED, its history line names the kind of change and an id (payload), or a count, never the record's words; use life_events.on_change(..., named=False) or a fixed summary. A screen that wants the title looks it up through the sealed store by id.
