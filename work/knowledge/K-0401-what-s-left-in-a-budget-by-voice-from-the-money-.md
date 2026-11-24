---
id: K-0401
kind: implementation
title: What's left in a budget by voice, from the Money page's own figures
status: confirmed
by: claude
created: 2026-11-24T11:23:22+00:00
concerns: core/assistant_domain_actions.py, core/finance_summary.py
from: commit:9e393c61
---
budget_left (observe) reads finance_summary.build_finance_summary's budget_targets (spent this month against each monthly target, most spent first), so the voice answer and the Money page never disagree; core/budget_manager.py was left alone (another session's work in progress). On the phone these questions reached only the offline library or the build-cost tools.
