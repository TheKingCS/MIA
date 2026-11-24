---
id: K-0371
kind: debugging
title: An order due date is a delivery date, not a payment date
status: confirmed
by: claude
created: 2026-11-24T06:22:14+00:00
concerns: core/receivables.py, core/business_actions.py, core/web_business.py, core/assistant_more_twins_actions.py
from: commit:b05c46d0
---
An eleventh fresh review of core/receivables.py found it called an undelivered order past its due date money overdue and told him to chase it, while the Business page reads due as delivery (overdue = not delivered on time). Now only a delivered order with money left is chased (longest past due first), and an undelivered one past its date is said as not delivered yet. The page own owed total left out delivered-but-unpaid orders, the voice payment tool could not find a delivered order, and a Sold It sale on the order build never counted as paid; business_actions._paid now counts payments and sales on the order builds once each, and the page, the invoice, receivables and order_paid all use it.
