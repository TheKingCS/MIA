---
id: K-0311
kind: implementation
title: A capability's tool, kind, tier and effect are checked as one
status: confirmed
by: claude
created: 2026-11-19T02:56:37+00:00
concerns: core/capability_check.py, core/actions.py, core/deadline.py
from: commit:6d969c8b, dec:DEC-0283
---
LS-04 (DEC-0283): core/capability_check.describe() reads the desktop's tools, ACTION_TYPES, the manifests' tiers and outside tags, and action_effects; disagreements() fails on a tool tiered looser than a kind it proposes (found by reading the handler's source for propose(context, "kind")), an irreversible kind below act_with_approval, a destructive tool at observe or suggest, or no tier. It found four irreversible deletions at act_within_grant. Errors: raise actions.Refused or actions.Unavailable where that's what it is; a plain ActionError is 'invalid', anything else 'failed' (Proposal.error). core/deadline.Deadline.why_not() between steps of outside work.
