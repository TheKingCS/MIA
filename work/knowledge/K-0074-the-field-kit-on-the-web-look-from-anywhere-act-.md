---
id: K-0074
kind: implementation
title: The Field Kit on the web: look from anywhere, act on the PC
status: confirmed
by: claude
created: 2026-11-07T18:01:25+00:00
concerns: core/web_field_kit.py, web/field-kit.js
from: dec:DEC-0125, dec:DEC-0113
---
core/web_field_kit.py serves /api/field-kit: the external drives and USB serial boards plugged into the computer MIA runs on (core/device_framework.py), the script library by category with each script's content (cut at 20,000 characters) to read and copy, and two network checks answered by check() at /api/field-kit/check (a hash's kind, a subnet from its CIDR). Deliberately read only: ejecting or flashing a drive, running a script and the port scan stay on the PC, beside the device or where a script's output can be watched and stopped; each tab says so and links there (/desktop-open/field_kit on the desktop, Ask MIA elsewhere). Password strength is left off the web on purpose so a password is never sent to the server to be scored. With this, every app has a web page except Diagnostics (owner page) and Settings.
