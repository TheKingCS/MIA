---
id: K-0268
kind: lesson
title: Fable's review of the run record, the lasting history, the one browser and action effects (items 24 
status: confirmed
by: claude
created: 2026-11-16T13:09:16+00:00
concerns: core/browser.py, core/browser_routines.py, core/assistant_actions.py, core/assistant_undo_actions.py, core/runs.py, tests/test_runs.py, tests/test_change_history.py, tests/test_browser.py
from: dec:DEC-0174, dec:DEC-0196, dec:DEC-0188
---
Found and fixed: (1) DEC-0196's everyday mode puts the recorder script and its binding on every page of the browser context, so teaching would have recorded his clicks and typing in his own other tabs, private sites included. _Worker._recorded now takes Playwright's binding source and, in everyday mode, drops events whose page isn't her tab; the script sends location.hostname and start_teaching's handler turns anything on a private site into one 'signin' (you do this part) step. (2) change history: assistant_actions._summary_of kept a tool's argument values in the sealed history; values are now left out when the tool's or argument's name matches _SECRET_NAME. (3) undo_by_time took `confirm` from the model; the yes now counts only against the exact list said within LIST_SECONDS (a module dict per person), so the list-first step is enforced in code, as CLAUDE.md asks of anything that matters. (4) RunBook.recover ran in every constructor; personal_data rebuilds stores in-process (reload_stores after undo, sync), which would have stopped live runs. Recovery now runs once per file per process (_RECOVERED); tests that simulate a restart clear it.

The pattern to look for next time: anything attached to a browser *context* reaches every tab once the browser is shared; anything a constructor does 'at start' also happens at every in-process rebuild of a store; any tool parameter named confirm is the model's word, not the person's, unless code ties it to something the person saw.

Left as it is: the approval sentence for Undo now ends 'This can't be undone.' (true: there's no redo). The sweep in test_action_effects can't see outward calls inside another module's store method.
