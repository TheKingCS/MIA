---
id: K-0428
kind: implementation
title: Who his best customers are
status: confirmed
by: claude
created: 2026-11-24T15:39:02+00:00
concerns: core/best_customers.py, core/assistant_business_voice_actions.py
from: dec:DEC-0125
---
core/best_customers.py (best_customers): each customer's orders that are not Cancelled, what has been paid on them through business_actions._paid (the order page's own count: its payments, and sales on its builds), ranked by paid then orders, each one's share; a customer with two or more orders and none in 180 days is named as gone quiet. Customers without orders are not ranked.
