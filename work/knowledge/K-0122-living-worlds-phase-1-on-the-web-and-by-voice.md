---
id: K-0122
kind: implementation
title: Living Worlds Phase 1 on the web and by voice
status: confirmed
by: claude
created: 2026-11-08T15:47:49+00:00
concerns: core/web_worlds.py, core/assistant_world_actions.py, web/worlds.js, core/personal_data.py
from: dec:DEC-0134, dec:DEC-0137
---
The living_worlds store existed but wasn't a personal store, so no person had one. Added it to PERSONAL_STORES and its fictional event types to life_events.TYPES. core/web_worlds.py serves the screen (the one central character with a version per world, the worlds with campaigns, one campaign opened: the last played unless one is asked for) and the world.* actions. One central character only: the store allows many, but the spec's player is one self across worlds, so world.character_add refuses a second. Play (dungeon_master.take_turn) is deliberately not exposed: DEC-0134 approves Phase 1 only; the screen says Phase 2 waits on the go-ahead.
