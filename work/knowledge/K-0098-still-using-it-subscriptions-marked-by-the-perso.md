---
id: K-0098
kind: implementation
title: Still using it: subscriptions marked by the person
status: confirmed
by: claude
created: 2026-11-08T02:12:01+00:00
concerns: core/subscriptions.py, core/findings.py, core/budget_manager.py, web/money.js
from: commit:bef6bdd, dec:DEC-0054
---
core/findings.py had the unused-subscription finding parked because nothing recorded use. Now the person records it: Bill.still_using_on, stamped by bill.still_using (Money Still Using, or I still use Netflix). A bill counts as a subscription when it repeats and is marked, filed as Entertainment, or named or noted as a subscription, membership, streaming, premium or plus; that keyword guess is deliberately loose because the finding only asks, never judges, and is never unprompted. A never-marked one waits until it has been on the books 90 days, so a new bill is not asked about at once.
