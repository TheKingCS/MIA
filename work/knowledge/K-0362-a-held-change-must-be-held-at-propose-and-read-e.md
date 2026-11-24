---
id: K-0362
kind: lesson
title: A held change must be held at propose, and read events must say so
status: confirmed
by: claude
created: 2026-11-24T04:52:57+00:00
concerns: core/workflows.py, core/habit_offers.py, core/actions.py, core/inbox_manager.py
from: dec:DEC-0293, dec:DEC-0294, commit:b7ff7aef
---
A seventh fresh review of the event-triggered workflows (DEC-0293) and habit offers (DEC-0294) found: (1) a held run proposed records.add as MIA, and propose ran it at once whenever he had pressed Approve From Now On for that kind; propose now takes hold=True. (2) No life event was ever recorded with an email source: an emailed receipt MIA filed on her own was recorded as manual, so nothing was ever held; auto_file now runs inside life_events.acting("email"). (3) one global seen-mark replayed old history for a newly published workflow and lost events sharing a second at a burst cut; each workflow keeps its own mark with the ids at its second, on the events own clock. (4) a habit was marked offered before the gate decided, and the gate drops AMBIENT messages for spacing, so most habits were burned unseen; a habit now counts as offered only once the gate log shows it went through, tried once a day. (5) standing-yes runs now record source mia, apart from approved proposals (assistant). Lesson: tests that stub run() and invent sources prove nothing about the real path; test the source end to end.
