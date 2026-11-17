---
id: K-0286
kind: implementation
title: Her own changes on Claude's pass, self-repair and the protected list
status: confirmed
by: claude
created: 2026-11-17T12:20:19+00:00
concerns: core/self_merges.py, core/self_repair.py, core/protected_list.py, core/dev_lab.py, core/night_school.py
from: dec:DEC-0225, dec:DEC-0222
---
What: Zac's yes to Q-76 to Q-78 (DEC-0222, DEC-0225). core/self_merges.py reviews one ready proposal Night School kept each night (step 7a1b); only Claude's readable pass merges, through dev_lab.approve (suite before and after, reverted by itself on a new failure); every verdict is kept in data/lab/self_merges.json and the day's merges reach Zac as one gate message (daily check self_changes) with how to undo. Undo is the new action lab.revert (dev_lab.revert: git revert -m 1 of the merge commit), on Diagnostics or by voice (undo_my_change, which names the change and needs his yes). core/self_repair.py runs every five minutes (job self_repair, never held by stop since it changes no record): starts Ollama through LLMManager._wake_local when it isn't answering, reloads the model on a thread, and makes a job that is backing off due now at most once an hour; each repair at most twice an hour, told through the gate. core/protected_list.py says dev_lab.PROTECTED in words; tests fail on a protected path no group names or a named safeguard missing (R-56).
Why that way: the merge reuses the lab's own approve so there is still one merge path (DEC-0225); a codex review never merges because Zac said Claude's pass. The night's review reads the lab it was given, so a stand-in lab in tests never reaches real proposals.
