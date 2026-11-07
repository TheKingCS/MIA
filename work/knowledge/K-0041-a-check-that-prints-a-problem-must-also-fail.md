---
id: K-0041
kind: lesson
title: A check that prints a problem must also fail
status: confirmed
by: claude
created: 2026-11-07T04:59:59+00:00
concerns: tools/docs.py
from: dec:DEC-0104
---
What happened: the script comparing the documented names against the undocumented list printed what was missing but exited 0, so the chain of commands carried on and one function (build_worksheet) went in undocumented; it was fixed in a follow-up commit. A test run piped into tail also hid a failure because the pipe's status was tail's.
Lesson: any check in a chain must exit non-zero on a problem, and a pipeline needs `set -o pipefail`, or a failure looks like success.
