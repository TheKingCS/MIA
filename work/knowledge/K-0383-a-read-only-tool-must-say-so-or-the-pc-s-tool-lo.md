---
id: K-0383
kind: debugging
title: A read-only tool must say so, or the PC's tool loop drops it
status: confirmed
by: claude
created: 2026-11-24T08:12:04+00:00
concerns: core/main_thread.py, core/assistant_actions.py, core/assistant_business_voice_actions.py, core/child_accounts.py
from: commit:a294f201
---
A thirteenth fresh review of a294f201 found customer_details counted as a change because of its name, so on the PC a question that called it was retried with lookups only, without it. Twenty-four tools their app marks observe had the same flaw (who owes me, the emergency kit, the canning shelf, money ahead, recall, look up online...). changes_records now treats the observe tier as read-only. Also: a record's name matched inside other words (Sign in redesign, Ann in annual), now whole words only; quote, my orders, delivered the and phone number pulled business tools into everyday talk, now narrower; business was missing from CHILD_BLOCKED_DOMAINS; a quote or order is found by its exact title or customer name first, the and 's dropped; due_day reads December 5 and 12/5; ready for pickup is Ready.
