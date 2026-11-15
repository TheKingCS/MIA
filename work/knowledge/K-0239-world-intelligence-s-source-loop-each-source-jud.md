---
id: K-0239
kind: implementation
title: World Intelligence's source loop: each source judged, muting suggested
status: confirmed
by: claude
created: 2026-11-15T16:44:12+00:00
concerns: core/world_intel.py, core/loops.py, core/world_intel_actions.py, web/intel.js, work/loop_coverage.json
from: dec:DEC-0170, dec:DEC-0094
---
What: core/world_intel.source_stats (per source, the last 30 days: finds, saved, set aside, new) and mute_suggestions (eight or more finds, none saved, four or more set aside). WorldBook.muted with set_muted; muted sources are passed to the Runner as skip and never read. The action world_source.mute (by id or by name), the voice tool mute_source, a "How Each Source Is Doing" section on the Sources tab with Mute/Unmute and a "mute?" chip, and the loop world.sources in core/loops.py (person scope, watch: the share of judged finds set aside, floor 0.6, at least five judged; the detail names the sources to mute). It covers store:world_intel, which leaves work/loop_coverage.json; action:world_source is decided "none" there.

Why suggest, not mute: which sources matter is the person's call; the loop shows the evidence and the page has the button. Trying new candidate sources for a month (proposal 5b) isn't built yet: it needs feed discovery from cited sites.

Small lesson: sorting a section of work/loop_coverage.json to insert an entry reshuffled sixteen unrelated lines; insert without sorting.
