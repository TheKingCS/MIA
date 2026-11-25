---
id: K-0496
kind: lesson
title: Every word-pattern route needed three or four review rounds
status: confirmed
by: claude
created: 2026-11-25T17:49:10+00:00
concerns: core/assistant_turn.py, core/today.py, core/job_quote.py, core/morning_briefing.py
from: commit:8027f3cc, commit:88a5ccdf
---
On 2026-11-25 every new code route matched on words (spending, the morning briefing, quotes, daily reminders, lesson how-tos) took three or four fresh reviews before it held: each fix of an over-match made an under-match (a hardcoded name, then Netflix refused as a person; the alarm filter by app, then every task dropped). What held: deciding by MIA own records rather than word shapes (a person is someone in his people or customers; an alarm is told by its own detail, not a shared app id; a tool call names one of her tools), sending anything ambiguous to the model rather than guessing (two amounts, two times, last week), and the corpus test plus a test per review. Check a filter against every producer of the thing it filters before shipping it.
