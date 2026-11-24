---
id: K-0458
kind: implementation
title: Mission rewards beyond XP, and objectives counted from records
status: confirmed
by: claude
created: 2026-11-24T20:30:20+00:00
concerns: core/mission_trophies.py, core/mission_manager.py, core/mission_trophy_actions.py
from: file:docs/future/GAME_LAYER_PLAN.md
---
Game layer step 2 (docs/future/GAME_LAYER_PLAN.md). Mission.trophies [{kind,name,ref}] with six kinds (item, structure, song, knowledge, recipe, skill) in core/mission_trophies.py, earned once inside the rewards_credited guard as trophy_earned life events in each person own folder; a recipe ref unlocks the Kitchen recipe, a skill ref gets 25 XP. A fourth metric, records, reads a rewards stat and counts from a baseline taken when the objective is set, so earlier jars never count. MissionManager listens to activity.logged and says ready to claim once (ready_said); completion stays his press rather than MIA completing on her own (grants rule), unlike paths homework. objective.tick refuses records objectives so +1 cannot inflate them. Actions mission.trophy and objective.count plus tools add_mission_reward and count_toward_mission; the add_objective tool turns a records metric into a tally because it cannot name a stat.
