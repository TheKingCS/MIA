---
id: K-0347
kind: lesson
title: Finding the right passage in 221 GB: per-index hits, rare words, meaning, and canning
status: confirmed
by: claude
created: 2026-11-23T10:28:58+00:00
concerns: core/reference_reader.py, core/pack_index.py, core/offline_library.py, core/question_plans.py
from: task:T-0060, commit:64d2ecfa, commit:512baed4
---
Asked live on the whole library (2026-11-23), she missed the USDA canning guide for canning green beans and gave a pets answer; fence posts lost their key sentence to the figure check. Fixes, each from a measured miss: (1) bm25 scores from different FTS5 indexes are not one scale, so a big index (Wikibooks, the US map) drowned a small one: take each index own best few (per_index) and rank them ourselves. (2) when no page holds every word, try the rarer ones together (drop the commonest per index) before any word (_queries). (3) can as preserving food is the key word, not a stopword (terms adds canning). (4) weigh words by rarity among the candidates (weighed). (5) words cannot tell a deep cut from prickly pears to cut: re-rank the best 24 by meaning with her local embedding model (nomic, search_query/search_document prefixes, by_meaning), words breaking ties; no model means the words stand. (6) a text that spells numbers (a third, two feet) lets her say them in digits (spelled_numbers). Also on the PC: QtPdf crashed in native code on a ready.gov PDF and silently killed indexing twice; PDFs now go through a worker process. And the downloader used the first mirror even when it crawled: mirrors are probed, the fastest used, and one falling below a quarter of its probe is left (2 MB/s to 34 MB/s).
