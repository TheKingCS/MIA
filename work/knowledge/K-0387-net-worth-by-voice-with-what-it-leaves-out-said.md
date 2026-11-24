---
id: K-0387
kind: implementation
title: Net worth by voice, with what it leaves out said
status: confirmed
by: claude
created: 2026-11-24T08:54:11+00:00
concerns: core/assistant_domain_actions.py, core/finance_summary.py
from: commit:a9d191df
---
No tool answered what's my net worth. get_net_worth (observe) says the Money page's figure (finance_summary._net_worth: linked accounts and property equity), each part named, and since that figure leaves his other debts out (cards, loans; a property's mortgage is in its equity), the figure with them taken off too; unlinked savings are said as not counted, and nothing to add up is said plainly, never a zero.
