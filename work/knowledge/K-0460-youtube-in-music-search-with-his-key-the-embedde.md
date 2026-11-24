---
id: K-0460
kind: implementation
title: YouTube in Music: search with his key, the embedded player, songs saved as links
status: confirmed
by: claude
created: 2026-11-24T20:52:03+00:00
concerns: core/youtube_music.py, core/youtube_actions.py, web/music.js, server/app.py
from: file:docs/future/GAME_LAYER_PLAN.md
---
Game layer step 3. A saved YouTube song is a library Track with youtube_id and no file, so playlists, search and track.delete work unchanged; scan_library never removes it, the Qt and phone players never get it (play_queue filters it, _load_track_into_player refuses), and web/music.js plays a list YouTube songs in an embedded youtube-nocookie iframe on the page. The CSP gained exactly frame-src https://www.youtube-nocookie.com and img-src https://i.ytimg.com. Search is YouTube Data API search.list with his key, gated by online_lookup.allowed and scrubbed words; the key goes through POST /api/music/youtube/key (never an action, whose proposal would show and keep it), sealed at rest in youtube_key.json (SEALED, retention device, a key_in reader for the at-rest test). Voice: find/save/play_on_youtube are OUTSIDE_TOOLS (titles are web text); play_on_youtube leaves the song as MIA pick (config music.youtube_next) for one press, because a voice turn has no screen for video. No downloading: YouTube-to-MP3 breaks YouTube terms. Iframe referrerpolicy strict-origin-when-cross-origin because the page sends no referrer and YouTube embeds can refuse without one.
