---
id: K-0035
kind: decision
title: Do not skip or disable tests to achieve green status
status: derived
by: mia
created: 2026-11-04T08:26:58+00:00
concerns: tests/test_ocr.py, tests/test_inbox.py, tests/test_textbook_tutor.py, tests/conftest.py
from: task:T-0019
---
Tests should not be skipped, disabled, marked as xfail, or deleted to achieve a green status. Instead, modify the tests to control their dependencies and ensure they pass regardless of external factors like Tesseract being installed.
