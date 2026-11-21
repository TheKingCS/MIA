---
id: K-0322
kind: method
title: Sealing an appended log a line at a time
status: confirmed
by: claude
created: 2026-11-21T07:45:19+00:00
concerns: core/at_rest.py, tests/test_sealed_stores.py
from: task:WP-04
---
WP-04. A .jsonl log goes in at_rest.LINE_SEALED; its writer appends seal_line(path, json.dumps(entry)) (out.name works as the path inside the with-open), its readers use open_text (a line that won't open stays as it was, so json.loads skips it), and a trim reads the raw lines (no need to open them) and writes the tail back through atomic_write_text, which seals any plain ones. Older plain lines keep reading. tests/test_sealed_stores.py checks every writer of a LINE_SEALED name calls seal_line.
