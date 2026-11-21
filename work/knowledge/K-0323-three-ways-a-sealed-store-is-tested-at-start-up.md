---
id: K-0323
kind: method
title: Three ways a sealed store is tested at start-up
status: confirmed
by: claude
created: 2026-11-21T08:24:02+00:00
concerns: tests/test_at_rest.py, tests/test_sealed_stores.py, core/at_rest.py
from: task:WP-04
---
WP-04. tests/test_at_rest.py writes each SEALED file under a key that's gone and checks its store copes (empty, the file copied aside): SEALED_STORES makes a class with data_dir=tmp_path; SEALED_FIXED points every *_FILE Path constant of the module at tmp_path (stores without a data folder: missions, skills, music...); SEALED_READERS calls a function (or 'Class.method', the class made with the folder) with a context whose failures/intents data_dir is tmp_path, the folder, or the path. Names the registry holds that no store writes (boss_book, kitchen, profile, failure_log) are at_rest.NO_FILE. Tests that compared a now-sealed file's bytes must read through open_bytes/open_text; sync works on content, so a test feeding merge_file must too.
