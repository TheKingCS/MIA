---
id: K-0300
kind: method
title: CI is the gate: actions pinned by commit, least permissions, the suite inside the image
status: confirmed
by: claude
created: 2026-11-18T13:17:44+00:00
concerns: .github/workflows/, tests/test_ci_workflows.py
from: task:FW-02, dec:DEC-0264, file:tests/test_ci_workflows.py
---
FW-02 (2026-11-18). Every action is pinned to the commit its tag named when pinned (annotated tags peeled twice: gradle/actions v4 is a tag of a tag), the tag kept as a comment; to move one, resolve the new tag with gh api repos/<owner>/<repo>/git/ref/tags/<tag> and peel until the object is a commit. Workflows say permissions: contents: read unless a job needs more. The VM test copies the tracked files into the booted image and runs the whole suite as the person with the image own venv, because the image leaves out folders the tests read. Windows CI stays on 3.12 (the PC), Linux on 3.13 (the image). tests/test_ci_workflows.py keeps all of this and keeps Windows user folders out of code and settings.
