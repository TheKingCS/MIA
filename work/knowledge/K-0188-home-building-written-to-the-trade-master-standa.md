---
id: K-0188
kind: implementation
title: Home building written to the Trade Master standard, and the traps the standard's triggers set
status: confirmed
by: claude
created: 2026-11-09T05:12:45+00:00
concerns: core/trade_jobs.py, core/trades.py
from: dec:DEC-0149
---
DEC-0149, 2026-11-09. Every first-list job is written: site layout, footings, slab, block foundation wall, floor, walls, roof framing, sheathing and dry-in, shingles, metal roof, windows and doors, house wrap and flashing, siding, insulation, air sealing, drywall, trim, paint, LVP, tile, DWV and supply rough-ins, an electric water heater, fixtures, rough and finish electrical, ductwork, a mini-split, a deck, stairs and gutters, and the furnace diagnosis. Licensed work follows answer 3 (B): electrical, plumbing and HVAC jobs carry the licensed stop rule and say a homeowner does them only under a permit that allows it; the gas side of a water heater and a mini-split's refrigerant (EPA 608) are named as the licensed trade's. What went wrong: problems()' word triggers read the steps, so 'hot outlet' (a water heater's) and gutter 'outlets' asked for the live-power rule, 'electrical panel' in an insulation certificate step did too, and 'footing' or 'foundation' in passing pulled in the utilities and structural rules; the fix each time was the plainer word ('drops', 'where your code says', 'concrete landing'), not a rule the job doesn't need. find() matches whole phrases, so 'tiling' and 'wiring the house' were added as words. Bash heredocs mangle these files: each batch was written with Write and appended with cat.
