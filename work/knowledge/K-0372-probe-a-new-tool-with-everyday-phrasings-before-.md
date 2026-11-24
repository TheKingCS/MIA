---
id: K-0372
kind: test-procedure
title: Probe a new tool with everyday phrasings before calling it done
status: confirmed
by: claude
created: 2026-11-24T06:30:31+00:00
concerns: core/assistant_domain_actions.py, core/assistant_today_actions.py, tests/test_everyday_phrasing_routing.py
from: commit:4ced6188
---
A routing probe (offered_tools on the desktop registry, no chat model) of twenty everyday phrasings for the tools built 2026-11-23/24 found six that reached nothing on the phone (no embedding model): has anyone not paid me, outstanding on my orders, still owe me, canned stuff to use first, plan for 3 people, how many days could my generator run. Trigger phrases are plain substrings, so each needs the words he would really say. They are kept as tests/test_everyday_phrasing_routing.py; add a new tool phrasings there.
