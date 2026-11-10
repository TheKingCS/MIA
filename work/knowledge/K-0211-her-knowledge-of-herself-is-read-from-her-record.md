---
id: K-0211
kind: implementation
title: Her knowledge of herself is read from her records when she is asked, never kept twice
status: confirmed
by: claude
created: 2026-11-10T23:38:37+00:00
concerns: core/self_knowledge.py, core/self_docs.py, core/dev_history.py, core/capabilities.py, core/device_framework.py
from: file:docs/CONVERSATION_REVIEW.md, file:core/self_knowledge.py, dec:DEC-0142
---
core/self_knowledge.py has TOPICS: her history, limits, direction, architecture, learning, memory, the glasses, the Chronicle, devices, the greenhouse. Each Topic names the files, decisions, apps and live readers that answer it, and block_for(context, prompt) turns a question into lines that each say where they came from: [app registry, partial], [decision DEC-0049, approved], [my history, counted now], [what I run on, checked now], [my code, core/x.py]. A file's line is that file's own opening (_opening), a decision's line is read from docs/DECISIONS.md (self_docs.decision), an app's line is the registry row and its state (capabilities.capability_map and capability_status), her history is counted from dev_history.records. So when the code changes, what she says changes with it, and a test fails if a topic points at a file, decision, app or reader that no longer exists. Zac asked for exactly this: no manually duplicated description that goes stale. One sentence is hand-kept and pinned by a test: nothing of hers searches the network for devices (true by reading the code on 2026-11-10; building a network scan means changing that sentence). A gated topic's plain word ("greenhouse") only counts in a question or beside you/your/MIA, so "add a greenhouse task" still goes to the tool. wants_described tells "do you have a greenhouse app?" (described from the registry) from "what is the greenhouse temperature?" (looked up). A live reader can also say what can't run here: the storage check needs lsblk, so on Windows she says she only finds serial boards. A file's opening is what she repeats, so an opening that says "this Pi" on a PC is a wrong answer waiting: keep openings true of where the code runs now.
