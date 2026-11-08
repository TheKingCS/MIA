---
id: K-0103
kind: implementation
title: Property photos
status: confirmed
by: claude
created: 2026-11-08T02:56:33+00:00
concerns: core/real_estate_manager.py, core/web_screens.py, web/real-estate.js
from: dec:DEC-0125
---
Same shape as asset photos (K-0102): Property.photo is a bare filename under the household property_photos/ folder, property_photo_path reads only its last part, set_property_photo copies JPG/PNG/WebP in as <id>-<time> and keeps the earlier file; property_photo_url links with ?v=<file>. Upload is a raw body to /api/real-estate/property/<id>/photo. Closes step 5 of the web build queue (Q-0014): recipes, assets and properties all have photos.
