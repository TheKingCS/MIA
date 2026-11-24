---
id: K-0406
kind: lesson
title: A question that starts with a tool's phrase must never force a change
status: confirmed
by: claude
created: 2026-11-24T12:07:58+00:00
concerns: core/assistant_actions.py, core/weather_watch.py, core/broiler_batch.py
from: commit:2f20a410, commit:5258c258
---
A twenty-second fresh review: named_action named a record-changing tool whenever the message started with its phrase, so Broilers, how much feed do 25 need? would be retried with only start_broilers and a batch made. A question (how, what, when, why, which, who, is, are, do, did, should, would, ending in ?) now never forces a change; can you add milk? still does. Also: the rain gauge read 6/10 of an inch, a quarter of an inch and 1 1/2 inches as whole inches (word phrases now longest first, fractions parsed), logged the same rain twice, dated rain from Saturday as today, and told him to skip watering then water deeply; the meat-bird steps read as cornish cross grow fast, said week 0, and withdrew feed without saying keep water in.
