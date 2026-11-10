---
id: K-0162
kind: implementation
title: Real Estate: listing a property for sale and recording the sale
status: confirmed
by: claude
created: 2026-11-09T08:22:27+00:00
concerns: core/real_estate_manager.py, core/estate_actions.py, core/web_screens.py, web/real-estate.js
from: dec:DEC-0018, dec:DEC-0057
---
core/real_estate_manager.py: a property gains asking_price, listed_date, sale_date, sale_price, selling_costs; statuses Under Contract and Sold; is_sold(); equity() is 0 once sold, so net worth and every total drop it with no other change; sale_numbers(p, price, costs, on) gives the net, the mortgage paid off (the amortized balance that day when the loan terms are known), the cash in hand, the adjusted basis (price paid less depreciation taken), the gain, the depreciation in it, months held and long-term. list_for_sale and record_sale (a property_sold life event; the mortgage balance goes to 0). Actions property.list_sale and property.sell say what the sale comes to, always 'an estimate, not a tax figure'. estate_page lists sold properties apart and leaves them out of the totals; the Real Estate page has List For Sale / Record The Sale and a Sold section. LIMITS['real_estate'] is now a boundary, not a 'yet'.
