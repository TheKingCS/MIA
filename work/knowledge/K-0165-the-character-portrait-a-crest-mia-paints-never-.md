---
id: K-0165
kind: implementation
title: The Character portrait: a crest MIA paints, never a person
status: confirmed
by: claude
created: 2026-11-09T08:51:40+00:00
concerns: core/art_studio.py, core/web_progress.py, web/character.js, core/person_settings.py
from: dec:DEC-0140, dec:DEC-0113
---
The portrait card was an 'art placeholder' (Zac's call). The art studio's NEGATIVE prompt and problem() keep people and faces out, so the portrait is a crest instead: art_studio USES['crest'] (1024 square, heraldic, one centred design), core/web_progress.crest_words (the two strongest of the six attributes as symbols, the finish by level: bronze, silver at 10, gold at 20), character_page()['crest'] {image, words, can_paint}. Paint My Crest starts it only when pressed (apply=True); settle() puts its id in the person setting `character.crest`, and the card shows it from /api/art/<id>/image. Painting needs ComfyUI on the PC; without it the art studio says how to start it.
