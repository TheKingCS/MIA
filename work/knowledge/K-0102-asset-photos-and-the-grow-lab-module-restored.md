---
id: K-0102
kind: implementation
title: Asset photos, and the Grow Lab module restored
status: confirmed
by: claude
created: 2026-11-08T02:46:57+00:00
concerns: core/maintenance_manager.py, core/web_equipment.py, web/asset.js, web/equipment.js, web/grow.js, web/grow-redirect.js
from: commit:d795fb4, dec:DEC-0125
---
Asset photos follow recipe photos: MaintenanceAsset.photo is a bare filename under the household's data_dir/asset_photos/, read back only by its last path part (asset_photo_path), set by set_asset_photo (JPG/PNG/WebP, named <id>-<time> so the earlier file stays and undoing the record change shows it). The link carries ?v=<filename> so a new photo is never cached stale. Upload is a raw body to /api/garage/asset/<id>/photo, not an action (no bytes in proposals). While checking it, the asset page redirected to the Greenhouse: d795fb4 had moved grow.html's inline redirect into web/grow.js, replacing the Grow Lab module (window.MIAGrow) that asset.html and greenhouse.html load. Restored the module from d795fb4^ and moved the redirect to grow-redirect.js; tests/test_web_scripts.py checks shared modules still define their globals and that no page borrows one as a redirect.
