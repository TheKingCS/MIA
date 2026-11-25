---
id: K-0478
kind: lesson
title: A course's labs page: one frame, and two traps on the way
status: confirmed
by: claude
created: 2026-11-25T07:07:02+00:00
concerns: core/lab_page.py, web/course.js, web/mia.js, core/esp32_path.py, core/paths.py
from: commit:abcbd8b1, commit:6da6ccab
---
Built web/course.html (core/lab_page.py, GET /api/labs/{course}, POST /api/labs/{course}/read), step 2 of docs/future/INTERACTIVE_LABS_PLAN.md: the course map, the lab chosen, the sketch, Flash This Lab (esplab.flash), Start This Course (path.start) and a serial monitor that reads the board and checks the lab. page() is course-neutral; another area adds its labs in _labs().

What went wrong: (1) web/lab.html and MIA.lab() already existed (the Data Logger's Lab). A second `lab:` key in mia.js's object would have silently replaced the first, so the Data Logger page would have read the course. Check a name in web/ and in mia.js before using it; the Write tool refusing an unread file caught this one. (2) paths.next_step finds the lesson behind a check by check.about in lesson.about; the ESP32 checks' about is the board's marker spec and the lessons had none, so every check named the stage's first lesson. esp32_path._tied now ties each lesson to the checks its own sketch prints. A new Program whose checks use about for something else needs the same tie.

Demo mode reads docs/schema/course.example.json (made from page() itself); phone width needs min-width: 0 on grid children holding a <pre>.
