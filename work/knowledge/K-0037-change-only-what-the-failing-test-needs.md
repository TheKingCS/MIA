---
id: K-0037
kind: lesson
title: Change only what the failing test needs
status: confirmed
by: claude
created: 2026-11-04T17:00:30+00:00
concerns: tests/test_ocr.py, tests/test_inbox.py, tests/test_textbook_tutor.py, coder:ollama-coder
from: task:T-0019, lab:20261104-61a6b0
---
On T-0019 MIAs coder found the real fix (patching both shutil.which and _WINDOWS_DEFAULT so the OCR test passes with Tesseract installed), but also rewrote the inbox and textbook tests, which broke four others: the lab graded it a fail. Fix the failing test; leave passing ones alone unless the task names them.
