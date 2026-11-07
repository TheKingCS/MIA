---
id: K-0066
kind: implementation
title: Receipts that do things, and an everyday mailbox read without touching it
status: confirmed
by: claude
created: 2026-11-07T14:55:09+00:00
concerns: core/receipt_effects.py, core/inbox_mail.py, core/inbox_manager.py
from: dec:DEC-0120
---
Built DEC-0120. core/receipt_effects.py: kind_of() sorts a receipt (groceries, car service, building supplies) by store and lines; propose() offers effects as sentences with a tick (pantry_add/new, grocery_check, maintenance_done/new with the odometer, material_add/new at the unit price), matched with core/receipt_match.match; apply() runs the ticked ones on filing, skipping any whose record has gone. The inbox item keeps receipt_kind and effects; inbox.file takes effects=[indexes].
core/inbox_mail.fetch_receipts reads an everyday mailbox: select(readonly=True), UID SEARCH since the last UID (first time SINCE 30 days), headers fetched with BODY.PEEK and judged by looks_like_receipt, only matches fetched whole with BODY.PEEK[]; state is UIDVALIDITY and last UID only.
What went wrong: lof as an oil-change word would have matched loaf; propose first used the 400-char excerpt, which can cut off an odometer line, so it now gets the whole text; PLYWD was not expanded until building-store abbreviations were added; and bash heredocs again turned escaped newlines into real ones (fixed with Edit).
