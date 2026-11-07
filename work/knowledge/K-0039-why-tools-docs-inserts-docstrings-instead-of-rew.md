---
id: K-0039
kind: implementation
title: Why tools.docs inserts docstrings instead of rewriting files
status: confirmed
by: claude
created: 2026-11-07T04:59:59+00:00
concerns: tools/docs.py
from: commit:df1122f
---
What: tools/docs.py edits source files only by inserting text, never by regenerating them.
How: it reads the file with ast to find each definition's body line and indentation, inserts the docstring there, refuses a definition that already has one or a body on the def line, then parses the result again; if it no longer parses, nothing is written.
Why: a rewrite (for example through ast.unparse) would drop comments and change formatting across the whole file, making the diff unreadable and losing what the comments say. Inserting keeps every other byte as it was, so a reviewer sees only the new docstrings.
