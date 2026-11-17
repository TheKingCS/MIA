---
id: K-0294
kind: debugging
title: An independent review of the night's builds, and what it caught
status: confirmed
by: claude
created: 2026-11-17T13:59:43+00:00
concerns: core/dev_lab.py, core/self_merges.py, core/self_repair.py, core/spoken_approval.py, core/activity_watch.py, core/recall_index.py, core/atomic_write.py
from: commit:dbca9e8a, commit:420ef8ee, commit:268f8c31
---
What: a fresh reviewer read the night's commits (her own merges and Undo, self-repair, the protected list, voice approval, the ambient view, noting, recall, the message sorter) and found six real problems, all fixed the same night:
1. a merge or revert that conflicts left conflict markers in the running copy (dev_lab._git now takes undo=, running merge --abort or revert --abort before raising);
2. the self-change and self-repair summaries went out AMBIENT, which the gate drops on spacing, so they could vanish; now TIMELY (held for an opening);
3. "yes, from now on" and "always do that" named no card and could approve one while he answered something else; now only words with "approve" or "accept";
4. self-repair reported starts it never tried (start_ollama off, a turn's cooldown) and its 15-second wait ran on the window's thread; now checked first and on its own thread, and the recall refresh embeds on its own thread too (refresh_later, with a lock and snapshot for search);
5. activity.json and recall_index.json weren't sealed though the docstring said so; added to at_rest.SEALED;
6. noting wrote every 30 seconds through atomic_write_text, which bumps /api/live, so every open screen reloaded twice a minute; atomic_write_text(live=False) and a span only growing longer saved at most every 5 minutes.
Also: the merge re-checks the protected list as it is now, with renames counted by both names; the focus hold only holds nice-to-know messages.
Why it matters: the tests passed on every one of these; only reading the paths end to end found them. Keep asking for the review.
