---
id: K-0115
kind: decision
title: Two looks per person: Spatial and Cards (DEC-0135)
status: confirmed
by: claude
created: 2026-11-08T11:34:15+00:00
concerns: core/display_style.py, web/shell.js, web/welcome.js, web/hub.js, core/web_account.py
from: dec:DEC-0135
---
Zac liked both the new spatial Nexus and the earlier cards design (especially on the phone), so the look is a per-person setting, display.style (core/display_style.py): spatial, cards, or auto (the default: spatial on the computer, cards on the phone). Core only stores the choice and hands it to every page in shell()['display']; the page resolves auto itself (MIAShell.look(), max-width 760px = phone) because only it knows the device. What follows the look: welcome.js opens on the Nexus only in spatial; hub.js draws the Garage room only in spatial (cards keeps its flat cards); the sidebar and the phone's bottom bar put Nexus or Home first; body gets look-spatial or look-cards for styling. Every feature is the same in both. Changed in Settings ('Look', setting.set, approved and undoable) and by voice (set_display_style, wants_style parses 'the old look', 'portals', 'cards on my phone'). Along the way the 'health' tool domain was attached to the Workout app, which test_every_assistant_tool_belongs_to_an_app had caught.
