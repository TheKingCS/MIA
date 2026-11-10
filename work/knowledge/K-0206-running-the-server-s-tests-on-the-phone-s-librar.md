---
id: K-0206
kind: test-procedure
title: Running the server's tests on the phone's libraries
status: confirmed
by: claude
created: 2026-11-10T13:35:38+00:00
concerns: server/app.py, android-phone/app/build.gradle.kts
from: commit:1b0d0f06, file:.github/workflows/windows.yml
---
The phone runs Python 3.13 with fastapi 0.99.1 and pydantic 1.10.27 (android-phone/app/build.gradle.kts, pinned). CI's phone-libraries job installs that set (pydantic with --no-binary and SKIP_CYTHON, as the phone runs it pure Python; Windows' app control also blocks pydantic 1's compiled modules) plus pytest and httpx<0.28 (Starlette 0.27's test client), and runs the server tests through tools.cloud_tests. Left out: web push and numpy tests, which the phone doesn't carry, and one test that uses a newer test client's option.
