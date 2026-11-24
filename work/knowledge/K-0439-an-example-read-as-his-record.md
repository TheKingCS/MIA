---
id: K-0439
kind: debugging
title: An example read as his record
status: confirmed
by: claude
created: 2026-11-24T17:16:00+00:00
concerns: core/question_plans.py
from: commit:d964fe23
---
Heard on qwen2.5:14b: the winter answer said you burn 4 cords a winter and you have 14 gallons of water logged; both came from the tools' own instructions (tell me yours ("I burn 4 cords a winter"), a target). A protocol rule against it backfired: the greenhouse answer stopped reporting its real 14 materials and went generic. Fixed at the source instead: question_plans.without_examples drops each quoted example holding a number (with its like or bracket) from a tool reply before it goes on a sheet; the tool's own reply keeps it.
