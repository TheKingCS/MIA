---
id: K-0196
kind: implementation
title: The file writer keeps a file's old contents before a large shrink
status: confirmed
by: claude
created: 2026-11-10T08:58:24+00:00
concerns: core/atomic_write.py
from: commit:5697f59c, file:core/atomic_write.py
---
atomic_write_text copies a file of 512 bytes or more to .<name>.prev when the new contents are under half its size, and retries os.replace on PermissionError (Windows refuses it while a reader holds the file). Why there: about a hundred stores start empty when their read fails and their next save would write that over the file; one guard in the one writer protects all of them with no call-site change. The copy is hidden (sync skips dot files), one per file, and removed after three days so a deliberate clear-out doesn't linger.
