"""
The world map with fog of war (DEC-0028): finished trips, arrivals,
photos with GPS and "I'm Here" clear tiles; waypoints nobody has reached
stay in the fog; new ground earns achievements and XP.
"""

import struct

import pytest

from core.actions import ActionCenter
from core.world_map import WorldMap, along, explored, exif_gps, ranks, regions, tile_of, world_page
from tests.engine_world import build_world


@pytest.fixture
def world(tmp_path, monkeypatch):
    context = build_world(tmp_path, monkeypatch)
    context.actions = ActionCenter()
    context.world_map = WorldMap(context, data_dir=context.my_dir)
    from core.expedition_manager import ExpeditionManager
    from core.trip_manager import TripManager
    from core.waypoint_manager import WaypointManager

    context.waypoints = WaypointManager(context, data_dir=context.home_dir)
    context.expeditions = ExpeditionManager(context, data_dir=context.home_dir)
    context.trips = TripManager(context, data_dir=context.home_dir)
    return context


def do(world, kind, **params):
    proposal = world.actions.propose(world, kind, params)
    done = world.actions.approve(world, proposal.proposal_id)
    assert done.status == "executed", done.result
    return proposal, done


def jpeg_with_gps(lat, lon):
    """A tiny JPEG whose EXIF says where it was taken (little-endian TIFF)."""
    def dms(x):
        x = abs(x)
        d = int(x)
        m = int((x - d) * 60)
        s = round(((x - d) * 60 - m) * 60 * 100)
        return [(d, 1), (m, 1), (s, 100)]
    gps_ifd = 26  # after the header (8) + IFD0 (2 + 12 + 4)
    entries, data_at = 4, gps_ifd + 2 + 4 * 12 + 4
    lat_at, lon_at = data_at, data_at + 24
    ifd0 = struct.pack("<H", 1) + struct.pack("<HHII", 0x8825, 4, 1, gps_ifd) + struct.pack("<I", 0)
    gps = struct.pack("<H", entries)
    gps += struct.pack("<HHI", 1, 2, 2) + (b"N" if lat >= 0 else b"S") + b"\x00\x00\x00"
    gps += struct.pack("<HHII", 2, 5, 3, lat_at)
    gps += struct.pack("<HHI", 3, 2, 2) + (b"E" if lon >= 0 else b"W") + b"\x00\x00\x00"
    gps += struct.pack("<HHII", 4, 5, 3, lon_at) + struct.pack("<I", 0)
    rationals = b"".join(struct.pack("<II", n, d) for n, d in dms(lat) + dms(lon))
    tiff = b"II*\x00" + struct.pack("<I", 8) + ifd0 + gps + rationals
    app1 = b"Exif\x00\x00" + tiff
    return b"\xff\xd8" + b"\xff\xe1" + struct.pack(">H", len(app1) + 2) + app1 + b"\xff\xd9"


def test_pure_bits():
    lat, lon = exif_gps(jpeg_with_gps(47.6062, -122.3321))
    assert abs(lat - 47.6062) < 1e-3 and abs(lon + 122.3321) < 1e-3
    assert exif_gps(b"not a jpeg") is None and exif_gps(b"\xff\xd8\xff\xd9") is None
    pts = along((47.0, -122.0), (47.0, -121.9))
    assert len(pts) >= 8 and pts[0] == (47.0, -122.0) and pts[-1] == (47.0, -121.9)
    tiles = explored([{"lat": 47.0, "lon": -122.0, "reveal": "around", "day": "2026-10-01"}])
    assert len(tiles) == 9 and regions(tiles) in (1, 2)
    earned = [r["name"] for r in ranks(12, 2) if r["earned"]]
    assert earned == ["First Steps", "Wanderer", "Day Tripper"]


def test_trips_arrivals_and_the_fog(world):
    a = world.waypoints.add_waypoint("Trailhead", 47.50, -121.80)
    b = world.waypoints.add_waypoint("Summit", 47.53, -121.75)
    world.waypoints.add_waypoint("Hidden Lake", 47.70, -121.60)
    x = world.expeditions.add_expedition("Mountain weekend")
    trip = world.trips.add_trip(x.expedition_id, "Summit day", start_date="2026-10-10", end_date="2026-10-10")
    world.trips.update_trip(trip.trip_id, waypoint_ids=[a.waypoint_id, b.waypoint_id], status="completed")
    page = world_page(world)
    assert page["stats"]["tiles"] >= 9 and page["stats"]["places"] == 2 and page["stats"]["to_discover"] == 1
    assert [p["label"] for p in page["pins"] if p["kind"] == "unknown"] == ["Hidden Lake"]
    assert set(world.world_map.first_seen)  # remembered the day each was cleared
    assert any(r["earned"] for r in page["ranks"])


def test_a_photo_is_pinned_where_it_was_taken(world):
    from core.expedition_media import save

    x = world.expeditions.add_expedition("Coast trip")
    save(world, x.expedition_id, "beach.jpg", jpeg_with_gps(45.9, -123.96))
    pins = [p for p in world_page(world)["pins"] if p["kind"] == "photo"]
    assert len(pins) == 1 and pins[0]["label"] == "Coast trip" and abs(pins[0]["lat"] - 45.9) < 1e-3


def test_im_here_clears_new_ground_once(world):
    prop, done = do(world, "map.checkin", lat=40.0, lon=-105.0)
    assert "9 new tiles" in prop.summary and "+45 XP" in done.result
    prop, done = do(world, "map.checkin", lat=40.0, lon=-105.0, label="Home")
    assert "been here before" in prop.summary and "explored here before" in done.result
    assert world_page(world)["stats"]["tiles"] == 9
    with pytest.raises(Exception):
        world.actions.propose(world, "map.checkin", {"lat": "nope", "lon": 1})
    x, y = tile_of(40.0, -105.0)
    assert f"{x},{y}" in world.world_map.first_seen
