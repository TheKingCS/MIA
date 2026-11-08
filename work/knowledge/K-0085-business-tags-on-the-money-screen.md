---
id: K-0085
kind: implementation
title: Business tags on the Money screen
status: confirmed
by: claude
created: 2026-11-08T01:16:08+00:00
concerns: core/money_actions.py, core/web_money.py, web/money.js
from: commit:e5ddfa4, dec:DEC-0125
---
The Expenses tab shows each charge's business (and "sorted by MIA" for auto tags) with a Business button, and above it "Which business?": the bank charges business_tagging.pending_review still holds (12 at a time), one button per business plus Personal, MIA's guess in amber with her reason. Every choice is the action expense.business, which calls apply_choice, so the screen teaches MIA the store exactly as tag_charge does by voice, and undo puts the charge back in the waiting list.
