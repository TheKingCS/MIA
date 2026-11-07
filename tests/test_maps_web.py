"""Maps' web screen (core/maps_web.py): cached tiles by the cache's rules, and the waypoints."""

from types import SimpleNamespace

from core import maps_web


def test_which_tiles_may_be_asked_for():
    assert maps_web.allowed("usgs_topo", 12, 800, 1500)
    assert not maps_web.allowed("osm", 5, 0, 0)  # OpenStreetMap: the world overview only
    assert not maps_web.allowed("usgs_topo", 17, 0, 0) and not maps_web.allowed("usgs_topo", 2, 4, 0)
    assert not maps_web.allowed("google", 1, 0, 0)


def test_a_tile_from_the_cache_or_fetched_once(tmp_path):
    fetched = []

    def tile_path(source, z, x, y):
        return tmp_path / source / str(z) / str(x) / f"{y}.jpg"

    def fetch_tile(source, z, x, y):
        fetched.append((z, x, y))
        if x == 99:
            raise OSError("offline")
        path = tile_path(source, z, x, y)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"jpg")
        return path

    ctx = SimpleNamespace(map_tiles=SimpleNamespace(tile_path=tile_path, fetch_tile=fetch_tile))
    assert maps_web.tile(ctx, "usgs_topo", 3, 1, 2).read_bytes() == b"jpg"
    assert maps_web.tile(ctx, "usgs_topo", 3, 1, 2) is not None and fetched == [(3, 1, 2)]  # kept: once
    assert maps_web.tile(ctx, "usgs_topo", 9, 99, 2) is None  # offline: no tile, no error
    assert maps_web.tile(ctx, "osm", 9, 1, 2) is None and len(fetched) == 2  # not allowed: never fetched


def test_centred_on_the_waypoints():
    points = [SimpleNamespace(waypoint_id="a", name="A", category="", latitude=40.0, longitude=-105.0),
              SimpleNamespace(waypoint_id="b", name="B", category="", latitude=40.2, longitude=-105.2)]
    data = maps_web.screen(SimpleNamespace(waypoints=SimpleNamespace(all_waypoints=lambda: points)))
    assert data["center"] == {"lat": 40.1, "lon": -105.1} and data["zoom"] == 12
    assert maps_web.screen(SimpleNamespace(waypoints=None))["zoom"] == 4
