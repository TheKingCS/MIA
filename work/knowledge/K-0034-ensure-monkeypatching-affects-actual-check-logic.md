---
id: K-0034
kind: debugging
title: Ensure monkeypatching affects actual check logic
status: withdrawn
by: mia
created: 2026-11-04T08:26:58+00:00
concerns: tests/test_ocr.py, tests/test_inbox.py, tests/test_textbook_tutor.py, tests/conftest.py
from: task:T-0019, review:T-0019@2026-11-03T21:22:18+00:00, resolve:T-0019@2026-11-03T21:23:18+00:00
---
The test `test_unavailable_without_tesseract` modified `_WINDOWS_DEFAULT` using `monkeypatch.setattr`, but the actual check for Tesseract availability is done via `shutil.which`. This modification was necessary because `_WINDOWS_DEFAULT` is used in the fallback logic when Tesseract is not on the PATH.

Withdrawn by claude: its title turns the reviewers mistaken objection into a lesson; the record shows the objection was answered and overturned (_WINDOWS_DEFAULT is used, core/ocr.py:74).
