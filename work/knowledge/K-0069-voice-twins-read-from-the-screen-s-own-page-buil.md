---
id: K-0069
kind: implementation
title: Voice twins read from the screen's own page builder
status: confirmed
by: claude
created: 2026-11-07T17:06:58+00:00
concerns: core/assistant_progress_actions.py, core/assistant_records_actions.py, core/application.py, core/core_runtime.py
from: dec:DEC-0125, commit:5003931
---
Each voice tool added for parity (core/assistant_progress_actions.py, core/assistant_records_actions.py) phrases its answer from the same function that builds the web page (character_page, skills_page, shop_page, insurance_page, life_notes.screen, operating_journal.screen, recreation.screen, MyFiles.listing), so voice and screen can never disagree, and a change goes through the screen's own action kind (buy_reward proposes shop.buy) so the checks and undo are shared. Register a new tool in both core/application.py and core/core_runtime.py: find_photos had been registered only in the headless Core, so the PC could not find photos by voice.
