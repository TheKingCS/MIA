---
id: K-0277
kind: lesson
title: Opus's review of the stop, Forge's scaffold and plans across apps
status: confirmed
by: claude
created: 2026-11-17T07:33:03+00:00
concerns: core/step_plans.py, core/stop.py, core/app_scaffold.py, core/assistant_turn.py, core/communication_gate.py
from: commit:f7f440ea, dec:DEC-0174
---
Three Fable-written features reviewed independently (DEC-0174) and fixed. Plans: _allowed checked only reach, undo and the never tier, and effect_of defaults to records/undoable, so 83 always-ask kinds (shop.buy, quote.send, *.delete, taught_skill.keep, a grant) could be steps; now always_asks() and grant.* are refused, with BOOKKEEPING (bill.pay, debt.pay: mark paid, no money moves) as the one exception. The steps.do card now carries the step's fingerprint, because the proposal stored only ids and steps.change could alter params between card and press. Lesson: a proposal must pin what its card showed. The stop: a bare 'all' in the everything pattern took 'stop all alarms' as an endless stop-everything; unreadable times silently meant forever; instant_answer (the Qt panels) skipped the stop. Lesson: an unreadable duration is a question, never the longest reading. Forge: writes weren't transactional and a $-anchored regex let a trailing newline through; use fullmatch and back up before writing.
