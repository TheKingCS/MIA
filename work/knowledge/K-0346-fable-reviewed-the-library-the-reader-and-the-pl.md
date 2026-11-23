---
id: K-0346
kind: lesson
title: Fable reviewed the library, the reader and the Planner: what Windows and real downloads do
status: confirmed
by: claude
created: 2026-11-23T00:39:29+00:00
concerns: core/offline_library.py, core/reference_reader.py, core/tool_loop.py, core/project_plans.py, core/garden_plans.py, core/mission_guide.py
from: task:T-0060, commit:24ad2189, commit:b8fc8049
---
Two Fable reviewers (2026-11-22) read 9243749c, b8fc8049 and 24ad2189; their findings are fixed with tests. Lessons worth carrying: (1) a cap on work read in list order silently skips the end of the list (the reader searched 40 of 74 packs): search everything first, then spend the budget on the best. (2) A mirror that ignores Range answers 200 with the whole file: never reopen the partial for writing on a resume, check 206 and Content-Range. (3) On Windows a file someone has open can neither be deleted nor replaced: libzim holds packs open (keep a remove list, drop her own handle first) and os.replace fails while queue.json is read (retry; never read a failed read as empty; a file lock for read-change-write across MIA and the command line). (4) A just-moved file keeps its recent mtime and the library skips files changed in the last 5 s: date it back. (5) Strict figure checks must know counts from figures by what follows the number (2 methods vs 2 drops), and list markers. (6) Matching names by fragment picks wrong (a matched tomato, potatoes matched sweet potatoes): exact, alias, or all words of one only. (7) Work a change out on a copy, and in the card sentence too, so a bad change is refused before the card and never half-applies. (8) Pair guide steps with objectives by their words, not position.
