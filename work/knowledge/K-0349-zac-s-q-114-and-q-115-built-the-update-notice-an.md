---
id: K-0349
kind: implementation
title: Zac's Q-114 and Q-115 built: the update notice and the Daylight theme
status: confirmed
by: claude
created: 2026-11-23T17:50:49+00:00
concerns: core/update_notice.py, core/themes.py, core/appearance.py, web/themes.css
from: dec:DEC-0287, dec:DEC-0288
---
Q-114 (DEC-0287): core/update_notice.py reads /run/ostree/staged-deployment (world-readable, so no privilege) and offers one gate message per staged update (fingerprint = the file's time); Settings shows Restart To Update and the tool restart_to_update only proposes system.apply_update (act_with_approval). Q-115 (DEC-0288): Theme.light; clean_theme keeps MEANING_TOKENS only when the data says light AND the panels are light (is_light, 10:1 on black) AND meaning_problems finds nothing (each shade within 15 degrees of its meaning's hue, 4.5:1 on white, rgb triplets matching). What went wrong first: the light theme broke three other checks: colour schemes' accents (cyan at 2:1 on white) and each app's own colour (--rgb-atmo-*) were tuned for dark fields; both now get darker shades of the same hue on a light theme (appearance.scheme_colours via themes.deepen; web/themes.css [data-light=1]); and clean_theme writes tier tints as '0' not '0.0', so a built-in must use the cleaned form. export() leaves light out, so Studio and imported themes are never light.
