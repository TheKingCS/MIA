---
id: K-0348
kind: lesson
title: A safety floor must know what it guards: Fable on the canning rule, query explosion and stemming
status: confirmed
by: claude
created: 2026-11-23T11:37:04+00:00
concerns: core/reference_reader.py, core/pack_index.py, core/offline_library.py, core/question_plans.py, core/tool_loop.py
from: task:T-0060, commit:116e218d
---
Fable reviewed 27b264c8..116e218d (2026-11-23); 13 findings, fixed with tests. The canning floor first deleted correct sentences ("never use a boiling-water bath" was removed for naming the bath) and kept a wrong one, treated pickled beans as low-acid, and fired on "can my chickens eat corn": now it acts only when canning is really asked, stands aside for pickled/acidified foods (USDA Guide 6 water-baths them), keeps a right answer whole, and replaces an answer that tells a low-acid food into a bath with the rule and an offer of the pressure steps; tomatoes get the added-acid rule. The index search sent the raw question (stopwords) into word-subset rounds: 240,000 queries for one question; now the question words only, at most 5, with a deadline, and rounds go on until an index gives enough pages (a page with every word can be the wrong one). _stem's -er rule merged corner/corn and butter/but: gone, canning/canner/canned map to one word. Downloads: a mirror bursting at 20 MB/s then steady at 3 MB/s was failed after 16 tries: the crawl floor is capped and probing happens once a file. Live lessons: the USDA calls green beans snap beans (OTHER_NAMES); a heredoc turned  into a backspace again (write patches with the Write tool).
