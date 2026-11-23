---
id: K-0359
kind: lesson
title: An emergency check must know the homestead talks about engines, fences and seedlings
status: confirmed
by: claude
created: 2026-11-23T20:38:59+00:00
concerns: core/first_aid_floor.py, core/debt_missions.py, core/homestead_year.py, core/plan_price.py, core/business_actions.py
from: commit:7a902252
---
Fourth fresh review (2026-11-23): first_aid_floor fired on homestead talk: an engine choked or seized, an electric fence shock, seedlings drowned, rice burnt, hydraulic lines bled, a mower unresponsive, tomatoes overdosed on fertilizer, post holes cut deep. Fixed with targeted figure patterns (never a blanket equipment word: I cut my hand on the chainsaw must still fire) and a cut needing a body part. The number check used split()[0] (OTHER region: your) and substring (000 in 1,000); now whole-number match, never assumed for an unlisted country. debt_missions ticked by name, so a rename ticked an unpaid step: steps now keep debt ids in config (MAP_KEY) and the mission completes when all are done, one at a time. homestead_year listed a daily task 30 times a month and a negative interval looped to OverflowError: now once a month with a count, positive intervals only. A Planner price without labor now says at least. Invoices: refused for cancelled orders, offered for delivered ones, and by voice (draft_invoice; the business domain added to the app manifest so every tool belongs to an app).
