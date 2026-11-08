---
id: K-0084
kind: lesson
title: Being out of something is not deleting it
status: confirmed
by: claude
created: 2026-11-08T01:11:50+00:00
concerns: core/assistant_correction_actions.py
from: dec:DEC-0125
---
Live check of the voice corrections (2026-11-08): for "We're out of flour" the model chose update_pantry_item (quantity 0) over remove_pantry_item, and it was right: the item stays for restocking and the grocery suggestions can see it. remove_pantry_item now only answers "remove ... from the pantry". Same care with broad trigger words: "favorite" and "stars" pulled kitchen tools into "my favorite color is blue" and "I give that movie 4 stars" until narrowed to "a favorite" and "rate the". Measuring the 332 action kinds against voice (by the store methods each calls) found 158 with a voice twin before this batch.
