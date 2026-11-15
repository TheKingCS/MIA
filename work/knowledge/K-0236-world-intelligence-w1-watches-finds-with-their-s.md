---
id: K-0236
kind: implementation
title: World Intelligence W1: watches, finds with their sources, a worker thread
status: confirmed
by: claude
created: 2026-11-15T15:53:25+00:00
concerns: core/world_intel.py, core/world_sources.py, core/world_intel_actions.py, core/web_world_intel.py, core/assistant_world_intel_actions.py, web/intel.js, core/background_jobs.py
from: dec:DEC-0170, dec:DEC-0171
---
What: core/world_intel.py (Watch, Discovery, WorldBook in world_intel.json, sealed; run_watch, tick, Runner), core/world_sources.py (the checked feed catalog and the feed and search adapters), core/world_intel_actions.py (world_intel.switch, world_watch.add/pause/remove, world_find.save/not_for_me), core/web_world_intel.py and web/intel.html (Finds, Watches, Sources), core/assistant_world_intel_actions.py (eight tools), a glasses card, and the job world_intel every 10 minutes in core/background_jobs.py.

How: a watch's words are phrases (by commas); an item matches when its title and summary hold every word of one phrase (plurals folded). A find is kept once by dedupe_key (link without tracking parameters, fragment or trailing slash; title when there's no link). Every find carries source_name, shown everywhere (Zac: always list the source). New finds are offered to the gate under one topic, world_find, which starts at four a day and learns (DEC-0171); saving a find calls gate.note_engagement.

Why a thread: the fetch is network work; the store is only changed on the job's own thread when Runner.collect() hands the results back, so no lock is needed on the store and the desktop window never waits. A subprocess writing result files was considered and dropped: dynamic file names can't be listed in at_rest.SEALED.

What went wrong: (1) core/assistant_world_actions.py already existed (Living Worlds' voice tools) and the first write replaced it; caught by git status, restored from HEAD, and everything renamed world_intel (Living Worlds also owns the world.* action kinds). Check for an existing file before writing a new one. (2) The first real run brought up twenty old Ollama releases at once: items published over 14 days ago are now skipped. (3) core.web_changes imported before core.actions is a circular import (pre-existing); the page module imports when_words inside its functions, and scripts import core.actions first. (4) On the PC's Python, arXiv and Grants.gov fail certificate checks without certifi; world_sources.get uses it.

Not yet: relevance from the person's records (W2), watches MIA makes herself (W1b), listings and store prices (W3, P phases), the source loop (store:world_intel is todo in work/loop_coverage.json).
