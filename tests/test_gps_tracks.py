"""Tracks (build plan step 14, core/gps_tracks.py): a GPX walk read in code: distance, climb past GPS jitter, moving
time, start and end grids; kept in the person's folder; a line in the TAK package."""

import io
import zipfile
from types import SimpleNamespace

import pytest

from core import gps_tracks as gt
from core import tak

GPX = """<?xml version="1.0"?>
<gpx version="1.1" creator="test" xmlns="http://www.topografix.com/GPX/1/1">
<trk><name>Ridge loop</name><trkseg>
<trkpt lat="38.8895" lon="-77.0353"><ele>100</ele><time>2026-11-01T14:00:00Z</time></trkpt>
<trkpt lat="38.8985" lon="-77.0353"><ele>101.5</ele><time>2026-11-01T14:10:00Z</time></trkpt>
<trkpt lat="38.9075" lon="-77.0353"><ele>140</ele><time>2026-11-01T14:20:00Z</time></trkpt>
<trkpt lat="38.9075" lon="-77.0353"><ele>139</ele><time>2026-11-01T14:50:00Z</time></trkpt>
<trkpt lat="38.8895" lon="-77.0353"><ele>100</ele><time>2026-11-01T15:20:00Z</time></trkpt>
</trkseg></trk></gpx>"""


def test_reading_a_walk():
    name, points = gt.parse_gpx(GPX)
    s = gt.stats(points)
    assert name == "Ridge loop" and s["points"] == 5
    assert s["km"] == pytest.approx(4.0, abs=0.02)  # 1 km + 1 km out, 2 km back
    assert (s["climb_m"], s["descent_m"]) == (40, 40)  # the 1.5 m wobble and the 1 m dip are GPS jitter
    assert s["hours"] == 1.33 and s["moving_hours"] == 0.83  # the half hour standing at the top isn't moving
    assert s["start"] == "18S UJ 2347 0648" and s["date"] == "2026-11-01"
    for bad in ("<gpx/>", "not xml"):
        with pytest.raises(gt.TrackError):
            gt.parse_gpx(bad)


def test_kept_and_asked_about(tmp_path):
    store = gt.GpsTracks(None, tmp_path)
    store.add_gpx(GPX)
    assert gt.GpsTracks(None, tmp_path).tracks[0]["name"] == "Ridge loop"
    context = SimpleNamespace(gps_tracks=store)
    said = gt.reply(context, "how far was my last hike?")
    assert said.startswith("Ridge loop (2026-11-01): 4") and "40 m up" in said and "1 h 20 min" in said
    assert gt.reply(context, "what's for dinner") is None


def test_a_track_is_a_line_in_the_tak_package(tmp_path):
    store = gt.GpsTracks(None, tmp_path)
    track = store.add_gpx(GPX)
    with zipfile.ZipFile(io.BytesIO(tak.data_package([], tracks=[track]))) as z:
        kml = z.read("MIA_places.kml").decode()
    assert "<LineString><coordinates>-77.035300,38.889500,0 " in kml and "Ridge loop" in kml
