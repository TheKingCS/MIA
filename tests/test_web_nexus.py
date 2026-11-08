"""
tests.test_web_nexus
======================

The Nexus (DEC-0130, core/web_nexus.py): what needs you in each portal, going to an area by voice, and the screen's
data in sidebar order with each area's hue; a portal's picture only once it exists (H-0096).
"""

from types import SimpleNamespace

import core.web_surfaces as surfaces
from core.web_nexus import nexus, portal_status, wants_area


def test_what_needs_you_counts_in_every_area_its_app_is_in():
    items = [{"when": "overdue", "module_id": "garage"}, {"when": "today", "module_id": "kitchen"},
             {"when": "soon", "module_id": "garage"}, {"when": "today", "module_id": "budget"}]
    assert portal_status(items) == {"garage": 1, "kitchen": 1, "home": 1, "health": 1, "finances": 1}


def test_going_to_an_area_by_its_name_or_an_everyday_name():
    assert wants_area("Take me to the garage") == ("hub.html?area=garage", "Garage")
    assert wants_area("open plants and animals") == ("hub.html?area=plants_animals", "Plants and Animals")
    assert wants_area("go to my money") == ("hub.html?area=finances", "Finances")
    assert wants_area("Hey MIA, take me to the Nexus.") == ("nexus.html", "the Nexus")
    assert wants_area("open the garage door") is None
    assert wants_area("what's in the garage?") is None


def test_the_screen_has_portals_in_order_with_hues_and_the_hud(monkeypatch):
    monkeypatch.setattr(surfaces, "_visible", lambda context, app: True)
    page = nexus(SimpleNamespace())
    assert page["portals"][0]["id"] == "home" and page["portals"][1]["hue"] == "#8fa7bf"
    assert {"level", "missions"} <= set(page["hud"]) and page["day"] == "Nothing needs you today"


def test_a_portal_carries_its_picture_only_once_muses_art_is_there(monkeypatch, tmp_path):
    """The room (web/nexus3d.js) asks only for pictures that exist (H-0096); the rest draw a placeholder."""
    import core.web_nexus as web_nexus

    monkeypatch.setattr(web_nexus, "PORTAL_ART", tmp_path)
    (tmp_path / "garage.jpg").write_bytes(b"jpg")
    assert web_nexus.portal_art("garage") == "img/portals/garage.jpg"
    assert web_nexus.portal_art("home") == ""
