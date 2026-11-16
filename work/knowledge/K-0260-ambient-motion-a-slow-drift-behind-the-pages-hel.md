---
id: K-0260
kind: implementation
title: Ambient motion: a slow drift behind the pages, held still whenever it should be (appearance A7)
status: confirmed
by: claude
created: 2026-11-16T08:25:56+00:00
concerns: core/appearance.py, core/homeostasis.py, core/person_settings.py, core/web_account.py, core/assistant_accessibility_actions.py, web/shell.js, web/themes.css, web/studio.js, docs/schema/appearance.schema.json, docs/schema/themes.example.json, tests/test_appearance.py
from: dec:DEC-0184, dec:DEC-0173
---
What: a per-person setting display.ambient (off or drift, off unless chosen) in core/appearance.py, sent with the look from /api/shell with `easing` (core/homeostasis.easing_now). web/shell.js sets <html data-ambient>, makes a fixed .theme-ambient layer behind the page, and sets data-ambient-held to why it's held (hidden: visibilitychange; battery: navigator.getBattery and chargingchange; easing: from the look). web/themes.css draws three radial glows in --rgb-accent, -2 and -3 on a layer 140% of the screen, animating only transform over 90 s (alternate). Held: animation-play-state paused (it stays where it is rather than vanishing). Still: reduced motion, effects light or none. Hidden: high contrast, reduced data. Choosable in Settings (Look › Background motion), the Appearance page's Your Look, and by voice through set_layout's `motion`.

Why this way: the plan's fallbacks (MIA_OS_APPEARANCE_ENGINE B: pause when hidden, on battery, or while homeostasis eases off; light effects and reduced motion stop backdrop movement). transform-only keeps it on the compositor. Off by default because motion behind reading can bother, and the reference picture is still.

What went wrong or nearly did: (1) homeostasis lived inside the runtime's background jobs with no page-facing state; a module-level reading time (_EASED_AT, set in Homeostasis.refresh when busy or battery) with a ten-minute freshness window gives the pages a signal without plumbing the runtime into appearance. It's only as fresh as the last refresh (each deferrable job's turn); a stale 'busy' expires by itself. (2) Under the Stark theme the layer was invisible: the body's own background painted over z-index -1 because only non-Stark themes isolate the body; the body is now isolated whenever the drift is on. (3) The Studio's demo data (docs/schema/themes.example.json) must carry every picker key (a test compares them); it was extended in place, keeping its formatting.

Not yet proven: smoothness and battery behaviour on the phone, a check for Zac's next phone session.
