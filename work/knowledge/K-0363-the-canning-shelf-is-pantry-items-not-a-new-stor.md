---
id: K-0363
kind: implementation
title: The canning shelf is pantry items, not a new store
status: confirmed
by: claude
created: 2026-11-24T05:08:40+00:00
concerns: core/canning_shelf.py, core/assistant_domain_actions.py
from: commit:6854f20a
---
Home-canned batches (core/canning_shelf.py) are ordinary pantry items: the name holds food, jar size and month so batches stay apart, the notes carry the Home-canned mark and the day put up, the expiration date is a year on (NCHFP: use within a year for best quality). So the Kitchen screen edits them, Undo takes them back, and preparedness.rotate already lists those nearing their date, with no new store, screen or parity gap. The date is quality, not safety: every shelf answer says a jar whose seal failed or shows spoiling goes out without tasting.
