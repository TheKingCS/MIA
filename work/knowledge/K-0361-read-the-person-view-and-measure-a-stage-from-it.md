---
id: K-0361
kind: lesson
title: Read the person view, and measure a stage from its own start
status: confirmed
by: claude
created: 2026-11-24T01:49:03+00:00
concerns: core/picture_of_you.py, core/paths.py, core/evening_wrap.py, core/bushcraft.py, core/fitness_path.py, core/gardening_path.py, core/woodworking.py
from: commit:09140ff9
---
Sixth fresh review (2026-11-23): picture_of_you built PathBook(context=context) with no data_dir, so it read the device file, not the person own book (context.paths from view_for): use the view stores, never construct a store. Recorded learning checks counted from the path start, so stage 2 workouts passed stage 3 minutes: PathBook.attempt now keeps stage_since per stage and measure reads from it. The evening wrap named the alarm as tomorrow first thing (today_items puts alarms first): module toolbox skipped. Safety wording tightened in the hobby programs (red end of the needle, filters and viruses, jerky to 160F, chest pain means emergency services, router table direction).
