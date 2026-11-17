# MIA OS: self-awareness and memory (Prompt 09 §11)

*Claude (Opus), 2026-11-17. Planning only.*

| Memory about herself | Kept in | Exists |
|---|---|---|
| What she learned building herself | knowledge entries (`core/dev_knowledge.py`), handed to whoever next works those files (`for_task`) | yes |
| Lessons from Night School | the report card and lessons per skill | yes |
| What each agent can be trusted with | `core/dev_ledger.py` | yes |
| Her specialists' notes | workbooks (derived until Zac confirms) | yes |
| Her history of changes | git, the change history, life events | yes |
| What she can do now | the capability registry (derived, not memory) | planned |

**Rule:** what she remembers about herself is kept apart from what she remembers about him; self-knowledge never
enters his memories or the recall index of his records, and his private data never enters her development records
(the repository is public).

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-SLF-011 | Her development records shall never hold his personal data, and her self-knowledge shall never be stored as one of his memories. | Must | MVP | All | Exists (the public-repo rule) | T | DEC-0221 → 09, 13 |
