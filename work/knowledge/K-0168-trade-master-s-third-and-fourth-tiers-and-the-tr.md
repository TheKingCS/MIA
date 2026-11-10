---
id: K-0168
kind: implementation
title: Trade Master's third and fourth tiers, and the trigger words that still trip the standard
status: confirmed
by: claude
created: 2026-11-09T07:26:27+00:00
concerns: core/trade_jobs.py, core/trades.py
from: dec:DEC-0149
---
DEC-0149, 2026-11-09. Third tier: ten breakdowns (a leaking water heater, a clogged toilet, a dishwasher or washer that won't drain, a warm fridge, a well with no water, ice dams, bathroom mold, a sticking door, a squeaky floor) and five small jobs (drywall patch, toilet, receptacle or switch, recaulking, weatherstripping); diagnoses point their causes at those jobs (cause:...|replace_toilet). Fourth tier: the plans shelf's builds as jobs, each naming its plan so its quantities come from build_calcs. Trigger words that caught real text this time: 'ridge' (raking light shows every ridge), 'outlet' (a toilet's outlet, gutter outlets), 'ladder frames' (shelving sides), 'circuits' (short-circuits), 'outlet it' (a drain pipe); each was reworded, not given a rule it doesn't need. The step-insert helper first anchored on the next '),' and split a step between its watch and hold; it now inserts before the next Step( or the phase's end.
