---
id: K-0225
kind: implementation
title: Smart Closet: suggestions worked out in code from weather, occasion, rest and ratings
status: confirmed
by: claude
created: 2026-11-15T08:39:48+00:00
concerns: core/smart_closet.py, core/web_closet.py, core/closet_actions.py, core/assistant_closet_actions.py, web/closet.js
from: dec:DEC-0162
---
Built core/smart_closet.py (pieces, outfits, ratings, ClosetBook store, sealed at rest), core/web_closet.py (the page and the day: weather card, today's calendar titles, a Loop work rhythm), core/closet_actions.py (closet_piece.add/edit/delete, closet.outfit, outfit_delete, rate, wore, laundry), core/assistant_closet_actions.py (seven tools), a glasses card and web/closet.js. Why in code: the model only phrases (DEC-0004). Warmth bands by the day's high (78/58/40 F), outerwear under 60 F or wet, a waterproof one when wet; an outfit rated 2 or under is never suggested. What went wrong: a test chose 62 F for a warm-flannel outfit and the generated combo won (warmth fit counts more than a 5-star rating: by design); deleting a piece left one-piece outfits, so outfits under two pieces now go with it. Wiring a new app also needs: capabilities LIMITS and AREAS, the overview stays under 1600 characters, docs/schema apps and shell examples, a glasses card or a parity decision, loop_coverage entries, at_rest SEALED plus tests/test_at_rest.py SEALED_STORES.
