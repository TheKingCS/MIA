---
id: K-0056
kind: method
title: How documentation keeps up with changed code
status: confirmed
by: claude
created: 2026-11-07T07:53:10+00:00
concerns: core/doc_freshness.py, tools/docs.py, core/work_review.py
from: dec:DEC-0110, file:core/doc_freshness.py
---
What: core/doc_freshness.py compares two versions of each changed Python file. For every class, function and method in both, it compares the code with the docstring, decorators and nested definitions taken out (as a syntax-tree dump, so moving lines or blank lines don't count), and lists the ones whose code changed while their docstring stayed exactly the same. A changed parameter list is marked strongest. A file's opening is asked about when public definitions came or went.
Why decorators don't count: @life_events.on_change was added to 109 methods in one day; it adds history, not a new job, and listing all of them would bury the real ones. Why private helpers don't trigger the file check: the first run flagged every file that gained a _helper, which was noise.
How to use it: python -m tools.docs stale before committing (exit 1 when there's something to read); every lab review gets the list; dev.doc_freshness watches a week of commits. A docstring that still holds needs no change.
