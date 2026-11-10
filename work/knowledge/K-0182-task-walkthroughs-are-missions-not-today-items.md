---
id: K-0182
kind: decision
title: Task walkthroughs are missions, not Today items
status: confirmed
by: claude
created: 2026-11-09T10:37:18+00:00
concerns: core/greenhouse_setup.py, core/trade_actions.py, core/today.py, core/web_equipment.py, web/equipment.js, tests/test_greenhouse_setup.py, tests/test_trade_session.py
from: file:core/greenhouse_setup.py, file:core/trade_actions.py, file:core/today.py
---
Zac, 2026-11-09: "Why is anything like this showing up in Today and Home? These are specific instructions that are part of the Greenhouse and Construction tasks. These should be ready to generate Missions that only show in the Missions tab and maybe under Greenhouse or Projects... so that stuff doesn't get cluttered." Today and Home are for what's due in the day. A setup sequence or a job's steps are a project's own, so they live in Missions, and on the project's page if anywhere. The greenhouse setup, once started, is the mission "Set up the greenhouse": one tally objective a step (short titles, greenhouse_setup.title_of). Ticking one on the Missions screen (objective.tick) counts as saying it's done, and a step MIA sees done herself is ticked for her (where() syncs it). The Greenhouse page's What's Next tab heads with the step you're on (page_card). A Trade Master job is its mission from trade.start, a phase an objective. The mission is made only after the session has begun, so a refused start leaves no orphan mission. Both Today sources and the greenhouse.setup_step action are gone. When you add a guided sequence, make it a mission and put its current step on its own app's page, never on Today.
