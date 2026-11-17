# MIA OS: memory privacy and his control (Prompt 13 §15)

*Claude (Opus), 2026-11-18. Planning only. Memory: DEC-0210.*

| He can | How | Exists |
|---|---|---|
| See what she remembers | Memories, Your Data | yes |
| Correct or forget one | "forget that", the Memories screen (undoable briefly, then gone; its vectors dropped) | yes / partial |
| Talk off the record | private mode: never stored, traced or indexed | yes |
| See what she read for an answer | Your Data's recent reads (from the traces) | yes |
| Erase what she noted about his apps | Settings › Erase (DEC-0197) | yes |
| Export everything | Your Data › export | yes |
| Delete his account | Your Data › delete, behind his password | yes |

**Forgetting is complete:** a forgotten record leaves its store, the recall index (dropped on the next refresh, never
returned before, since hits are re-read) and the next sync; the undo window keeps it a few minutes only.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-SEC-027 | A forgotten memory shall be gone from its store, the recall index and every synced device after the undo window. | Must | MVP | All | Partial | T | DEC-0210, DEC-0251 → 13 |
