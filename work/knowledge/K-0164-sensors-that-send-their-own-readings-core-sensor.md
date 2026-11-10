---
id: K-0164
kind: implementation
title: Sensors that send their own readings (core/sensors.py)
status: confirmed
by: claude
created: 2026-11-09T08:49:05+00:00
concerns: core/sensors.py, server/app.py, web/sensors.js, core/glasses_cards.py
from: dec:DEC-0019, dec:DEC-0125
---
Greenhouse, Power and the Lab took readings by hand only. A person adds a sensor on the Sensors page (POST /api/sensors, not an action: its key is a secret and actions are logged); the key is shown once and kept as its SHA-256. The sensor posts {value, note} to /api/sensors/reading with X-Sensor-Key; core/sensors.reading finds it in constant time, refuses a non-number, NaN or a reading within MIN_GAP (30 s), and runs the app's own reading action (lab_reading.add, energy.reading, grow.reading) on view_for(owner): ranges, charts and findings treat it like any reading. A key can only log a number to its own series; no reads, no sign-in; the forwarded-request switch applies. Greenhouse measures are the grow lab's MEASURES, accepted by id or label. sensor.remove stops the key; readings stay. Voice list_sensors; glasses Lab → Sensors (amber after a quiet day). The store is the device's (data/sensors.json), each sensor naming its person. It's the general path DEC-0019 approved; DEC-0150's greenhouse node (its registry, alerts) can use it or replace it when Zac answers.
