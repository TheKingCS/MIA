---
id: K-0407
kind: debugging
title: A question word anywhere isn't a question
status: confirmed
by: claude
created: 2026-11-24T12:17:07+00:00
concerns: core/assistant_actions.py
from: commit:f1e8c5a1
---
A twenty-third fresh review of f1e8c5a1: the question check searched the whole request, so tag questions (add a recipe for venison chili, would you?) and dictated words (add a note that says what is the wifi password?) lost their named-tool nudge. _ASKS is anchored now: the question word at the start, after at most a short Topic, lead, so Broilers, how much feed do 25 need? still isn't forced.
