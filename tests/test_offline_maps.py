"""Vector offline maps (core/offline_maps.py): names, the box around waypoints, a map file's header, the cut."""

import struct
from types import SimpleNamespace

import pytest

from core import offline_maps as om


def _fake_pmtiles(path, w=-105.05, s=39.97, e=-104.95, n=40.04):
    head = bytearray(127)
    head[:7], head[7] = b"PMTiles", 3
    head[100], head[101] = 0, 15
    struct.pack_into("<iiii", head, 102, *(round(v * 1e7) for v in (w, s, e, n)))
    head[118] = 12
    struct.pack_into("<ii", head, 119, round(-105.0 * 1e7), round(40.005 * 1e7))
    path.write_bytes(bytes(head) + b"tiles")
    return path


def test_names_and_the_box_around_waypoints():
    assert om.valid_name("home") and om.valid_name("elk-creek_2") and not om.valid_name("../x")
    assert not om.valid_name("Home") and not om.valid_name("")
    w, s, e, n = om.around([(40.0, -105.0), (40.1, -105.2)], km=11.1)
    assert (s, n) == (39.9, 40.2) and w < -105.2 and e > -105.0
    assert om.around([]) is None


def test_a_map_files_header(tmp_path):
    found = om.header(_fake_pmtiles(tmp_path / "home.pmtiles"))
    assert found["max_zoom"] == 15 and found["bounds"] == [-105.05, 39.97, -104.95, 40.04]
    assert found["center"] == [-105.0, 40.005] and found["center_zoom"] == 12
    (tmp_path / "junk.pmtiles").write_bytes(b"not a map")
    assert [m["name"] for m in om.maps(tmp_path)] == ["home"]  # a broken file isn't offered
    assert om.path_of("home", tmp_path) and om.path_of("../home", tmp_path) is None


def test_the_cut(tmp_path, monkeypatch):
    monkeypatch.setattr(om, "TOOL", tmp_path / "pmtiles.exe")
    (tmp_path / "pmtiles.exe").write_bytes(b"")
    ran = []

    def run(cmd, **kw):
        ran.append(cmd)
        _fake_pmtiles(tmp_path / "maps" / "home.pmtiles")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    out = om.extract("home", (-105.05, 39.97, -104.95, 40.04), 14, source="https://build/x.pmtiles", run=run,
                     folder=tmp_path / "maps")
    assert out.name == "home.pmtiles" and ran[0][1:3] == ["extract", "https://build/x.pmtiles"]
    assert "--bbox=-105.05,39.97,-104.95,40.04" in ran[0] and "--maxzoom=14" in ran[0]
    with pytest.raises(ValueError):
        om.extract("home", (10, 0, 5, 1), run=run, folder=tmp_path / "maps")  # west past east
    with pytest.raises(ValueError):
        om.extract("Bad Name", (0, 0, 1, 1), run=run, folder=tmp_path / "maps")


def test_the_newest_build():
    builds = b'[{"key": "20261105.pmtiles"}, {"key": "20261106.pmtiles"}, {"key": "notes.txt"}]'
    assert om.latest_build(get=lambda url: builds) == "https://build.protomaps.com/20261106.pmtiles"
