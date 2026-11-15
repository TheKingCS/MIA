---
id: K-0244
kind: implementation
title: M3: the app list is read from the manifests
status: confirmed
by: claude
created: 2026-11-15T18:08:46+00:00
concerns: core/web_surfaces.py, core/app_registry.py, tools/app_manifests.py, android-phone/app/build.gradle.kts
from: dec:DEC-0178
---
What: the hand-kept APPS tuple in core/web_surfaces.py (156 lines) is gone; _apps_from_manifests() builds the same App objects from apps/*/manifest.json sorted by a new `order` field, with new `ask` and `domains` fields, and RETIRED from each manifest's `retired`. The registry check gained: no two apps share a sidebar place, and an app's shared domains (uses) are in its own domains. tools/app_manifests.py write --force now keeps what only a person writes (version, permissions, dependencies, services, agents, workflows, integrations, x- keys).
How it was proven: the new fields were generated from the hand list first, and the App tuples rebuilt from the manifests compared equal to the hand list (all 56, in order, and the retired set) before the list was deleted; regenerating afterwards reproduced the same manifests.
What nearly went wrong: the phone app bundles MIA's code by an include list in android-phone/app/build.gradle.kts (core/**, server/**, web/**), so it would have shipped with no apps at all; apps/*/manifest.json was added and a test guards it. An empty list is logged as an error. Anything else that packages the code by folder needs apps/ too.
