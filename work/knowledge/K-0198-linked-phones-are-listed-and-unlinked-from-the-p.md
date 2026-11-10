---
id: K-0198
kind: implementation
title: Linked phones are listed and unlinked from the PC
status: confirmed
by: claude
created: 2026-11-10T08:58:24+00:00
concerns: core/linked_devices.py, server/app.py, web/signins.js
from: commit:79608661, file:core/linked_devices.py
---
core/linked_devices.py owns home_link.devices: for_key (stamps last_seen once a day), listed, unlink by a 12-character prefix of the key's hash (never the key), unlink_all. Sign out everywhere and a password change unlink every phone of that person. Before this only the phone could remove its own key, so a lost phone stayed trusted.
