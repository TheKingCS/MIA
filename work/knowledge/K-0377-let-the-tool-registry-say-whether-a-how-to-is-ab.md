---
id: K-0377
kind: lesson
title: Let the tool registry say whether a how-to is about MIA
status: confirmed
by: claude
created: 2026-11-24T07:19:54+00:00
concerns: core/assistant_chat.py
from: commit:04e548a6
---
A twelfth fresh review of 04e548a6 found its word lists cut both ways: usage questions without a listed app verb (how do I set an alarm, make a note, start a workout, send an email, see my debts) went down the action path with no help docs and a bare system line, where the model might do the thing instead of explaining; and world questions with a dual-use verb or a bare you (how do I remove a tick, purify water if you do not have a filter) were still held to her pages. Now about_mia asks her own tool registry: a how-to is about the world only when tools matched and all are library, knowledge, learning or plans tools; nothing matched, or no registry, stays hers. Teach-me requests use the same test, and a world how-to on the tools path is told to explain, not act.
