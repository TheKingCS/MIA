---
id: K-0099
kind: implementation
title: Pictures in Knowledge articles
status: confirmed
by: claude
created: 2026-11-08T02:21:03+00:00
concerns: core/reference_library_manager.py, server/app.py, web/knowledge.js
from: dec:DEC-0125
---
Articles stay plain text on the web (no foreign HTML in MIA's page); their pictures come separately. article_images (pure) reads each <img>, resolves its src against the article's folder with posixpath, and drops web links, data: URIs, anything that climbs out of the pack and icons under 60px; at most 12, each once. /api/knowledge/picture serves an entry only when its mimetype is image/*, so the endpoint can't be used to pull the pack's HTML or scripts into the page. knowledge.js loads each through MIA.image (auth'd blob URL) and removes a figure whose picture fails.
