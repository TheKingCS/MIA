"""
tests.test_music_module
==========================

Unit tests for modules.music.module's pure formatting functions — no
Qt event loop needed, same shape as tests/test_power_module.py.
"""

from __future__ import annotations

from core.music_manager import NowPlaying, ScanResult, Track
from modules.music.module import format_duration, format_now_playing_line, format_scan_result, format_track_row


def test_format_duration_under_a_minute():
    assert format_duration(45) == "0:45"


def test_format_duration_minutes_and_seconds():
    assert format_duration(225) == "3:45"


def test_format_duration_over_an_hour():
    assert format_duration(3725) == "1:02:05"


def test_format_duration_negative_clamped_to_zero():
    assert format_duration(-5) == "0:00"


def test_format_track_row_with_artist_and_album():
    track = Track(track_id="t1", file_path="/a", title="Blue Skies", artist="Sam", album="Weather", duration_seconds=225)
    assert format_track_row(track) == "Blue Skies — Sam (Weather)   3:45"


def test_format_track_row_without_artist_or_album():
    track = Track(track_id="t1", file_path="/a", title="Untitled Track", duration_seconds=10)
    assert format_track_row(track) == "Untitled Track   0:10"


def test_format_now_playing_line_none():
    assert format_now_playing_line(None) == "Nothing is currently playing."


def test_format_now_playing_line_playing():
    now_playing = NowPlaying(
        track_id="t1", title="Blue Skies", artist="Sam", album="Weather",
        position_seconds=83, duration_seconds=225, is_playing=True, volume_percent=70,
    )
    assert format_now_playing_line(now_playing) == "▶ Blue Skies — Sam   1:23 / 3:45"


def test_format_now_playing_line_paused():
    now_playing = NowPlaying(
        track_id="t1", title="Blue Skies", artist="", album="",
        position_seconds=0, duration_seconds=225, is_playing=False, volume_percent=70,
    )
    assert format_now_playing_line(now_playing) == "⏸ Blue Skies   0:00 / 3:45"


def test_format_scan_result_normal():
    result = ScanResult(added=12, updated=3, unchanged=40, removed=1)
    assert format_scan_result(result) == "Scan complete: 12 added, 3 updated, 1 removed."


def test_format_scan_result_root_missing():
    result = ScanResult(root_missing=True)
    assert format_scan_result(result) == "Could not scan — the library folder isn't currently accessible."
