---
id: K-0104
kind: implementation
title: Parts per asset
status: confirmed
by: claude
created: 2026-11-08T03:02:55+00:00
concerns: core/asset_parts.py, core/assistant_asset_part_actions.py, core/web_equipment.py, web/asset.js
from: dec:DEC-0125
---
No new store: an asset's parts are stated links in core/links.py, asset:<id> REQUIRES <inventory_item|material|component>:<id>, so they also show in the link graph and undo covers them. core/asset_parts.py lists them with stock (stock_state is pure: a material is low at or under its reorder level, anything is out at zero), out and low first; the asset page's Parts tab and three voice tools use the same two actions. Out and low are amber (needs you), not red: the design standard keeps red for errors, overdue and destructive actions. The old test asserting parts were PLANNED was updated.
