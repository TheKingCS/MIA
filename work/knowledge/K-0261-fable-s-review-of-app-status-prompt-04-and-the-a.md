---
id: K-0261
kind: lesson
title: Fable's review of app status, Prompt 04 and the appearance engine (queue items 14 to 23)
status: confirmed
by: claude
created: 2026-11-16T08:37:23+00:00
concerns: core/theme_picture.py, core/themes.py, core/assistant_accessibility_actions.py, core/appearance.py, core/orb_state.py, core/app_ecosystem.py, docs/mia_os/MIA_OS_SYSTEM_REQUIREMENTS.md, tests/test_theme_picture.py
from: dec:DEC-0174, dec:DEC-0184, dec:DEC-0185
---
What was reviewed: M5 app status (core/app_ecosystem.statuses), Prompt 04's sixteen documents, prompt 24's plan, appearance A2 to A7 (tokens and tiers, core/appearance.py, the presets, the Appearance page, core/orb_state.py, colours onto tokens, the apps' colours, core/theme_picture.py, theme_design.adjust, ambient motion).

Found and fixed: (1) core/theme_picture._open set PIL.Image.MAX_IMAGE_PIXELS for the whole process and let Image.open try every decoder Pillow has; a picture arrives from a page upload, so it now opens with formats=("PNG","JPEG","WEBP") and refuses a picture whose header says more than MAX_PIXELS before decoding anything. (2) The glass readability check (appearance.readability_problems) was only a test over built-in themes, though the plan says a failing theme is refused; themes.build_theme now runs it (a late import: appearance is built on themes), so theme.save, theme.import, the designer, mixes and picture themes all get it. (3) adjust_theme's trigger phrases included "make it warmer", "a bit cooler", "make it darker": named_action runs a tool when one phrase starts the message, and DEC-0185 lets MIA adjust greenhouse controllers, so a bare phrase could mean heat; every phrase now names the theme, colours or look, with a test. (4) Prompt 04's handoff section had gone stale after Zac's answers (the greenhouse "never commanded", four decisions "proposed").

Checked and left: orb_state is one state per runtime, so a second person's page would show MIA busy with someone else's turn; fine for one person (DEC-0119), revisit if households return. easing_now is only as fresh as homeostasis's last refresh and expires after ten minutes. statuses() drops a non-failing job with no owning app (none today: every job is in a manifest, a test holds it). A vivid pure yellow accent passes accent_problem (amber's band ends at hue 54).

How to review the next batch: read the trust boundaries first (anything a page or file can send: uploads, theme files, links), then every new trigger phrase against named_action's rule, then the claims documents make about code.
