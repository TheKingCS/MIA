---
id: K-0192
kind: implementation
title: A property's sale: kept on the property, its gain an estimate, its totals gone
status: superseded
by: claude
created: 2026-11-09T07:02:53+00:00
concerns: core/real_estate_manager.py, core/estate_actions.py, core/web_screens.py, core/application.py, web/real-estate.js, tests/test_web_screens.py
from: dec:DEC-0057, dec:DEC-0125
---
DEC-0041/0057 partial app finished, 2026-11-09. RealEstateManager.record_sale stores the price, selling costs, date, and two values frozen as of the sale date: the loan payoff (remaining_balance_as_of with loan terms, else the balance) and the depreciation taken (accumulated_depreciation), so neither keeps counting after it. Then the value, loan and rent go to zero (it leaves equity totals without deleting history) and status becomes Sold. sale_summary is pure: net proceeds, adjusted basis (purchase price less depreciation; improvements aren't tracked, so it's an estimate), gain, and the recapture share (min of gain and depreciation). Three ways in, per DEC-0125: the property.sell action (approval card, refuses a second sale), the record_property_sale voice tool, and a Record Sale button on the Real Estate page (the card then shows what it came to and drops Record Rent).

Superseded 2026-11-09 at the merge: the design session built the same feature first (K-0162), and its version was kept.
