---
id: K-0463
kind: debugging
title: Every real online lookup failed: connectivity.status is a property, not a method
status: confirmed
by: claude
created: 2026-11-24T21:30:18+00:00
concerns: core/online_lookup.py, core/connectivity.py
from: file:core/online_lookup.py
---
Found by a server-level test of YouTube search (tests/test_server_game_layer.py): core/online_lookup.allowed called context.connectivity.status(), but core/connectivity.py exposes status as a property, so the call raised TypeError (not caught) and look_up_online failed on every real Core where the monitor runs. Its unit tests faked status as a lambda, so they passed. Fixed to read the attribute and call it only if callable; a test now uses the real shape. Lesson: a fake must match the real object shape; a test through the real server context catches what fakes hide.
