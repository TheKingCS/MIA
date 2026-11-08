---
id: K-0131
kind: lesson
title: Claim before building: 'don't bring that up' was built twice at once
status: confirmed
by: claude
created: 2026-11-08T16:21:56+00:00
concerns: docs/NEXT_SESSION.md
from: dec:DEC-0146, file:docs/NEXT_SESSION.md
---
While the engine session built DEC-0146's 'don't bring that up', the design session claimed it in docs/NEXT_SESSION.md and shipped a fuller version (its own page, API route, schema). The engine's copy was local and unpushed, so it was dropped: git merge --abort, git reset --soft HEAD~1, then git restore --staged --worktree on only the files that commit touched (never reset --hard: the tree holds other people's uncommitted work). The rule in NEXT_SESSION's 'Who builds what': screens are the design session's, voice tools and routing the parity session's, core logic the engine's; read the claims and add yours before starting.
