"""
tests.test_map_tile_cache
=============================

Unit tests for core.map_tile_cache. urllib.request.urlopen() is
monkeypatched (same "mock the external query, test our own caching/
decision logic" reasoning as test_avatar_manager.py mocking
QMediaDevices/test_power_manager.py mocking psutil) — no real network
call happens in this committed suite, keeping `pytest` runnable
offline per this project's own offline-first testing stance. A real
live fetch against the actual USGS/OSM tile services is exercised
separately as a one-off smoke check, not part of this file.
"""

from __future__ import annotations

import io

import pytest

import core.map_tile_cache as map_tile_cache_module
from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.map_tile_cache import MapTileCache
from core.map_tile_math import tiles_covering_bbox


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    monkeypatch.setattr(map_tile_cache_module, "_DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(map_tile_cache_module, "_TILE_CACHE_DIR", tmp_path / "data" / "map_tiles")


class _FakeResponse:
    def __init__(self, data: bytes) -> None:
        self._buffer = io.BytesIO(data)

    def read(self) -> bytes:
        return self._buffer.read()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _make_context() -> AppContext:
    return AppContext(config=ConfigManager(), events=EventBus())


def test_is_cached_false_when_nothing_downloaded_yet(isolated_paths):
    cache = MapTileCache(_make_context())
    assert cache.is_cached("usgs_topo", 8, 71, 95) is False


def test_fetch_tile_downloads_and_caches(isolated_paths, monkeypatch):
    calls = []

    def fake_urlopen(request, timeout=None):
        calls.append(request.full_url)
        return _FakeResponse(b"fake-jpeg-bytes")

    monkeypatch.setattr(map_tile_cache_module.urllib.request, "urlopen", fake_urlopen)

    cache = MapTileCache(_make_context())
    path = cache.fetch_tile("usgs_topo", 8, 71, 95)

    assert path.exists()
    assert path.read_bytes() == b"fake-jpeg-bytes"
    assert cache.is_cached("usgs_topo", 8, 71, 95) is True
    assert len(calls) == 1
    assert "/8/95/71" in calls[0]  # z/y/x order, confirmed against the live service


def test_fetch_tile_does_not_re_download_an_already_cached_tile(isolated_paths, monkeypatch):
    call_count = 0

    def fake_urlopen(request, timeout=None):
        nonlocal call_count
        call_count += 1
        return _FakeResponse(b"fake-jpeg-bytes")

    monkeypatch.setattr(map_tile_cache_module.urllib.request, "urlopen", fake_urlopen)

    cache = MapTileCache(_make_context())
    cache.fetch_tile("usgs_topo", 8, 71, 95)
    cache.fetch_tile("usgs_topo", 8, 71, 95)

    assert call_count == 1


def test_different_sources_are_cached_independently(isolated_paths, monkeypatch):
    monkeypatch.setattr(
        map_tile_cache_module.urllib.request, "urlopen", lambda request, timeout=None: _FakeResponse(b"x")
    )
    cache = MapTileCache(_make_context())
    usgs_path = cache.fetch_tile("usgs_topo", 4, 2, 3)
    osm_path = cache.fetch_tile("osm", 4, 2, 3)

    assert usgs_path != osm_path
    assert usgs_path.suffix == ".jpg"
    assert osm_path.suffix == ".png"


def test_osm_tile_url_uses_standard_z_x_y_order(isolated_paths, monkeypatch):
    calls = []

    def fake_urlopen(request, timeout=None):
        calls.append(request.full_url)
        return _FakeResponse(b"x")

    monkeypatch.setattr(map_tile_cache_module.urllib.request, "urlopen", fake_urlopen)
    cache = MapTileCache(_make_context())
    cache.fetch_tile("osm", 4, 2, 3)

    assert calls[0] == "https://tile.openstreetmap.org/4/2/3.png"


def test_ensure_region_cached_fetches_only_missing_tiles(isolated_paths, monkeypatch):
    bbox = dict(min_lat=34.98, min_lon=-90.35, max_lat=39.15, max_lon=-81.6)
    tiles_at_zoom_6 = tiles_covering_bbox(zoom=6, **bbox)
    pre_cached_x, pre_cached_y = tiles_at_zoom_6[0]

    monkeypatch.setattr(
        map_tile_cache_module.urllib.request, "urlopen", lambda request, timeout=None: _FakeResponse(b"x")
    )

    cache = MapTileCache(_make_context())
    cache.fetch_tile("usgs_topo", 6, pre_cached_x, pre_cached_y)

    fetched_urls = []
    monkeypatch.setattr(
        map_tile_cache_module.urllib.request,
        "urlopen",
        lambda request, timeout=None: (fetched_urls.append(request.full_url), _FakeResponse(b"x"))[1],
    )

    count = cache.ensure_region_cached("usgs_topo", zoom_levels=(6,), **bbox)

    assert count == len(tiles_at_zoom_6) - 1  # every tile except the pre-cached one
    assert not any(f"/6/{pre_cached_y}/{pre_cached_x}" in url for url in fetched_urls)


def test_ensure_region_cached_calls_progress_callback_for_every_tile(isolated_paths, monkeypatch):
    monkeypatch.setattr(
        map_tile_cache_module.urllib.request, "urlopen", lambda request, timeout=None: _FakeResponse(b"x")
    )

    cache = MapTileCache(_make_context())
    progress_calls = []
    cache.ensure_region_cached(
        "usgs_topo",
        min_lat=34.98,
        min_lon=-90.35,
        max_lat=39.15,
        max_lon=-81.6,
        zoom_levels=(6,),
        on_progress=lambda done, total: progress_calls.append((done, total)),
    )

    assert len(progress_calls) > 0
    last_done, last_total = progress_calls[-1]
    assert last_done == last_total


def test_ensure_region_cached_skips_a_failing_tile_without_aborting(isolated_paths, monkeypatch):
    import urllib.error

    call_count = 0

    def flaky_urlopen(request, timeout=None):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise urllib.error.URLError("simulated failure")
        return _FakeResponse(b"x")

    monkeypatch.setattr(map_tile_cache_module.urllib.request, "urlopen", flaky_urlopen)

    cache = MapTileCache(_make_context())
    # Should not raise even though the first tile's fetch fails.
    count = cache.ensure_region_cached(
        "usgs_topo", min_lat=34.98, min_lon=-90.35, max_lat=39.15, max_lon=-81.6, zoom_levels=(6,)
    )
    assert count >= 1  # at least the later tiles succeeded


def test_worldwide_overview_constants_are_internally_consistent(isolated_paths):
    from core.map_tile_cache import (
        TILE_SOURCES,
        WORLDWIDE_OVERVIEW_SOURCE,
        WORLDWIDE_OVERVIEW_ZOOM_LEVELS,
        WORLDWIDE_BOUNDS,
    )

    assert WORLDWIDE_OVERVIEW_SOURCE in TILE_SOURCES
    assert len(WORLDWIDE_OVERVIEW_ZOOM_LEVELS) > 0
    min_lat, min_lon, max_lat, max_lon = WORLDWIDE_BOUNDS
    assert min_lat < max_lat
    assert min_lon < max_lon


def test_ensure_region_cached_worldwide_overview_is_small(isolated_paths, monkeypatch):
    """Confirms the worldwide overview really is the small, one-time
    footprint the module's docstring claims — not accidentally a much
    bigger fetch than intended."""
    from core.map_tile_cache import WORLDWIDE_BOUNDS, WORLDWIDE_OVERVIEW_ZOOM_LEVELS

    monkeypatch.setattr(
        map_tile_cache_module.urllib.request, "urlopen", lambda request, timeout=None: _FakeResponse(b"x")
    )
    # This test alone fetches ~341 simulated tiles — skip the real
    # per-tile rate-limit delay (irrelevant against a fake response)
    # so the committed suite doesn't pay ~17s for it.
    monkeypatch.setattr(map_tile_cache_module.time, "sleep", lambda seconds: None)
    cache = MapTileCache(_make_context())
    min_lat, min_lon, max_lat, max_lon = WORLDWIDE_BOUNDS
    count = cache.ensure_region_cached("osm", min_lat, min_lon, max_lat, max_lon, WORLDWIDE_OVERVIEW_ZOOM_LEVELS)

    assert count < 500  # measured directly at 341 tiles before picking this range
