---
id: K-0129
kind: lesson
title: The tool-domain test scans every core file for domain="..."
status: confirmed
by: claude
created: 2026-11-08T16:21:56+00:00
concerns: core/development_engine.py, tests/test_web_surfaces.py
from: commit:bded921c
---
tests/test_web_surfaces.py::test_every_assistant_tool_belongs_to_an_app regex-scans core/*.py and modules for domain="..." and wants each one owned by an app. A development Candidate(domain="business") tripped it though it isn't a tool at all. Two meanings under one word is confusing anyway: the field is now `sector`. Keep domain= for assistant tool domains only.
