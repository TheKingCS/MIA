---
id: K-0364
kind: debugging
title: A purchase in a debt question was read as extra a month
status: confirmed
by: claude
created: 2026-11-24T05:16:51+00:00
concerns: core/question_plans.py
from: commit:95e4a2ae
---
The debts plan took any amount in the question as extra paid each month, so "if I buy a $900 welder can I still pay off the truck loan?" came back as "with $900 more a month, debt-free sooner": the opposite of the question. Its words also missed "pay down" and the afford plan missed "if I buy a", so such questions never composed. Fixed: buying() tells a purchase from money toward a debt; instead() works out what the same money would do on the first debt (a lump on its balance, or monthly), and says the minimums and payoff dates hold either way.
