---
id: K-0173
kind: implementation
title: Voice-only flows given a way without voice through Today's list
status: confirmed
by: claude
created: 2026-11-09T09:04:18+00:00
concerns: core/today.py, core/greenhouse_setup.py, core/actions.py, core/loops.py, tests/test_greenhouse_setup.py, tests/test_trade_session.py
from: dec:DEC-0125, dec:DEC-0150, dec:DEC-0149
---
DEC-0125, 2026-11-09. The greenhouse setup sequence and Trade Master's walkthroughs worked only by voice and had no screen (screens are the design session's). Both now put their next move on core/today.py's list, which Home and the phone already show with each item's suggested action: the setup's next step (a new action kind, greenhouse.setup_step, Done for a step only the person sees, Skip otherwise, through greenhouse_setup.mark, the same as saying 'done' or 'skip that'), and the live job's step (trade.check while a hold point is open, else trade.next). A diagnosis needs two answers, so its question shows without a button. The new action family had to be covered by a loop (tests/test_loop_coverage): greenhouse.reporting now covers action:greenhouse.
