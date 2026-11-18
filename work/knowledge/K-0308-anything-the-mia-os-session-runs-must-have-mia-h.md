---
id: K-0308
kind: debugging
title: Anything the MIA OS session runs must have MIA_HOME set: the image is read-only
status: confirmed
by: claude
created: 2026-11-18T15:38:59+00:00
concerns: os/files/mia-shell, core/logger.py, os/files/mia-runtime.service
from: commit:fb0b9329
---
FW-03's first VM run: KWin started her shell, which died at import because core.logger opened /usr/lib/mia/logs/mia.log inside the read-only image. The runtime's service sets MIA_HOME=%h/.local/share/mia; os/files/mia-shell now exports the same, and the logger falls back to the console when its folder can't be written. Any new program the session or image starts needs MIA_HOME too.
