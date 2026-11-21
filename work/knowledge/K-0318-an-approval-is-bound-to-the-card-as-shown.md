---
id: K-0318
kind: implementation
title: An approval is bound to the card as shown
status: confirmed
by: claude
created: 2026-11-21T04:25:01+00:00
concerns: core/actions.py, web/mia.js
from: commit:e3fde75b
---
WP-02. actions.binding_of(kind, params, summary) is taken after describe() and kept on the Proposal; approve refuses (Refused) a card whose hash changed since, or a ?binding= from another card; execute gets a deepcopy of params. web/mia.js remembers each card's binding from propose() and pending() and sends it with approve. A test that edits a card's kind on purpose must re-make its binding.
