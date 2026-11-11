---
id: K-0216
kind: lesson
title: The music player is asked from the server's thread and only plays on the window's
status: confirmed
by: claude
created: 2026-11-11T00:07:21+00:00
concerns: core/music_manager.py, core/web_more.py, server/app.py
from: file:core/music_manager.py, file:tests/test_music_manager.py
---
A QMediaPlayer only plays on the GUI thread, and the web pages' requests arrive on the server's thread. Every playback method of MusicManager is wrapped in _on_gui_thread: on another thread it hands the work to context.main_thread_call and waits up to _GUI_WAIT_SECONDS for the answer. Three things follow. A wrapped method can return None (the window was too busy to answer in time; the work still runs when it gets there), so callers test `is False` for a real refusal, as music_control does for next past the last song. The server's player calls run outside the turn lock (_player in server/app.py), because waiting on the window's thread while holding the lock a window action may want would hang both. And where there is no window (tests, the phone's own engine) main_thread_call is None, the method runs where it was called, and music_plays_here() says the page has to play instead.
