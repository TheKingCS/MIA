---
id: K-0038
kind: method
title: How to document a file so the words match the code
status: confirmed
by: claude
created: 2026-11-07T04:59:59+00:00
concerns: tools/docs.py, core/code_atlas.py, docs/ATLAS.md
from: dec:DEC-0104, commit:df1122f
---
What: DEC-0104 asks for a docstring on every class, function and method, saying what it is, what it does and how.
How: `python -m tools.docs next 20` lists the biggest backlogs (engine first). `python -m tools.docs show core/x.py` prints each undocumented definition with its code. Write the docstrings as JSON {file: {name: text}} and run `python -m tools.docs apply docs.json`: it puts each one after the full signature, re-parses the file, lowers work/doc_baseline.json and regenerates docs/ATLAS.md. Then run tests/test_documentation.py and the file's own tests.
Why this way: a docstring is a claim about the code, so every claim gets checked against the code before it goes in (which file it writes, which action kind, what the default is). Several wrong claims were caught this way: processed/ that was really imported/, a decisions file under the wrong name, a store said to be the household's that is the person's own. When a docstring and the code disagree, the code is right.
