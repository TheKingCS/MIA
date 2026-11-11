---
id: K-0221
kind: implementation
title: Businesses: a quick view of each, a dashboard per business, orders and quotes per business
status: confirmed
by: claude
created: 2026-11-11T08:27:49+00:00
concerns: core/web_businesses.py, core/business_book.py, core/business_actions.py, core/web_business.py, web/businesses.js, web/biz.js, web/business.js
from: dec:DEC-0153, file:core/web_businesses.py
---
DEC-0153 (Zac, 2026-11-11). The businesses are Money's own BusinessEntity records; nothing new keeps them. core/web_businesses.py reads each one's tagged income and expenses (budget totals with entity_id), its debts, its Real Estate properties (Property.entity_id) and its orders and quotes: Quote and Order in core/business_book.py gained entity_id ('' = not sorted yet, shown as a link on Businesses), the forms gained a Business pick (picks.businesses from Money), and an accepted quote's order keeps its business. Orders & Quotes takes ?business=<id> (or none) and adds new ones in that business. Pages: web/businesses.html is the Businesses subdashboard's own page (Area.page, like the Dashboard), web/biz.html?id= one business. Voice: get_businesses and get_business in the ledger domain (core/assistant_business_view_actions.py). Customers stay everyone's: Zac asked for orders and quotes per business, not customers.
