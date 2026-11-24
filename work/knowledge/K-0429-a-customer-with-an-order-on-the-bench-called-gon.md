---
id: K-0429
kind: debugging
title: A customer with an order on the bench called gone quiet
status: confirmed
by: claude
created: 2026-11-24T15:46:42+00:00
concerns: core/best_customers.py
from: commit:ba2822f1
---
Review of ba2822f1: only created_at was read, so a regular with an order still Open, Building or Ready was named gone quiet; now anything still open rules that out. A ledger entry two orders name (a shared job id) is credited once, to the oldest order. The share is said as of what has been paid on orders and the ranking as all time (market-day sales are not orders; there is no date range). best customer and top customer reach it; my regulars no longer does (a market's regulars are not customers on orders).
