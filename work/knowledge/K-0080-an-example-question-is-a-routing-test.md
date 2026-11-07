---
id: K-0080
kind: lesson
title: An example question is a routing test
status: confirmed
by: claude
created: 2026-11-07T18:28:47+00:00
concerns: core/assistant_records_actions.py, core/glasses.py, core/web_surfaces.py, tests/test_parity.py
from: dec:DEC-0125
---
Holding every glasses ask and every app ask (the Say line) to reaching that app's own tools (tests/test_glasses.py, tests/test_parity.py) found old asks that reached none or the wrong app: "What's my next trip?" and lab, notes and inbox questions attached no tools (no domain keywords: those areas only had multi-word trigger phrases), "How's the battery?" got only the system tools, "What's overdue on my vehicles?" went to Compliance, "What do customers still owe me?" to Debts. Fixed by keywords (core/assistant_records_actions.register_area_keywords) and better asks. Watch single keywords against small talk: "property" broke test_small_talk_stays_tool_free ("a useful property of this material"), so real estate keeps rental/tenant only. A live check of the new questions on the PC model passed 15/15 (tests/live_model_check.py GOLDEN_CASES).
