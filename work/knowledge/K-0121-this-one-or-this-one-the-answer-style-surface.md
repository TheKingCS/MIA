---
id: K-0121
kind: implementation
title: This one or this one: the answer-style surface
status: confirmed
by: claude
created: 2026-11-08T15:43:50+00:00
concerns: core/answer_compare.py, core/assistant_answer_style_actions.py, web/answers.js, web/shell.js, server/app.py
from: dec:DEC-0138
---
DEC-0138's store (core/response_style.py) learned from picks but nothing offered them. core/answer_compare.py: plan (at most once a day, a reply of 140+ characters, offers on, not private) picks the least-settled dimension via next_experiment; restyle asks the model to rephrase MIA's own reply with one style change and same_facts drops any version with a number the reply didn't have (a changed figure is a changed fact); keep saves the pending offer in person settings and shuffles the two ways by the offer id so the reply isn't always A. The server does the model call outside the turn lock. Each turn carries comparable (false after the safety floor, a fixed reply, or in an off-record/journal/personal conversation: life_notes._private), and the compare endpoint re-checks privacy server side. StyleBook.choose drops a dimension's old picks so saying it outright wins at once (a tally would otherwise outvote it). Voice words map to styles in code (assistant_answer_style_actions.wanted).
