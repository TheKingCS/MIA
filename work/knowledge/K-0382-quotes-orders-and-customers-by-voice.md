---
id: K-0382
kind: implementation
title: Quotes, orders and customers by voice
status: confirmed
by: claude
created: 2026-11-24T07:59:31+00:00
concerns: core/assistant_business_voice_actions.py
from: commit:2b935d5f, dec:DEC-0125
---
A probe of business questions found no voice tools at all for quotes, customers, listing orders or marking one delivered (only a payment, an invoice draft and who owes me), against DEC-0125. core/assistant_business_voice_actions.py adds list_quotes, list_orders, customer_details (observe) and add_customer, make_quote, accept_quote, order_status (act_within_grant), each change through the Business page's own action kind via _run (propose, approve, undo), registered from register_business_view_actions so the PC and the phone both have them; customers' names and open quotes' and orders' titles reach them by name. A customer he doesn't have is said, never made up. order_paid also hears paid the deposit.
