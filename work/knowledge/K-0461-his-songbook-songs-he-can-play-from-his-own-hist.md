---
id: K-0461
kind: implementation
title: His songbook: songs he can play, from his own history
status: confirmed
by: claude
created: 2026-11-24T21:06:52+00:00
concerns: core/repertoire.py, core/rewards_manager.py
from: file:docs/future/GAME_LAYER_PLAN.md
---
core/repertoire.py keeps songs learned as song_learned life events in the person own folder (personal_life_events), like jars canned: dated, never a second store, undone by reversed_ids. One per song per instrument. The rewards stat songs_learned feeds the Songbook chain (1/5/15/30/75) and mission records objectives (STATS), and publishes activity.logged so the tier unlocks at once. Screen: Music Can Play tab (song.learned); voice: learned_a_song, songs_i_can_play. Watch: a heredoc mangled backslashes in a split script again; Write the helper.
