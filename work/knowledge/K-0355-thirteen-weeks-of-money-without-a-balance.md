---
id: K-0355
kind: implementation
title: Thirteen weeks of money without a balance
status: confirmed
by: claude
created: 2026-11-23T18:10:46+00:00
concerns: core/money_ahead.py, core/web_money.py, web/money.js
from: commit:29396ed9
---
core/money_ahead.py: flows() walks each bill and income source from next_bill_due_date/next_income_due_date with date_recurs_on from its anchor (one-time items once); an overdue bill or late pay lands on today with its note; debt minimums monthly on the day of the last logged payment, else the 1st (said). weeks() buckets Monday-first; tight() sorts net<0 worst first. Deliberately no balance: bank linking is deferred (Zac, 2026-11-17), so it says weekly flow only.
