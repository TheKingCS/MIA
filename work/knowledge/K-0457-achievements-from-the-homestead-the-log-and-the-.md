---
id: K-0457
kind: implementation
title: Achievements from the homestead, the log and the congratulation card
status: confirmed
by: claude
created: 2026-11-24T20:19:21+00:00
concerns: core/life_milestones.py, core/achievement_cards.py, core/rewards_manager.py, web/shell.js
from: file:docs/future/GAME_LAYER_PLAN.md
---
Zac (2026-11-24) asked for missions and achievements tied together, an achievements log and cards that pop up. Built on core/rewards_manager.py rather than beside it: new stats read from records in core/life_milestones.py (produce lb from the grow lab with oz and kg converted, eggs from the flock book, jars from canned life events because eaten jars leave the pantry; undone ones dropped by reversed_ids), three chains and the structures as one-time milestones matched on Complete project names (a repair/paint/move word means no build). Harvests, eggs and jars publish activity.logged so the unlock is immediate. core/achievement_cards.py: catalog, log dated from reward_unlocked life events, unseen (person setting achievements.seen_at; first time only the last day; 3 at once plus more), page and say. The card lives in web/shell.js so every page has it, checked on load and on every live change; closing is achievement.seen (a pressed action, no confirm). Gotchas: tests/test_achievements.py was taken (core.achievements is the level-up toasts), a test pins the exact text capture }; in shell.js so achievementCard is attached on its own line, and a new ref kind (pantry:) needs a RecordType.
