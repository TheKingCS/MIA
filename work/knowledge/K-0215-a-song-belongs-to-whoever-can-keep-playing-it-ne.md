---
id: K-0215
kind: implementation
title: A song belongs to whoever can keep playing it, never to the Music page
status: confirmed
by: claude
created: 2026-11-11T00:07:21+00:00
concerns: web/player.js, web/shell.js, web/music.js, core/web_more.py, core/music_manager.py, server/app.py, android-phone/app/src/main/java/com/mia/phone/Music.kt
from: file:web/player.js, file:core/web_more.py, file:docs/WEB_PARITY.md
---
Zac, 2026-11-10: music has to keep playing with the Music app closed and while moving through the other apps. It stopped because the song lived in the Music page's own audio element, and every app is its own page. Now one player is shared by every page (web/player.js, window.MIAPlayer: play(tracks, at), control(what), now(), on(fn)) and it picks who plays. In the phone app the phone does (android-phone Music.kt, reached through the MusicBridge added to the web view as window.MIAPhoneMusic; it answers in JSON text and takes only library track ids). In the desktop window MIA does, on the computer's speakers (core/music_manager.py through /api/music/now, /play and /control, assembled in core/web_more.py). In a plain browser the page does, and what was playing and at which second is kept for the tab (sessionStorage) so the next page carries on. The frame (web/shell.js mountPlayer) shows a small bar on every page but Music, which draws its own from the same calls. Why this way: no page outlives a navigation, so the only way a song survives one is for something that isn't a page to play it; the two places Zac uses MIA (the window and the phone app) both already had such a player. What it doesn't do: in a plain browser there is a short gap between pages and the browser may want one tap on Play; the radio page keeps its own audio; closing the PC window ends MIA, so the song ends with her; on the phone a song plays on with the screen off but not after the app is swiped away.
