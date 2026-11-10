---
id: K-0183
kind: implementation
title: Projects and Missions connected without a second system
status: confirmed
by: claude
created: 2026-11-09T12:25:02+00:00
concerns: core/mission_projects.py, core/mission_guide.py, core/mission_manager.py, core/web_progress.py, core/web_projects.py, web/missions.js, web/projects.js, tests/test_mission_projects.py
from: dec:DEC-0152, file:core/mission_projects.py, file:core/mission_guide.py
---
2026-11-09, Zac's architecture handoff (DEC-0152). Following its own instruction (inspect first, make the smallest change), nothing was rebuilt. Mission.project_id already existed and was the gap's whole answer: the pages just didn't show it, and it couldn't be set after creation. Added: MissionManager.missions_for_project and set_project (recorded); core/mission_projects.py (missions_for, project_of, a derived progress with config weights, mission_card, the mission.project action, project_choices); core/mission_guide.py (guide_for over GUIDES: the Trade Master job's live step with Next/Checked/Back/Stop and its phase's step list, or Start; the greenhouse setup's step); missions_page cards carry project and guide; projects_page cards carry missions, progress and the status counts for filter tabs; the sheet and project cards link both ways (missions.html#mission=<id>, projects.html#<id>); voice set_mission_project and get_project_missions. The guide puts the job's Next Step and Checked buttons back, on the mission's own screen where Zac wanted them, rather than on Today. Gotchas: MissionManager is device-level, so its history lands in its own folder (life_events.folder_of(missions)), not the household log; test with that. The trade reply needs context.actions in a test world.
