---
id: K-0234
kind: implementation
title: MIA_HOME: one setting for where a person's MIA lives
status: confirmed
by: claude
created: 2026-11-15T13:21:06+00:00
concerns: core/data_root.py, tools/move_home.py, core/at_rest.py, deploy/install_runtime.sh
from: dec:DEC-0155, dec:DEC-0168, dec:DEC-0126
---
What: core/data_root.py reads the environment variable MIA_HOME once at import. Unset: HOME is the code's folder, exactly the old layout. Set: DATA_DIR, CONFIG_DIR, LOG_DIR, the user folders beside data (trip_photos, trail_maps, maintenance_documents, lite_captures, homestead_snapshots, financial_snapshots, reference_library) and WORK_DIR are under it. 131 files in core/ and server/ were changed by script: `Path(__file__).resolve().parent.parent / "data"`, `ROOT / "data"` and `_PROJECT_ROOT / "data"` became DATA_DIR; each module keeps its own `_DATA_DIR`/`_FILE` names, so the tests that monkeypatch them didn't change.

What ships with the code and stays there (SEED_DIR, CODE_ROOT): skill_definitions.json, mission_pathways.json, foods.tsv, model_bench_cases.json, default_config.json, blueprints/. For work/: what MIA writes (tasks, activity.jsonl, council.jsonl, review lessons, saga, missions, STOP) goes to WORK_DIR; what ships (knowledge, parity.json, loop_coverage.json, doc_baseline.json, known_failures.json, agents.json, specialists, night_school.json) is read through work_path(): the home's copy if it has one, else the code's.

How it's checked: tests/test_data_root.py runs the runtime in a fresh interpreter with MIA_HOME set, adds a person and a mission, forces all ten jobs, and compares every file's size and mtime under the code tree before and after: no difference allowed. A static test refuses any `parent.parent / "data"` (or config, logs) outside data_root.py. The first manual run found the only leak: work/activity.jsonl and a task a loop opened.

tools/move_home.py: refuses while MIA runs on the source, a target that holds a MIA, or a target inside a copied folder; copies; verifies size and SHA-256 per file; never deletes. Logs, the lock file and shipped seed files aren't copied.

The important finding: at_rest's data key is DPAPI-protected (Windows account). On Linux `_blocked` is "this system has no DPAPI; files stay plain", and a sealed file raises UnreadableFile after being copied aside, so stores start empty. Copying the PC's data to Fedora therefore shows nothing until a Linux key backend exists (restore() itself refuses without DPAPI). move_home counts sealed files and stops unless --sealed-ok where dpapi_available() is false.

Not done: gui/, modules/ and tools/ still name `ROOT / "data"` in a few places (the desktop app on Windows runs with MIA_HOME unset, so nothing changes there; they need the same treatment before the window runs on MIA OS). The phone sets its own root by where the code is unpacked.
