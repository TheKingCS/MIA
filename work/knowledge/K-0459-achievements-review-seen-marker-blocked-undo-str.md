---
id: K-0459
kind: debugging
title: Achievements review: seen-marker blocked undo, structures matched any mention
status: confirmed
by: claude
created: 2026-11-24T20:33:41+00:00
concerns: core/achievement_cards.py, core/life_milestones.py, web/shell.js
from: commit:9c325fb6
---
Review of 9c325fb6. (1) Closing a card ran an action, which recorded an undoable change (config.json via atomic_write_text) and so blocked undoing the harvest that earned it; now POST /api/achievements/seen calls mark_seen inside undo_log.outside_undo, and cards are marked by id (not by a time string, which lost same-second unlocks and broke at the DST fall-back), each as it closes. (2) Structure milestones unlocked for any mention (Greenhouse automation, Painting the shed, Join the food coop); now structure_of needs the bare name or a build verb, catches -ing forms of mending words and parts, takes plurals, and gives one structure per project. (5) grams were not a unit. (6) unseen is cached on the history files state and the frame spaces its checks. Left: jars canned only go down by undo; homestead stats are household-wide (low under DEC-0119).
