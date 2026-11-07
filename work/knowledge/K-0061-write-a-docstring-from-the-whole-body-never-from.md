---
id: K-0061
kind: lesson
title: Write a docstring from the whole body, never from its first lines
status: confirmed
by: claude
created: 2026-11-07T09:55:23+00:00
concerns: documentation
from: file:tools/docs.py, dec:DEC-0104
---
Working the documentation backlog, I wrote docstrings for desktop apps from the first eight or nine lines of each method (to move faster). Checked against the full code, about one in ten was wrong: a handler said to refresh three cards refreshed one; a rewards card said 'what's next, by tier' when it shows challenge chains; a row said to show a module's folder when it shows its id and version; a page said to have a refresh button it doesn't. The fix: read the whole body (tools.docs show prints it), and spot-check a sample of what was written against the code before committing. A wrong docstring is worse than none: it is believed.
