---
id: K-0248
kind: implementation
title: M5: each app's status from one place
status: confirmed
by: claude
created: 2026-11-16T04:54:20+00:00
concerns: core/app_ecosystem.py, core/web_surfaces.py, web/apps.js, tests/test_app_ecosystem.py
from: dec:DEC-0178, dec:DEC-0057
---
What: core/app_ecosystem.statuses(reg, context) gives every app {status, why}: failing (a record that won't load, or a job at BACKOFF_AFTER failures in a row), missing_dependency (a dependency not here or retired), needs_attention (a job that failed lately, an open tool_error, page_error or action_failed issue from the Fix-It Log in the last 7 days pinned by tool through owner_of or by page through the manifests' web pages, or a store reset by data_recovery in the last 7 days), hidden (web_surfaces._visible), retired, working. health() is now the apps not working. apps_page carries status and status_why per app; web/apps.js shows a chip (failing in the bad tone, the rest amber) and the reasons on the card. describe_app says it. _apps_from_manifests logs an app whose dependency isn't there at start.
Why this way: core/capabilities.capability_status already says what's implemented (DEC-0057); M5 is the other half, whether it works now, and both read from the same records. Status never comes from the model.
What to know: a reset store is found by file name; _recovered maps names by every .json/.jsonl string or Path its store's module defines (88 of 91 stores; freedom_log, fitness and plaid have none). A module defining files for several stores pins them on the first. 'running' isn't tracked, and a Qt module that fails to import isn't pinned yet.
