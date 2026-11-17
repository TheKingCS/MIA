# MIA OS: files and documents (Prompt 10 §15)

*Claude (Opus), 2026-11-17. Planning only.*

| Need | Through | Exists |
|---|---|---|
| Browse, move, copy | Dolphin (KDE's file manager) | planned |
| Her files screen (recent, project folders, favourites) | `files.html` (`myfile.*` actions) | yes |
| Preview | KDE's thumbnailers; her readers for PDFs and photos | partial |
| Search | Baloo (§ unified search) | planned |
| Understand, summarise | Talk, on a shared file | partial |
| Organise | proposals ("move these 12 receipts to Finances?"), each an action with undo | partial |

**His files stay his**: in his home, ordinary folders, owned by him. MIA never moves, renames or deletes a file
without an approved action; a file deletion that can't be undone is tiered as needing approval every time
(`myfile.delete`: irreversible). Cloud storage is his apps' (Nextcloud, a browser), not hers.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DSK-024 | MIA shall never move, rename or delete his files except by an approved action, and a deletion she can't undo shall ask every time. | Must | MVP | All | Exists (myfile tiers) | T | DEC-0213 → 10, 13 |
