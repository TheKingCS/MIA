---
id: K-0288
kind: implementation
title: The ambient view on a second monitor, flowing to one
status: confirmed
by: claude
created: 2026-11-17T13:02:00+00:00
concerns: core/ambient.py, gui/ambient_screens.py, web/ambient.html, gui/main_window.py
from: dec:DEC-0231
---
What: core/ambient.py shapes Home's own data (web_surfaces.dashboard) into a glanceable view, served at /api/ambient and drawn by web/ambient.html (no sidebar, no Talk, the theme's tokens, the orb from ui.css). gui/ambient_screens.py opens it frameless and full screen on the monitor the main window isn't on, and follows Qt's screenAdded, screenRemoved, primaryScreenChanged and the window's screenChanged; with one monitor it closes (Home holds the same). gui.ambient_screen turns it off. MainWindow starts it in showEvent and stops it in closeEvent, since Switch User rebuilds the window.
Why that way: Zac's Q-80 answer, "if I turn one off she flows with just 1"; gui must not import modules, so the page address is built here like web_home's. The demo example is generated from the dashboard example through shape(), and a test keeps them equal.
