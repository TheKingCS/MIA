---
id: K-0298
kind: lesson
title: Careful parts fail where they meet: review the joins, not only each module
status: confirmed
by: claude
created: 2026-11-18T11:00:05+00:00
concerns: core/undo_log.py, core/kind_grants.py, core/dev_lab.py, core/activity_watch.py, core/specialist_review.py
from: commit:e986559f, commit:eec85f3b, file:tests/test_authority_review.py
---
Fable's review of 2026-11-18 (three independent reviewers on two days of Opus builds). Each module was careful by itself; the defects were at the joins. The stop and the standing yeses lived in the config file, and undo restores whole files, so an undo could lift a stop. A standing yes was granted per kind, and one kind (setting.set) covers every setting. The lab recorded a merge only after its second suite, so a timeout left the merge in and unrecorded. Erase wrote through the same writer that keeps a safety copy and an undo history, so two copies survived it. A reviewer's doubt was read only as a literal JSON false. When adding a safeguard, list every other mechanism that touches the same file, record or reply (undo, the atomic writer's .prev, change history, sync, another process) and test the pair.
