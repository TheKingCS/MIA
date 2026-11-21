---
id: K-0320
kind: method
title: How to seal a store at rest
status: confirmed
by: claude
created: 2026-11-21T04:25:02+00:00
concerns: core/at_rest.py, tests/test_sealed_stores.py, tests/test_at_rest.py
from: commit:5b196628, commit:747466ee
---
WP-04. A file can be sealed only when every reader goes through at_rest.open_text (or open_bytes) and catches ValueError (UnreadableFile is one; json.JSONDecodeError alone isn't enough) with OSError, and it's written through atomic_write_text. Then: its name to at_rest.SEALED, its class to tests/test_at_rest.py SEALED_STORES (needs a data_dir constructor: the start-up test writes it sealed under a lost key and expects an empty store and a copy aside), off at_rest.NOT_SEALED_YET, and lower NOT_SEALED_YET_MOST. Tests that read the file plainly after a write must read through open_text. Appended .jsonl logs need line sealing instead.
