---
id: K-0138
kind: implementation
title: Playing a Living Worlds turn: one action, the story kept by the book
status: confirmed
by: claude
created: 2026-11-08T16:43:56+00:00
concerns: core/web_worlds.py, web/worlds.js, core/assistant_world_actions.py, core/dungeon_master.py
from: dec:DEC-0134
---
world.turn (core/web_worlds.py) wraps dungeon_master.take_turn as an ordinary action, so a turn is approved by the person pressing Do It (quick, no confirm box), runs under the turn lock with the model call inside it like a Talk turn, and is undoable like any change. Its result is the narration, then what changed, then what the dice refused, one per line (turn_lines), so the screen and the voice tool say the same thing. The page's story is the campaign's own history when the book keeps one (_story reads book.turns_in, the engine's claimed turn history) plus the turns played since the tab opened (sessionStorage, a per-viewer convenience), de-duplicated by what was said and the first line. What went wrong: the story box's input made the campaign grid wider than a phone; a flex input's intrinsic width counts toward the grid's min-content, so it needs width: 0 as well as min-width: 0.
