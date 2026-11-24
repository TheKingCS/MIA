---
id: K-0384
kind: test-procedure
title: Everyday workouts and meals on the phone
status: confirmed
by: claude
created: 2026-11-24T08:19:57+00:00
concerns: core/assistant_life_actions.py, core/question_plans.py
from: commit:f982d0d4
---
A probe of kitchen and fitness phrasings with no chat model: I ran 3 miles, did 45 minutes on the bike and I benched 185 reached no tools (the workout words were only gym words); what's for dinner this week went to the week review. Workout keywords gained the cardio and lift words, the week review leaves meals to the kitchen. Weigh-ins were already caught in code (quick_commands WEIGHT). Open: plan tacos for tuesday names no meal, so it reaches nothing.
