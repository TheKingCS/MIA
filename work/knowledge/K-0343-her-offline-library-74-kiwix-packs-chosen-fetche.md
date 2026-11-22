---
id: K-0343
kind: implementation
title: Her offline library: 74 Kiwix packs chosen, fetched with Kiwix's hash, and indexed where Kiwix didn'
status: confirmed
by: claude
created: 2026-11-22T23:25:02+00:00
concerns: core/offline_library.py, core/pack_index.py, core/assistant_library_actions.py, core/reference_library_manager.py, web/knowledge.js
from: task:T-0060
---
Zac asked (2026-11-22) for as many offline resources as would make her the most useful offline assistant. core/offline_library.py holds the chosen packs (PACKS, 14 shelves, sets essential/standard/big; his country's map from core/region, never named in code), reads Kiwix's OPDS catalog (library.kiwix.org, kept a day beside the packs), and fetches through a queue one runner at a time (a lock file), resumed with HTTP Range. Trust: the size and SHA-256 come from the metalink on lb.download.kiwix.org over HTTPS; the bytes may come from any mirror, and a file that doesn't hash right is thrown away. What went wrong first: (1) list_packs skips a file changed in the last 5 s, so a just-installed pack isn't listed at once; (2) 22 of the 74 packs have no Kiwix full-text index (iFixit, the canning guide, LibreTexts, devdocs, the preppers' collections), and even an indexed pack's index never covers the PDFs inside it, so libzim found nothing for 'purify water with bleach' in the water pack. core/pack_index.py fixes that: her own SQLite FTS5 index per pack (pages when Kiwix gave none, PDFs always, through QtPdf), built after each download and for packs copied in by hand; big indexed packs (Wikipedia, the Q&A sites) are left to Kiwix's. (3) A PDF's own title can be junk ('Microsoft Word - Water.doc'): pdf_name cleans it. look_up_offline merges both searches, ranks by the question's words and frames the passages with browser_safety.outside. The suite never reaches Kiwix: published() and run_queue() do nothing with the real network under pytest.
