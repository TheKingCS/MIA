---
id: K-0243
kind: implementation
title: M2: MIA answers about her own apps from the registry
status: confirmed
by: claude
created: 2026-11-15T17:50:05+00:00
concerns: core/app_ecosystem.py, core/assistant_app_registry_actions.py, web/apps.js, core/web_surfaces.py
from: dec:DEC-0178, dec:DEC-0175
---
What: core/app_ecosystem.py turns the Application Registry into answers: inventory (by life area, per device), details (an app's tools, actions, stores, jobs, devices, shared domains, dependents), which (exact owner of a tool or action, else apps ranked by content words in their name, description and tools), health (registry problems pinned on the app they name; scheduler jobs failing in a row pinned on the app whose manifest claims the job), overlaps (tools in two apps sharing at least 60% of their description's content words) and gaps (open capability_gaps). Four tools in a new domain app_registry, owned by the Apps app (module_browser): list_my_apps, describe_app, which_app, check_my_apps; registered on the PC (assistant_tools) and the phone (core_runtime). The Apps page's manage view shows the same section (web_surfaces._registry_section, guarded so the page renders without it).
Why this way: answers in code (the model only phrases them); the registry is read once per process because manifests change only with code; overlaps are word similarity, so they're said as suggestions, never faults. The overlap pass over every tool takes about 0.06 s.
What went wrong: the trigger "app for" was too broad (it would attach these tools to "an app for tracking..."), removed; app taglines end with a period, which doubled in sentences.
