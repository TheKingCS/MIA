---
id: K-0145
kind: implementation
title: The lab keeps each coder attempt's method: tools and targets, never content
status: confirmed
by: claude
created: 2026-11-08T20:26:37+00:00
concerns: core/dev_lab.py, core/dev_knowledge.py, tests/test_dev_lab.py
from: task:T-0025, dec:DEC-0073
---
T-0025 (DEC-0073 review step 2): run_claude now asks Claude Code for --output-format stream-json --verbose and trace_steps() reads each tool_use block as {tool, target}: the file (relative to the lab folder) or pattern, or a command's first six words, never old/new strings or written content. It returns a CoderSaid (a str carrying .steps), so every other coder, which returns a plain str, works unchanged and keeps no trace. write() saves the steps per attempt in data/lab/traces/<id>.json; trace_summary() collapses repeats (Read x2), and the retrospective's _record adds it under 'Method:' with lab:<id> as a citable source. Checked on Zac's PC the same afternoon: a real headless Claude Code run with these flags in a scratch folder ("Read note.txt and reply with only its first word") exited 0 in 9 stream lines; trace_steps gave its answer and the one step {Read, note.txt}, relative to the folder.
