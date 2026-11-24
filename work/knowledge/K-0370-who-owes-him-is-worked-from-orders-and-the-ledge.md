---
id: K-0370
kind: implementation
title: Who owes him is worked from orders and the ledger payments
status: confirmed
by: claude
created: 2026-11-24T06:12:43+00:00
concerns: core/receivables.py, core/assistant_domain_actions.py
from: commit:7f8af478
---
core/receivables.py: each order not cancelled, its price less the ledger revenue entries in its payment_ids (business_actions._paid, the same sum order.pay and the invoice use), oldest due first, overdue days, and a delivered order with money still on it named as the one to chase, with draft_invoice as the next step. An order with no price is said apart, never counted as owing nothing. Read-only.
