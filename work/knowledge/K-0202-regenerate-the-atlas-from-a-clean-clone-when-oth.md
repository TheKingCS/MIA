---
id: K-0202
kind: method
title: Regenerate the atlas from a clean clone when other sessions have work open
status: confirmed
by: claude
created: 2026-11-10T08:58:24+00:00
concerns: docs/ATLAS.md, work/doc_baseline.json
from: file:core/code_atlas.py, file:tests/test_documentation.py
---
core/code_atlas.py counts every file on disk, so on a PC where another session has uncommitted files the regenerated docs/ATLAS.md describes their unpublished files and CI's clean checkout fails test_the_atlas_is_current. Clone the commit into a scratch folder, run python -m core.code_atlas and core.code_atlas baseline there, and copy ATLAS.md and work/doc_baseline.json back.
