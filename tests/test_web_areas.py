"""
tests.test_web_areas
======================

MIA's areas and hubs (DEC-0129, core/web_areas.py): every app has an area, shared apps sit in each of their hubs,
every page an area links to exists, and a hub lists only what the person can open.
"""

from pathlib import Path
from types import SimpleNamespace

import core.web_surfaces as surfaces
from core.web_areas import AREAS, AREAS_BY_ID, Page, areas_of, hub, sidebar

WEB = Path(__file__).resolve().parent.parent / "web"


def test_every_web_app_is_in_an_area_except_the_dashboard():
    placed = {m for a in AREAS for m in a.members if isinstance(m, str)}
    missing = {app.module_id for app in surfaces.APPS if app.page} - placed - {"web_home", "dashboard", "maintenance"}
    assert missing == set()


def test_the_apps_zac_named_sit_in_both_their_hubs():
    assert areas_of("skills") == ["learning", "missions"]
    assert areas_of("real_estate") == ["finances", "business"]
    assert areas_of("compliance") == ["finances", "business"]
    assert areas_of("workshop") == ["business", "projects"]
    assert "garage" in areas_of("toolbox") and "garage" in areas_of("sight")
    assert "personal" in areas_of("files") and "recreation" in areas_of("music")
    assert areas_of("kitchen") == ["home", "health"]


def test_every_member_is_a_known_app_or_a_page_that_exists():
    for area in AREAS:
        for m in area.members:
            if isinstance(m, Page):
                assert (WEB / m.page.split("?")[0]).is_file(), m.page
            else:
                assert m in surfaces.APPS_BY_ID, m


def test_a_hub_lists_only_what_the_person_can_open(monkeypatch):
    monkeypatch.setattr(surfaces, "_visible", lambda context, app: app.module_id != "dungeon")
    found = hub(SimpleNamespace(), "finances")
    names = [a["name"] for a in found["apps"]]
    assert names[0] == "Money" and "The Dungeon" not in names
    assert hub(SimpleNamespace(), "nowhere") is None
    assert [a["id"] for a in sidebar(SimpleNamespace())][:3] == ["home", "garage", "plants_animals"]


def test_fifteen_areas_in_zacs_order():
    assert [a.name for a in AREAS] == ["Home", "Garage", "Plants and Animals", "Health and Fitness", "Recreation",
                                       "Security", "Browser", "Settings and Diagnostics", "Finances", "Business",
                                       "Personal", "Learning", "Missions", "Projects", "Communications"]
    assert AREAS_BY_ID["communications"].members[0].page == "communications.html"
