---
id: K-0486
kind: debugging
title: A question that reached for a tool that only saves when asked was answered from memory
status: confirmed
by: claude
created: 2026-11-25T12:20:36+00:00
concerns: core/main_thread.py, core/tool_loop.py, core/assistant_plan_actions.py
from: commit:38766969
---
The tool loop takes a question that reaches for a record-changing tool as unasked-for and retries with lookups only. material_list (act_within_grant because keep=true saves a plan) was dropped that way, and the model then made up a materials list: against DEC-0118 (quantities only from core/build_calcs.py). core/main_thread.call_changes judges the call, not the tool: CHANGES_ONLY_WITH names the argument that makes it a change (keep, sent by the small model as the string false). A new tool that saves only on a flag belongs there.
