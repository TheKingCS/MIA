---
id: K-0491
kind: implementation
title: A claim of a change no tool made is never said
status: confirmed
by: claude
created: 2026-11-25T13:53:14+00:00
concerns: core/claim_check.py, core/assistant_turn.py, core/calendar_move.py
from: commit:57992c89
---
core/claim_check.py checks the model reply that reaches the person in the turn branch where no change tool ran (the tool loop only looks things up): a first-person claim of a change (I have added, a reminder is set, you have been reminded, I will send a notification), not an offer or a question, is replaced by an honest line when he asked for something done, and dropped when offhand; each is kept in the Fix-It Log as claimed_done. Found by a live sweep: remind me to check the oil Saturday was offered only the alarms and the model said it was done. The same sweep: a model-filled date is replaced by the day his words name (assistant_turn.with_his_day), remind me to X on a day goes on the calendar in code, and list_calendar_events lists the days asked (calendar_move.listing).
