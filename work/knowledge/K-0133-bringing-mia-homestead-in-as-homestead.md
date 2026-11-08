---
id: K-0133
kind: implementation
title: Bringing MIA Homestead in as homestead/
status: confirmed
by: claude
created: 2026-11-08T16:21:56+00:00
concerns: pytest.ini, CLAUDE.md, core/homestead_manager.py
from: dec:DEC-0145
---
The sibling repo became homestead/ by git subtree add --prefix=homestead with all its history (94 commits), checked byte-identical by comparing tree hashes (HEAD:homestead against the fetched tree). Not at the root: it has its own core/ and modules/, which would collide with MIA's; it stays self-contained (its own CLAUDE.md, requirements, database and scenario suite, run from inside homestead/). A root pytest.ini (testpaths = tests) keeps the two core packages apart; collection was unchanged. subtree add refuses a dirty tree, so it ran in a separate worktree. Its scenarios run 242 of 245 on Windows: the 3 need rsync. The safety check held back pushing another repository's history onto master until Zac says yes.
