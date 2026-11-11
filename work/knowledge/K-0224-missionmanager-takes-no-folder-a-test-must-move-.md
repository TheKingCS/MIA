---
id: K-0224
kind: lesson
title: MissionManager takes no folder: a test must move _MISSIONS_FILE
status: confirmed
by: claude
created: 2026-11-11T08:31:43+00:00
concerns: core/mission_manager.py, tests/test_upkeep_missions.py
from: dec:DEC-0153, file:tests/test_upkeep_missions.py
---
2026-11-11: a new test built MissionManager(context, data_dir=...) inside try/except TypeError, fell back to MissionManager(context), and wrote ten test missions into the PC's real data/missions.json (removed the same minute by their upkeep: occurrence keys; nothing else under data/ changed). MissionManager reads the module constant _MISSIONS_FILE; tests must monkeypatch core.mission_manager._MISSIONS_FILE (as tests/engine_world.py does) and can assert context.missions.path is the temporary one. Never write a fallback that silently uses a store's default location in a test.
