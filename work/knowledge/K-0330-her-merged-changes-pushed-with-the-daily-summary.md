---
id: K-0330
kind: implementation
title: Her merged changes pushed with the daily summary
status: confirmed
by: claude
created: 2026-11-22T14:04:33+00:00
concerns: core/lab_push.py, core/background_jobs.py
from: task:WP-12, dec:DEC-0264
---
WP-12 (Q-100, DEC-0264). core/lab_push.push() after self_merges.offer in the self_changes daily check: on master only, the commits origin/master..HEAD (no network unless something waits) must all be hers (author MIA Lab, subject 'From the lab: ' for her merges, 'Revert "From the lab: ' for their Undo), else it holds for the owner; then fetch, and if GitHub has newer commits it holds (never a rebase or force); then git push origin HEAD:master. The outcome goes to config lab.pushed. Under pytest run() never uses the real git (the suite runs in his own copy). On the lab's protected list and in protected_list's lab group.
