---
id: K-0043
kind: implementation
title: MIA answers about herself from her code and the vault, not only the docs
status: confirmed
by: claude
created: 2026-11-07T05:11:42+00:00
concerns: core/self_docs.py, tests/test_capabilities.py
from: dec:DEC-0104, dec:DEC-0105, file:core/self_docs.py
---
What: core/self_docs.py (the get_mia_docs tool and the council) searched only docs/*.md. It now also searches every docstring in core/, server/, tools/, modules/ and gui/ (one passage per file and per definition, as core.x.name) and the Knowledge Vault's live entries.
How: ast reads each file (about a second for 600 files, rebuilt only when a file's time changes; checking the times costs about 25 ms). Each source kind has a weight: a decision 3, a doc 2, a team entry 1.8, a code docstring 1, her own unconfirmed write-up 0.9. So a decision or doc on a subject still comes first, and the code answers the how-does-this-work questions the docs never covered. Withdrawn and superseded entries are left out; her unconfirmed ones say so.
Why: Zac wants MIA to understand her own architecture well enough to restore herself, run efficiently and one day build models of her own (DEC-0106). The docstrings (DEC-0104) and the vault (DEC-0105) are useless to her if she can't reach them when asked. Tests are left out because they say what's checked, not how she works.
