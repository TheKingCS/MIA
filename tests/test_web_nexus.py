"""
tests.test_web_nexus
======================

The Nexus (DEC-0130; Living Worlds only since DEC-0153, core/web_nexus.py): what needs you counted in each area and
its destination, going to a destination, subdashboard, the Dashboard or the Nexus by voice, the screen's portals (each
story, in play first, then "Make a World") with the HUD; a portal's picture only once it exists (H-0096); the Nexus
and an area's room share one 3D engine.
"""

from types import SimpleNamespace

import core.web_surfaces as surfaces
from core.web_nexus import nexus, portal_status, wants_area


def test_what_needs_you_counts_in_the_owning_area_and_its_destination():
    items = [{"when": "overdue", "module_id": "garage"}, {"when": "today", "module_id": "kitchen"},
             {"when": "soon", "module_id": "garage"}, {"when": "today", "module_id": "budget"}]
    assert portal_status(items) == {"garage": 1, "kitchen": 1, "home": 1, "finances": 1}


def test_going_to_a_destination_or_subdashboard_by_its_name_or_an_everyday_name():
    assert wants_area("Take me to the garage") == ("hub.html?area=garage", "Garage")
    assert wants_area("open the homestead") == ("hub.html?area=homestead", "Homestead")
    assert wants_area("open plants and animals") == ("hub.html?area=homestead", "Homestead")
    assert wants_area("go to my money") == ("hub.html?area=finances", "Finances")
    assert wants_area("open AI tools") == ("hub.html?area=ai_tools", "AI Tools")
    assert wants_area("show me personal tools") == ("hub.html?area=personal_tools", "Personal Tools")
    assert wants_area("open health & fitness") == ("hub.html?area=health", "Health and Fitness")
    assert wants_area("go to the dashboard") == ("index.html", "the Dashboard")
    assert wants_area("Hey MIA, take me to the Nexus.") == ("nexus.html", "the Nexus")
    assert wants_area("open living worlds") == ("nexus.html", "the Nexus")
    assert wants_area("open the garage door") is None
    assert wants_area("what's in the garage?") is None


def test_the_screen_has_a_portal_per_story_in_play_first_then_make_a_world(tmp_path):
    from core.living_worlds import LivingWorldsBook

    page = nexus(SimpleNamespace())
    assert [p["id"] for p in page["portals"]] == ["new_world"] and page["day"].startswith("No story in play")
    book = LivingWorldsBook(None, data_dir=tmp_path)
    coast = book.create_universe("Dragon Coast", "fantasy")
    old = book.create_campaign(coast.universe_id, "The Long Winter")
    old.status = "ended"
    road = book.create_campaign(coast.universe_id, "The Ember Road", "Smugglers on the coast road.")
    page = nexus(SimpleNamespace(living_worlds=book))
    assert [p["name"] for p in page["portals"]] == ["The Ember Road", "The Long Winter", "Make a World"]
    first = page["portals"][0]
    assert first["page"] == f"worlds.html?campaign={road.campaign_id}" and first["line"].startswith("Dragon Coast · ")
    assert first["hue"] == page["portals"][1]["hue"]  # one world, one colour
    assert {"level", "missions"} <= set(page["hud"]) and page["day"] == "1 story in play"


def test_a_portal_carries_its_picture_only_once_muses_art_is_there(monkeypatch, tmp_path):
    """The room (web/nexus3d.js) asks only for pictures that exist (H-0096); the rest draw a placeholder."""
    import core.web_nexus as web_nexus

    monkeypatch.setattr(web_nexus, "PORTAL_ART", tmp_path)
    (tmp_path / "garage.jpg").write_bytes(b"jpg")
    assert web_nexus.portal_art("garage") == "img/portals/garage.jpg"
    assert web_nexus.portal_art("home") == ""


def test_the_nexus_and_an_areas_room_load_the_same_3d_engine():
    """The Nexus and the Garage's room are drawn by one engine (web/nexus3d.js), with the flat versions kept for
    reduced motion and machines without WebGL 2."""
    from pathlib import Path

    web = Path(__file__).resolve().parent.parent / "web"
    for page in ("nexus.html", "hub.html"):
        html = (web / page).read_text(encoding="utf-8")
        assert html.index('src="spatial.js"') < html.index('src="nexus3d.js"'), page
    engine = (web / "nexus3d.js").read_text(encoding="utf-8")
    assert "window.MIARoom = window.MIANexus3D" in engine and "prefers-reduced-motion" in engine
