---
id: K-0108
kind: implementation
title: Health records
status: confirmed
by: claude
created: 2026-11-08T06:42:16+00:00
concerns: core/health_manager.py, core/health_actions.py, core/assistant_health_actions.py, web/health.js
from: dec:DEC-0129, dec:DEC-0126
---
One personal store, core/health_manager.HealthStore (health.json, in PERSONAL_STORES, sealed at rest from its first save). Sleep by night (re-logging replaces), visits with next_due, medications as written on the label with times turned into daily alarms labelled only 'Medication time' (the alarm store is device-wide, so a name there would show on a shared screen), doses taken, records as given. core/health_actions.py makes every change an action and builds the page with its forms; due visits and refills feed core/today.py. MIA never suggests a dose or reads a result: tools repeat what was said.
