---
id: K-0241
kind: implementation
title: Procurement P2: specs compared by numbers, prices remembered, total cost
status: confirmed
by: claude
created: 2026-11-15T17:01:35+00:00
concerns: core/product_specs.py, core/price_book.py, core/price_actions.py, core/assistant_price_actions.py, core/web_world_intel.py, web/intel.js
from: dec:DEC-0172
---
What: core/product_specs.py (categories pump, fan, lumber, pipe, panel, sensor, solar, each with the specs that decide it and how they compare: min, max, eq; read() pulls numbers with units from words; verdict() gives identical by a shared model token, equivalent when every stated spec is met, similar when one is unknown, not suitable when one fails, each with reasons). core/price_book.py (PriceObservation and PriceBook, a sealed personal store under the epistemic contract; product_key: a model number, else sorted significant words plus specs read; judge(): never with fewer than three prices in 90 days, else low / usual / high, and a "was" price above anything seen called out; total_cost(): every part named, unknown parts listed and never counted as zero; cost_per_mile from his own settings). core/price_actions.py (price.record, price.trip_cost), core/assistant_price_actions.py (record_price, check_price, compare_need, set_trip_cost), and the Needs tab showing each need's best prices with fit and comparison, and a Record A Price button.

Two corrections made while testing: (1) a need's offers are found by its words, not by the exact product key, because a need's specs are minimums ("1000 cfm") that no offer's exact specs will equal; each offer's own price history stays under its key. (2) check_price never mixes different products into one verdict: for vague words it says it hasn't seen that exact one and lists things like it.

Lesson: Python strings in a Bash heredoc turned the regexes' \b into backspace characters (product_specs.py); found by a test, fixed, and the repository scanned for any other chr(8). Write patch scripts with the Write tool, never a heredoc, when they hold backslashes.

Next: P3, finds and listings linked to needs, the opportunity score and the Procurement view.
