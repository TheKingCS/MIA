---
id: K-0287
kind: implementation
title: Approving a waiting card by voice, from now on included
status: confirmed
by: claude
created: 2026-11-17T13:02:00+00:00
concerns: core/spoken_approval.py, core/quick_commands.py, core/actions.py
from: dec:DEC-0215
---
What: core/spoken_approval.py, heard first by core/quick_commands.handle: "what's waiting for me?", "approve it", "approve 2", "approve it from now on", "yes, and from now on", "always do that", "reject it". It approves through ActionManager.approve(from_now_on=...), so a kind that always asks is refused in the card's own words.
Why that way: a quick command matches his own words in code, so the model can never approve a card, and nothing she reads can grant her anything (DEC-0156). A bare "yes" or "do it" is not taken, because those answer her other questions (the undo tools' confirm, capability gaps). With several cards waiting and no number she lists them instead of guessing.
