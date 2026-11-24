---
id: K-0403
kind: debugging
title: The Money page's budgets mixed in business targets and next month's spending
status: confirmed
by: claude
created: 2026-11-24T11:41:43+00:00
concerns: core/finance_summary.py, core/assistant_domain_actions.py, core/feed_mix.py
from: commit:10e4e17a, commit:bdb7e90e
---
A twenty-first fresh review: finance_summary's budget_targets took every entity's targets (a business's Groceries showed as a second line) and spending with no end date (an expense entered ahead for next month counted now); now the household's own (entity_id='') to today. budget_left matched categories by two-way substring (grocery missed Groceries; Other matched inside brother); now resolve_by_name with the words he'd use. feed_mix: percent spelled out, the target after want, a calcium figure taken as a feed, 50-lb, and a target equal to a feed removed every copy.
