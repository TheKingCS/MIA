---
id: K-0142
kind: implementation
title: MIA checks her docs against her repository every week
status: confirmed
by: claude
created: 2026-11-08T18:50:43+00:00
concerns: core/inspection.py, core/self_audit.py, tests/test_inspection.py
from: task:T-0020, dec:DEC-0071
---
T-0020 (DEC-0071 point 1): core/inspection.py gained a `repository` subject. repository_findings() reads the repository itself: reference docs (CLAUDE.md and docs/*.md, leaving out history and generated docs and forward-looking PROPOSAL/PLAN/REVIEW docs) naming a file that isn't there, accepting a dotted reference to a module (core/x.attr); an APPROVED decision that says it's built naming a missing code file (skipped when it says nothing is built); a requirement not installed. The weekly self-audit runs it as its third audit and opens one task for the top finding nobody has looked at (source audit:doc:/dec:/req:...). Why this way: the rules are narrow so the first run on the real repository gave zero findings; a noisy audit gets ignored. Read-only.
