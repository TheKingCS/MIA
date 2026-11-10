---
id: K-0170
kind: implementation
title: Boss battles and questlines by voice, from the page's own data
status: confirmed
by: claude
created: 2026-11-09T07:53:18+00:00
concerns: core/assistant_game_actions.py, core/application.py, core/core_runtime.py, tests/test_boss_battles.py, tests/test_questlines.py
from: dec:DEC-0028, dec:DEC-0125
---
DEC-0028/DEC-0125, 2026-11-09, from the self-audit (no Assistant tool read boss_book or quest_book). core/assistant_game_actions.py: get_bosses phrases core/boss_battles.bosses (so a child never hears a debt: bosses() leaves them out), make_boss finds the mission by name and runs boss.add, get_questlines phrases questlines.quests_section (season, current chapter, offers), start_questline runs quest.start for an offer by name. All in the missions domain, which belongs to the Missions app already, so no app change was needed.
