# MIA OS: store formats and migrations (Prompt 15; DEC-0267)

*Claude (Opus), 2026-11-18. Planning only. MIA's stores are JSON files (some JSONL), many sealed.*

| Change | How |
|---|---|
| A new field | added with a default; old files read fine (most changes) |
| A renamed or reshaped field | **a migration**: the store gains `schema_version`; on load an older file is backed up (`.v<N>.bak`), migrated forward in code, written atomically; a test loads a fixture of every older version |
| A removed field | left in old files, ignored on read |
| A new store | added to the personal or household list, the at-rest list if it holds personal data, its loop decision |
| Rollback | an older MIA reads a newer file because changes are additive; a migrated file is kept beside its backup until the next update succeeds |

Sync merges records by id and keeps unknown fields, so two devices on different versions don't drop each other's data.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DEV-020 | A store whose shape changes other than additively shall carry a schema version, back the old file up and migrate it on load, with a test over every older version. | Must | R1 | All | New | T | DEC-0267 → 15, 14 |
