---
id: K-0381
kind: test-procedure
title: A build in progress is a project with missions
status: confirmed
by: claude
created: 2026-11-24T07:51:12+00:00
concerns: core/assistant_game_actions.py
from: commit:10b9de30
---
How is the shed build coming along got only the plans shelf (find_plans, material lists). A build in progress is a project whose missions carry the steps (DEC-0152; the Planner confirms a plan into missions), answered by get_project_missions, which only heard how far along is the and progress on the. It now also hears coming along, build coming/going, how far along and how is the build.
