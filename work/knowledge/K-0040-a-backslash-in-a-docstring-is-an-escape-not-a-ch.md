---
id: K-0040
kind: debugging
title: A backslash in a docstring is an escape, not a character
status: confirmed
by: claude
created: 2026-11-07T04:59:59+00:00
concerns: tools/docs.py, tests/test_documentation.py
from: commit:c356748, commit:8320ff2
---
What happened: a docstring describing an unescape function contained a backslash sequence; Python read it as an escape and printed a SyntaxWarning (and a backslash-n would have broken the line).
Fix: the docstring was reworded without backslashes, and tools.docs now refuses any docstring containing one, with a test (test_putting_docstrings_in_place).
Lesson: when words describe escaping, say it in words ("a backslash before a comma") instead of typing the characters, and compile every changed file to be sure there are no warnings.
