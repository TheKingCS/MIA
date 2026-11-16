---
id: K-0271
kind: implementation
title: Procurement P3, first part: opportunities scored with reasons
status: confirmed
by: claude
created: 2026-11-16T15:36:10+00:00
concerns: core/opportunity.py, core/web_world_intel.py, web/intel.js, core/assistant_requirement_actions.py, tests/test_opportunity.py
from: dec:DEC-0172, task:P3
---
What: core/opportunity.py. assess() turns a World Intelligence find into an opportunity when it meets an open need (its refs or its watch's refs name requirement:<id>, set by core/relevance.py). Nine dimensions, each {name, value, reason}: project relevance, price advantage (price_book.judge against the same product_key), compatibility (the need's spec words found in the listing; 'not X' contradicts), quality and distance 'not known', urgency from needed_by, total cost (price_book.total_cost for quantity minus have, unknown parts named), strategic value (the need's priority), confidence. recommend(): skip when owned, acquired or ordered, over the ceiling, or a spec contradicted; wait when high; buy when ready only with a verified low and every spec met; else investigate. opportunities() ranks by recommendation then the find's score.

Where: the World page's data gains 'opportunities' (web_world_intel._opportunities, never breaks the page) and an Opportunities tab in web/intel.js; voice what_is_worth_buying (observe, world_intel app).

What went wrong: price_book.money_in takes any number, so 'Ventilation fan 12V, $45' read as 12. price_in needs a currency sign. money_in is still used for what the person types, where a bare number is a price.

Not yet: quality, distance and strategic value from real records; Compare, Saved, History and Reports.
