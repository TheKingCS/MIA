"""Grid references and TAK (build plan step 14, DEC-0099): MGRS worked out in code (checked against pyproj and the
mgrs package: 4,000 random points agreed to the metre, 2026-11-06; the reference outputs are pinned here), and
MIA's waypoints as a TAK data package of Cursor on Target events and KML."""

import io
import zipfile
from datetime import datetime, timezone
from types import SimpleNamespace
from xml.etree import ElementTree as ET

import pytest

from core import geo_grid as g
from core import tak

# (lat, lon) -> the mgrs package's own answer
REFERENCE = {
    (38.8895, -77.0353): "18S UJ 23478 06483",  # the Washington Monument
    (60.0, 5.0): "32V KM 76979 58157",  # south-west Norway: zone 32, not 31
    (78.2, 15.6): "33X WG 13696 80760",  # Svalbard: zone 33
    (-33.8568, 151.2153): "56H LH 34900 52288",  # the Sydney Opera House
}


def test_the_reference_points():
    for (lat, lon), want in REFERENCE.items():
        assert g.to_mgrs(lat, lon) == want


def test_back_and_forth_and_precision():
    for (lat, lon), ref in REFERENCE.items():
        back = g.from_mgrs(ref)
        assert abs(back[0] - lat) < 2e-5 and abs(back[1] - lon) < 2e-5  # within a couple of metres
    assert g.to_mgrs(38.8895, -77.0353, 3) == "18S UJ 234 064"  # 100 m
    lat, lon = g.from_mgrs("18SUJ2306")  # 1 km: the middle of that square
    assert g.to_mgrs(lat, lon, 2) == "18S UJ 23 06"
    assert g.from_mgrs("56hlh3490052288")[0] < 0  # southern hemisphere, any case


def test_what_isnt_a_reference():
    for bad in ("hello", "18S UJ 123 45", "61S UJ 1 1"):
        with pytest.raises(g.GridError):
            g.from_mgrs(bad)
    with pytest.raises(g.GridError):
        g.to_mgrs(89.0, 0.0)  # the poles use UPS


def waypoint(wid="w1", name="Spring & well", lat=38.8895, lon=-77.0353, notes="Fresh <cold> water"):
    return SimpleNamespace(waypoint_id=wid, name=name, latitude=lat, longitude=lon, notes=notes, category="Water Source")


def test_a_cursor_on_target_event():
    event = ET.fromstring(tak.cot_event(waypoint(), datetime(2026, 11, 6, 12, tzinfo=timezone.utc)))
    assert event.get("type") == tak.MARKER and event.get("uid") == "MIA-w1" and event.get("stale").startswith("2027-11-06")
    assert event.find("point").get("lat") == "38.8895000"
    assert event.find("detail/contact").get("callsign") == "Spring & well"
    assert event.find("detail/remarks").text == "18S UJ 23478 06483 Water Source Fresh <cold> water"


def test_a_tak_data_package():
    data = tak.data_package([waypoint(), waypoint("w2", "Trailhead", 39.0, -77.5, "")])
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = set(z.namelist())
        assert {"MANIFEST/manifest.xml", "MIA_places.kml", "w1/w1.cot", "w2/w2.cot"} <= names
        manifest = ET.fromstring(z.read("MANIFEST/manifest.xml"))
        listed = {c.get("zipEntry") for c in manifest.iter("Content")}
        assert listed == names - {"MANIFEST/manifest.xml"}
        assert "18S UJ 23478 06483" in z.read("MIA_places.kml").decode()


def test_talking_in_grid_references():
    saved = []
    store = SimpleNamespace(add_waypoint=lambda **kw: saved.append(SimpleNamespace(**kw)) or saved[-1],
                            all_waypoints=lambda: saved)
    context = SimpleNamespace(waypoints=store)
    said = tak.reply(context, "add a waypoint called Spring at 18S UJ 23478 06483")
    assert said.startswith("Waypoint 'Spring' saved at 18S UJ 2347") and abs(saved[0].latitude - 38.8895) < 2e-5
    assert tak.reply(context, "what's the grid for spring?").startswith("Spring is at 18S UJ 2347")
    assert "isn't a grid reference" not in (tak.reply(context, "add waypoint Camp at 18S UJ 2347806483") or "")
    assert tak.reply(context, "what's for dinner") is None


def test_places_go_to_tak_apps_on_this_network_only_by_approval(monkeypatch):
    from core import actions
    from core.actions import ActionCenter

    sent = []
    monkeypatch.setattr(actions, "_who", lambda context: "p1")
    monkeypatch.setattr(tak, "send", lambda events: sent.extend((e, (tak.SA_GROUP, tak.SA_PORT)) for e in events) or len(events))
    context = SimpleNamespace(waypoints=SimpleNamespace(all_waypoints=lambda: [waypoint()]), config=None, undo=None,
                              events=None)
    center = ActionCenter()
    proposal = center.propose(context, "map.tak_share", {})
    assert "on TAK apps on this network" in proposal.summary and sent == []  # nothing goes until approved
    assert center.approve(context, proposal.proposal_id).result.startswith("Sent 1 place")
    assert sent[0][1] == ("239.2.3.1", 6969) and "MIA-w1" in sent[0][0]
    assert not actions.ACTION_TYPES["map.tak_share"].child_ok


def test_the_multicast_stays_on_this_network(monkeypatch):
    import socket

    calls = []

    class Socket:
        def __init__(self, *args):
            pass

        def setsockopt(self, level, option, value):
            calls.append(("ttl", value) if option == socket.IP_MULTICAST_TTL else ("other", value))

        def sendto(self, data, where):
            calls.append(("to", where))

        def close(self):
            calls.append(("closed", None))
    monkeypatch.setattr(socket, "socket", Socket)
    assert tak.send(["<event/>", "<event/>"]) == 2
    assert calls == [("ttl", 1), ("to", ("239.2.3.1", 6969)), ("to", ("239.2.3.1", 6969)), ("closed", None)]  # one hop
