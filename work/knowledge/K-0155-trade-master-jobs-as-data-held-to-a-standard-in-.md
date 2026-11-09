---
id: K-0155
kind: implementation
title: Trade Master: jobs as data held to a standard in code; the session refuses to pass a hold
status: confirmed
by: claude
created: 2026-11-09T02:38:19+00:00
concerns: core/trades.py, core/trade_jobs.py, core/trade_session.py, core/trade_actions.py, core/carpentry.py, core/specialists.py, core/loops.py, tests/test_trades.py, tests/test_trade_session.py
from: dec:DEC-0149
---
DEC-0149, 2026-11-08. A job (core/trades.py) is written once from named sources; the 3B model never makes up a step. The standard (problems()) was worth its rules on the first run: it refused the cold room for 11 steps (it was missing its loading step) and flagged the electrical stop rule on two jobs from 'wiggle-wire' and 'loose wire' until the trigger was tightened to real electrical words. What went wrong first: (1) 'job.*' action kinds and context.jobs were already the workshop's customer jobs (core/job_manager.py): renamed to trade.* and context.trade_session, core/trade_session.py, core/trade_actions.py. (2) New specialists inserted after Construction changed Night School's study order and a test; they go at the end, and a wiring question now rightly goes to the Electrical specialist. (3) A plain dev:trades process had to be named in core/loop_coverage.py before a loop could cover it. (4) The model's context gets a job outline only when the words are about doing the work, not every mention of a workshop. The README of the specialists had Night School's own uncommitted line; only this change's lines were staged (git update-index --cacheinfo).
