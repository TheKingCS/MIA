---
id: K-0256
kind: implementation
title: Appearance A5: the Appearance page and an orb driven by real activity
status: confirmed
by: claude
created: 2026-11-16T07:16:14+00:00
concerns: core/appearance.py, core/orb_state.py, web/studio.js, web/shell.js, web/mia.js, server/app.py, core/actions.py, core/llm_manager.py, core/council.py, core/person_settings.py, core/web_account.py, core/account_actions.py
from: dec:DEC-0184, dec:DEC-0183
---
What: core/appearance.picker gives the Studio's 'Your look' data (theme in use, schemes with three colours and any problem, density, sidebar, effects choices); themes.studio carries it as 'look'. web/studio.js draws it first: a tile per theme rendered from its own tokens (backdrop, panel, accent, frame glow), scheme swatches, segmented spacing/sidebar/effects and the reduced-transparency toggle; pointer and focus preview the look on the page (MIAShell.previewTheme; scheme tokens computed as core does), leaving restores the applied look, a click proposes setting.set and reloads. Layout is now two plain settings (display.density, display.sidebar). The five look keys are in person_settings.PERSONAL_SETTINGS and web_account.SETTINGS; setting.set refuses a scheme scheme_problem rejects. core/orb_state.py counts activities (thinking in LLMManager.generate/chat_with_tools, working around ActionCenter.approve's execute, council around council.answer) and flashes moments (success or warning after approve, notification when the gate delivers, warning when homeostasis backs a job off); /api/live sends a 'presence' event when current() changes; mia.js dispatches it as mia-presence; shell.js sets <html data-presence> and .mia-orb[data-presence-orb], listening coming from the page's own microphone.
What went wrong: the orb's module was first written as core/presence.py, over the existing DEC-0044 'what matters now' list of that name (restored from HEAD; the orb's is core/orb_state.py). Check a file's name is free before writing it. A3's keys weren't personal settings, so a real install stored them for the whole device; fixed. 'speaking' isn't produced: answers aren't streamed, and the orb never shows activity that isn't happening.
