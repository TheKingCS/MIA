# MIA OS: sync and consistency (Prompt 12 §17; DEC-0243)

*Claude (Opus), 2026-11-18. Planning only. Built: `core/sync.py`.*

| Case | Rule (built) |
|---|---|
| Changed on one side | that side's copy wins |
| Changed on both | three-way merge against the base: records matched by id; each side's changed fields kept |
| The same field on both | the newer file wins; **planned:** the losing value kept in the history as a conflict note, said to him |
| The history | merged line by line by event id (never rewritten) |
| XP and credits | each side's gains since the base added |
| Photos and files | by fingerprint; changed on both: both kept ("name (2).jpg") |
| Two phones | the PC takes a file only if it's still the version the phone saw (`expect`) |
| The private journal | only between devices holding its key, sealed the whole way, the newer entry wins |

**Provenance:** every merged record keeps who changed it where (the history's device field, planned). **A third
full engine** (the laptop, Q-89) syncs with the hub the same way; engines never sync with each other directly, so
there's one base per device.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DST-023 | When the same field changed on two devices, the losing value shall be kept in the history and he shall be told. | Should | R1 | All | New | T | DEC-0243 → 12 |
| REQ-DST-024 | Every full engine shall sync only with the hub, through the same three-way merge. | Must | MVP | All | Exists (the phone) | T | DEC-0243 → 12 |
