---
id: K-0480
kind: implementation
title: Scenario drills: the simulator for a course without a board
status: confirmed
by: claude
created: 2026-11-25T07:56:38+00:00
concerns: core/drills.py, web/course.js, core/assistant_turn.py, core/lab_page.py
from: commit:02be98f6
---
core/drills.py: a drill is a situation and a few decisions, each choice best, fine or wrong with why, written from the course's own sources (Survival and bushcraft's: ATP 3-50.21, BSA, CDC, EPA). On the course page (lab_page.page carries drills_of the program; web/course.js reveals core's verdicts once picked) and by voice, taken in code before the plans (assistant_turn._drill_reply). Its place rides in MIA's own last message, "(Drill <id>: question n of m, k best so far.", so a multi-turn exchange needs no store; esp32_sim's build along could have done the same. A drill never passes a check.

What went wrong: "I think C" fell through to the model, which invented a boiling rule (1 minute per 1,000 feet); now a letter with only filler words around it is an answer, and while a drill is live any other short reply is asked for the letter in code. On the page, the DOM's replaceChildren writes a null child as the text "null" (the frame's el() skips nulls): course.js uses fill(), which filters them.
