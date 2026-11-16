---
id: K-0267
kind: implementation
title: UI-3, second part: every action kind's reach and reversibility
status: confirmed
by: claude
created: 2026-11-16T10:26:22+00:00
concerns: core/action_effects.py, core/actions.py, apps/lab/manifest.json, tests/test_action_effects.py
from: dec:DEC-0181, dec:DEC-0188, dec:DEC-0156
---
What: core/action_effects.py. REACHES (records, device, system, outside) and REVERSIBILITY (undoable, compensable, irreversible); DEFAULT records/undoable; EFFECTS names the 22 of 468 kinds that differ, each with why, found by reading their execute code and the helpers in their module. ActionCenter.propose appends "This can't be undone." to an irreversible kind's sentence unless it already says so (says_irreversible); ActionType.as_dict lists reach and reversibility for /api/actions. tests/test_action_effects.py: every declared kind exists; a sweep of each kind's code (with parity.desktop_registry() loaded so tool-module kinds like browser.commit are present) fails on marks of reaching beyond the stores (unlink, rmtree, rename, tak.send, home_call, subprocess, urlopen, dev_lab.approve, perform_pending, save_to_files, make_folder, picture saves and deletes, inbox filing, map downloads) that aren't declared, with INSIDE listing marked kinds that stay inside records (art.delete and wallet.delete keep files aside for undo; weather.place only reads online); system and outside kinds must be act_with_approval or never.

Found: lab.approve (merging code into MIA) was act_within_grant, so a learned skill could have merged on its own; raised to act_with_approval in apps/lab/manifest.json. 'Pay' kinds (bill.pay, debt.pay, order.pay) only mark things paid in records; quote.email and insurance.request only draft.

Limit: the sweep can't see an outward call inside another module's store method (MyFiles.delete was found by reading). Declare new outward kinds when writing them.
