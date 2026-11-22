---
id: K-0329
kind: implementation
title: Device records, scoped keys and the lost device's erase
status: confirmed
by: claude
created: 2026-11-22T13:56:38+00:00
concerns: core/linked_devices.py, server/app.py, core/home_link.py, web/signins.js
from: task:WP-10, dec:DEC-0242
---
WP-10 (DEC-0242, Q-90). home_link.devices entries are linked_devices.record(): profile_id, name (the device in words from its user agent, never its address), kind, scope (person or household), linked; listed() adds stale after 90 days unseen. require_profile_id (now taking the Request) refuses a device key outside its scope (allows: a household key reaches HOUSEHOLD_ROUTES, /api/live until WP-20 adds the display's view). Lost on Sign-ins (/api/security/devices/lost, mark_lost) moves the record to home_link.lost: the key is refused at once and, when it next asks, answered 410 with X-MIA-Erase (logged device_erased once). The device's home_call sees that answer and erase_here() removes everything in its DATA_DIR (the .keys folder too: crypto-erase) and forgets the link. Only home_call checks it, so a device erases on its next sync or screen call, best effort. Conflict notes were already built in core/sync.py.
