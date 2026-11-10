---
id: K-0191
kind: implementation
title: The job in progress as a question plan, kept away from the benchmark's open 'this' questions
status: confirmed
by: claude
created: 2026-11-09T05:41:04+00:00
concerns: core/question_plans.py, tests/test_trade_session.py
from: dec:DEC-0149, dec:DEC-0052
---
DEC-0149/DEC-0052, 2026-11-09. core/question_plans 'the job' (_the_job): the live trade session's item (or the one the words name, trades.find) on a sheet: its outline, where you are (trade_session.say), its tools split by the household inventory (matched by name, said as an estimate), its stop rules, and the holds left. First version took the benchmark's F2/F8/F9/F11 as examples and a wide regex (troubleshoot, step by step), but those questions are deliberately in NOT_A_PLAN (open 'this' questions the normal turn answers, already given the live job by trade_session.context_block), and the regex would have taken 'troubleshoot my wifi' on the phone. Kept: examples and words that say 'job' or 'step'; an empty sheet when no job is live or named (so the plan steps aside); a MISSING line only for 'this job' with none in progress.
