"""
tests.test_trail_map_library
================================

Unit tests for core.trail_map_library. Isolates _DATA_DIR/_TRAIL_MAPS_FILE
and root_path into a tmp_path, same pattern as
test_reference_library_manager.py. urllib.request.urlopen() is
monkeypatched for add_from_url() tests — no real network call in this
committed suite (see core/map_tile_cache.py's own tests for the same
reasoning).
"""

from __future__ import annotations

import io

import pytest

import core.trail_map_library as trail_map_library_module
from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.trail_map_library import NotAPdfError, TrailMapLibrary


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    monkeypatch.setattr(trail_map_library_module, "_DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(trail_map_library_module, "_TRAIL_MAPS_FILE", tmp_path / "data" / "trail_maps.json")
    monkeypatch.setattr(trail_map_library_module, "_DEFAULT_ROOT", tmp_path / "trail_maps")


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


def test_starts_empty_when_no_file_exists(isolated_paths):
    library = TrailMapLibrary(_make_context())
    assert library.all_trail_maps() == []


def test_add_from_url_downloads_and_catalogs_a_real_pdf(isolated_paths, monkeypatch):
    monkeypatch.setattr(
        trail_map_library_module.urllib.request,
        "urlopen",
        lambda request, timeout=None: _FakeResponse(b"%PDF-1.4 fake pdf bytes"),
    )

    library = TrailMapLibrary(_make_context())
    trail_map = library.add_from_url("Fall Creek Falls", "Tennessee", "https://example.com/fcf.pdf")

    assert trail_map.park_name == "Fall Creek Falls"
    assert trail_map.state == "Tennessee"
    assert trail_map.source_url == "https://example.com/fcf.pdf"
    assert library.file_path(trail_map.trail_map_id).read_bytes() == b"%PDF-1.4 fake pdf bytes"


def test_add_from_url_rejects_a_non_pdf_response(isolated_paths, monkeypatch):
    monkeypatch.setattr(
        trail_map_library_module.urllib.request,
        "urlopen",
        lambda request, timeout=None: _FakeResponse(b"<html>404 Not Found</html>"),
    )

    library = TrailMapLibrary(_make_context())
    with pytest.raises(NotAPdfError):
        library.add_from_url("Fake Park", "Tennessee", "https://example.com/missing.pdf")
    assert library.all_trail_maps() == []


def test_add_from_local_file_copies_a_real_pdf(isolated_paths, tmp_path):
    source = tmp_path / "my_map.pdf"
    source.write_bytes(b"%PDF-1.4 local file bytes")

    library = TrailMapLibrary(_make_context())
    trail_map = library.add_from_local_file("Cumberland Falls", "Kentucky", source)

    assert library.file_path(trail_map.trail_map_id).read_bytes() == b"%PDF-1.4 local file bytes"


def test_add_from_local_file_rejects_a_non_pdf(isolated_paths, tmp_path):
    source = tmp_path / "not_a_pdf.txt"
    source.write_bytes(b"just some text")

    library = TrailMapLibrary(_make_context())
    with pytest.raises(NotAPdfError):
        library.add_from_local_file("Fake Park", "Kentucky", source)


def test_trail_maps_for_state_filters_case_insensitively(isolated_paths, monkeypatch):
    monkeypatch.setattr(
        trail_map_library_module.urllib.request,
        "urlopen",
        lambda request, timeout=None: _FakeResponse(b"%PDF-1.4"),
    )
    library = TrailMapLibrary(_make_context())
    library.add_from_url("Cumberland Falls", "Kentucky", "https://example.com/a.pdf")
    library.add_from_url("Fall Creek Falls", "Tennessee", "https://example.com/b.pdf")

    kentucky_maps = library.trail_maps_for_state("kentucky")
    assert len(kentucky_maps) == 1
    assert kentucky_maps[0].park_name == "Cumberland Falls"


def test_delete_trail_map_removes_file_and_catalog_entry(isolated_paths, monkeypatch):
    monkeypatch.setattr(
        trail_map_library_module.urllib.request,
        "urlopen",
        lambda request, timeout=None: _FakeResponse(b"%PDF-1.4"),
    )
    library = TrailMapLibrary(_make_context())
    trail_map = library.add_from_url("Cumberland Falls", "Kentucky", "https://example.com/a.pdf")
    file_path = library.file_path(trail_map.trail_map_id)
    assert file_path.exists()

    library.delete_trail_map(trail_map.trail_map_id)

    assert library.get_trail_map(trail_map.trail_map_id) is None
    assert not file_path.exists()


def test_catalog_persists_across_reload(isolated_paths, monkeypatch):
    monkeypatch.setattr(
        trail_map_library_module.urllib.request,
        "urlopen",
        lambda request, timeout=None: _FakeResponse(b"%PDF-1.4"),
    )
    context = _make_context()
    library = TrailMapLibrary(context)
    library.add_from_url("Cumberland Falls", "Kentucky", "https://example.com/a.pdf")

    reloaded = TrailMapLibrary(context)
    assert len(reloaded.all_trail_maps()) == 1
    assert reloaded.all_trail_maps()[0].park_name == "Cumberland Falls"
