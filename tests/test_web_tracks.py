"""
tests/test_web_tracks.py — Tracks on the web (core/web_tracks.py, DEC-0099): every track newest first with its numbers
and its shape, the totals, a GPX file kept by `gps_track.add` (a bad one refused before approval) and `gps_track.delete`.
"""

import math
from datetime import date
from types import SimpleNamespace

import pytest

from core.actions import ACTION_TYPES, ActionError
from core.gps_tracks import GpsTracks
from core import web_tracks


def gpx(name="Ridge loop", day="2026-11-01", n=40):
    """A GPX loop of `n` points around a hill, a minute apart, climbing then coming down."""
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / (n - 1)
        ele = 300 + 60 * math.sin(a / 2)
        pts.append(f'<trkpt lat="{45 + 0.01 * math.sin(a):.6f}" lon="{-110 + 0.014 * math.cos(a):.6f}"><ele>{ele:.1f}</ele>'
                   f'<time>{day}T09:{i:02d}:00Z</time></trkpt>')
    return (f'<?xml version="1.0"?><gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1"><trk><name>{name}</name>'
            f'<trkseg>{"".join(pts)}</trkseg></trk></gpx>')


def _ctx(tmp_path):
    """A context with an empty track store in tmp_path."""
    ctx = SimpleNamespace()
    ctx.gps_tracks = GpsTracks(ctx, data_dir=tmp_path)
    return ctx


def test_a_track_kept_from_a_gpx_file_shows_its_numbers_and_shape(tmp_path):
    ctx = _ctx(tmp_path)
    assert "Ridge loop" in ACTION_TYPES["gps_track.add"].describe(ctx, {"gpx": gpx()})
    ACTION_TYPES["gps_track.add"].execute(ctx, {"gpx": gpx()})
    [t] = web_tracks.screen(ctx, date(2026, 11, 9))["tracks"]
    assert t["name"] == "Ridge loop" and t["date"] == "2026-11-01" and t["km"] > 0 and t["climb_m"] > 0
    assert t["time"] == "39 min" and t["shape"].startswith("M") and t["start"]


def test_tracks_are_newest_first_with_totals_for_the_last_month_and_all_time(tmp_path):
    ctx = _ctx(tmp_path)
    ctx.gps_tracks.add_gpx(gpx("Old one", "2026-08-01"))
    ctx.gps_tracks.add_gpx(gpx("New one", "2026-11-05"))
    page = web_tracks.screen(ctx, date(2026, 11, 9))
    assert [t["name"] for t in page["tracks"]] == ["New one", "Old one"]
    assert page["totals"]["count"] == 2 and page["totals"]["count_30"] == 1
    assert page["totals"]["km"] == pytest.approx(2 * page["totals"]["km_30"], abs=0.2)


def test_a_file_that_isnt_gpx_is_refused_before_anything_is_approved(tmp_path):
    ctx = _ctx(tmp_path)
    with pytest.raises(ActionError):
        ACTION_TYPES["gps_track.add"].describe(ctx, {"gpx": "not a gpx file"})
    with pytest.raises(ActionError):
        ACTION_TYPES["gps_track.add"].describe(ctx, {"gpx": "  "})


def test_a_track_is_deleted_and_a_missing_one_is_refused(tmp_path):
    ctx = _ctx(tmp_path)
    track = ctx.gps_tracks.add_gpx(gpx())
    assert ACTION_TYPES["gps_track.delete"].describe(ctx, {"track_id": track["id"]}) == "Delete Ridge loop"
    ACTION_TYPES["gps_track.delete"].execute(ctx, {"track_id": track["id"]})
    assert GpsTracks(ctx, data_dir=tmp_path).tracks == []
    with pytest.raises(ActionError):
        ACTION_TYPES["gps_track.delete"].describe(ctx, {"track_id": track["id"]})


def test_a_shape_fits_its_square_and_needs_two_points():
    d = web_tracks.shape([{"lat": 45, "lon": -110}, {"lat": 45.01, "lon": -110.01}, {"lat": 45.0, "lon": -110.02}])
    nums = [float(x) for x in d.replace("M", "").replace("L", "").split()]
    assert all(0 <= v <= 100 for v in nums)
    assert web_tracks.shape([{"lat": 45, "lon": -110}]) == ""


def test_without_a_track_store_the_screen_says_so():
    assert web_tracks.screen(SimpleNamespace())["available"] is False
