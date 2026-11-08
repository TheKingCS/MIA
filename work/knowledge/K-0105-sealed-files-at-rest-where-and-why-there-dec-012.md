---
id: K-0105
kind: decision
title: Sealed files at rest: where and why there (DEC-0126)
status: confirmed
by: claude
created: 2026-11-08T03:36:08+00:00
concerns: core/at_rest.py, core/atomic_write.py, core/sync.py
from: dec:DEC-0126, file:core/at_rest.py, file:tests/test_at_rest.py
---
The most private stores' files (at_rest.SEALED: conversations, memories, notes, life notes) are sealed with AES-256-GCM inside atomic_write_text, because every store already writes through it; reads go through at_rest.open_text, which reads sealed or plain, so a store moves at its next save with no migration step. The data key is 32 random bytes protected by Windows DPAPI in data/.keys/data_key.json: nothing to type at start, useless on another account or PC. Each envelope names its key id so a recovered key opens old files. What went wrong or nearly did: stores that can't read their file start empty and their next save replaces it, so a sealed file that won't open is copied aside before the error; a key file that won't open is never replaced (sealing stops and the security log alerts); sync compared raw bytes, which differ on every seal (random nonce), so sync and the /api/sync/file endpoints use open_bytes; tests that read conversations.json directly needed open_text. To seal another store: add its file name to SEALED and make its _load use open_text; grep for any other reader of that file name first.
