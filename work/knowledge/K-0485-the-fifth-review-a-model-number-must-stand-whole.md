---
id: K-0485
kind: lesson
title: The fifth review: a model number must stand whole, and routes need their own exclusions
status: confirmed
by: claude
created: 2026-11-25T12:03:50+00:00
concerns: core/part_specs.py, core/assistant_path_actions.py, core/esp32_sim.py, core/esp32_path.py
from: commit:e73c992d
---
The fifth independent review found seven bugs in a part from a photo, the not-started course and the watchdog lab, each fixed with a test (tests/test_review_labs_5.py). A spec matched by any word of its name ('push', 'buzzer', 'capacitive') fired on ordinary photos: a photo's answer now needs a model number with a digit, standing whole. Refusing a course not started also refused a started one's own words ('woodworking basics' is Carpentry's). New voice routes took other tools' requests ('what does the pot lab print?', 'why won't it upload?', 'simulator'). And a check whose marker two paths print (FALLBACK from the quiet and from BOOT) passed on the wrong one: a check's marker should come from one cause only.
