---
id: K-0285
kind: implementation
title: Approve Once or Approve From Now On on every card (DEC-0215)
status: confirmed
by: claude
created: 2026-11-17T11:48:38+00:00
concerns: core/kind_grants.py, core/actions.py, core/grants.py, web/shell.js, tests/test_kind_grants.py
from: dec:DEC-0215
---
What: core/kind_grants.py. grantable(kind): tier act_within_grant and effect ('records', 'undoable'), not grant.*, steps.*, history.*, undo.* (373 of 482 kinds). The person setting grants.kinds holds {kind: {given, last_used}}; live() drops ones unused for 90 days or no longer grantable. ActionCenter.approve(..., from_now_on=True) refuses a non-grantable kind before anything runs and keeps the standing yes only once the change executed. ActionCenter.propose(..., proposed_by='mia') approves at once when the kind is granted and marks the proposal auto (a caller that proposes then approves gets the executed proposal back). grants.standing lists them as kind:<kind>; take_back ends one. Proposal.as_dict has grantable; the web confirm box shows Approve From Now On beside Approve Once where it may; POST /api/actions/{id}/approve?from_now_on=true.

Why this way: Zac chose a button on every card over waiting for five approvals; the trust ladder's evidence offer stays as a reminder. A standing yes only ever applies to a proposal MIA's own code made, through the same describe and execute, so nothing she reads can trigger or widen one.

Gotcha: docs/schema/action.schema.json forbids extra properties; new Proposal fields need it updated (test_actions' schema checks caught it).
