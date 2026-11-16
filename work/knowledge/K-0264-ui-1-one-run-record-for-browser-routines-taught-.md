---
id: K-0264
kind: implementation
title: UI-1: one run record for browser routines, taught skills and workflows
status: confirmed
by: claude
created: 2026-11-16T09:46:19+00:00
concerns: core/runs.py, core/browser_routines.py, core/browser.py, core/taught_skills.py, core/workflows.py, core/actions.py, core/assistant_browser_actions.py, core/agent_activity.py, web/welcome.js, docs/schema/run.schema.json, tests/test_runs.py
from: dec:DEC-0188, dec:DEC-0117, dec:DEC-0123
---
What: core/runs.py (RunBook, a personal store, runs.json, RunRecord with the EPISTEMIC contract) and docs/schema/run.schema.json. Engines write it: browser routines through browser_routines._Record (start, each step, a wait for a commit or sign-in, the end; the run's id travels in the held step's `where` as "run"); taught skills mirror into it in taught_skills._result, the one function every wait and end passes through, with Run.record_id, without changing how skills run; workflows write a start, one step with their lines, and done or failed. Readers: whats_running (taught_skills app, observe), Agent Activity's Running column (core/agent_activity._running, web/welcome.js), and later the stop (UI-2) and plans (UI-7).

Decisions: (1) A run record is a log, so RunBook saves inside undo_log.outside_undo, as SkillBook._save_run does: "undo that" takes back her step, never the fact that it ran. (2) recover() runs when the store loads: running becomes stopped ("may not have finished"), never done; waiting stays only for engines in WAITS_SURVIVE (taught skills keep their wait in their own store); a browser routine's wait lived in browser memory, so it becomes stopped with "run it again from step N". (3) A declined browser.commit used to sit until the 30-minute expiry: ActionType gained an optional `rejected` hook, called by ActionCenter.reject (errors there are logged, never undo the no); browser.commit's drops the held step and ends the run. _expire ends the run too.

Tests: tests/test_runs.py (including a child process killed with os._exit mid-step, then read back as stopped at that step), the browser routine paths (waiting, yes, no, expiry, restart), test_taught_skills and test_workflows additions, the schema. Gotchas: two runs finishing in the same second tie on `updated`, so tests should hold the run object rather than ask for recent(1); a fake clock for the expiry must move forward from time.time(), not from monotonic.
