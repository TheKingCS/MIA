"""
tests.test_web_areas
======================

MIA's eight destinations and their subdashboards (DEC-0153, core/web_areas.py; the area hues from DEC-0130): the
eight in Zac's order, every app and page with exactly one owner, every web page owned or listed as part of the
frame, old area ids still opening, a hub listing its subdashboards, what the person can open and the way back, and no
area's hue a status color.
"""

from pathlib import Path
from types import SimpleNamespace

import core.web_surfaces as surfaces
from core.web_areas import (AREAS, AREAS_BY_ID, OLD_IDS, Page, areas_of, children, destinations, hub, member_id, resolve,
                            sidebar, top_of)

WEB = Path(__file__).resolve().parent.parent / "web"
# Pages no area owns, on purpose: the frame's own screens, detail pages opened from their app, redirects, and the
# glasses' and phone's views.
NOT_OWNED = {"index.html", "hub.html", "nexus.html", "glasses.html", "presence.html", "start.html", "asset.html",
             "recipe.html", "grow.html", "dev-window.html", "finances.html", "worlds.html", "dashboard.html",
             "maintenance.html", "property.html", "diagnostics.html", "settings.html"}


def test_the_eight_destinations_in_zacs_order():
    assert [a.name for a in destinations()] == ["Dashboard", "Home", "Garage", "Finances", "Health and Fitness",
                                                "AI Tools", "Missions", "Settings"]
    assert [a.id for a in children("home")] == ["kitchen", "smart_devices", "homestead", "recreation", "personal_tools",
                                                "learning"]
    assert [a.id for a in children("finances")] == ["businesses"]
    assert all(AREAS_BY_ID[a.parent].parent == "" for a in AREAS if a.parent)  # one level of subdashboards


def test_every_app_and_page_has_exactly_one_owner():
    owners: dict[str, list[str]] = {}
    for area in AREAS:
        for m in area.members:
            owners.setdefault(member_id(m), []).append(area.id)
    assert {k: v for k, v in owners.items() if len(v) > 1} == {}
    # Property and Maintenance are redirects now (to Real Estate and Garage): Home Upkeep stands in for them.
    missing = {app.module_id for app in surfaces.APPS if app.page} - set(owners) - {"web_home", "dashboard",
                                                                                     "maintenance", "property"}
    assert missing == set()


def test_every_web_page_is_owned_or_part_of_the_frame():
    owned = {m.page.split("?")[0].split("#")[0] for a in AREAS for m in a.members if isinstance(m, Page)}
    owned |= {app.page for app in surfaces.APPS if app.page}
    unowned = {p.name for p in WEB.glob("*.html")} - owned - NOT_OWNED
    assert unowned == set()


def test_the_apps_zac_placed_are_where_he_put_them():
    assert areas_of("security") == ["smart_devices"]  # the cameras
    assert areas_of("passwords") == ["security"] and top_of("security") == "settings"
    assert areas_of("real_estate") == ["businesses"] and areas_of("business") == ["businesses"]
    assert areas_of("memories") == ["personal_tools"] and areas_of("skills") == ["missions"]
    assert areas_of("inbox") == ["ai_tools"] and areas_of("sight") == ["ai_tools"] and areas_of("dungeon") == ["missions"]
    assert areas_of("good_news") == ["dashboard"] and areas_of("kitchen") == ["kitchen"]
    assert areas_of("worlds") == ["recreation"]


def test_living_worlds_opens_the_nexus_and_nothing_else_does():
    pages = {m.id: m.page for a in AREAS for m in a.members if isinstance(m, Page)}
    assert pages["worlds"] == "nexus.html"
    assert [k for k, v in pages.items() if v == "nexus.html"] == ["worlds"]


def test_every_member_and_shortcut_is_a_known_app_or_a_page_that_exists():
    page_ids = {m.id for a in AREAS for m in a.members if isinstance(m, Page)}
    for area in AREAS:
        for m in area.members:
            if isinstance(m, Page):
                assert (WEB / m.page.split("?")[0].split("#")[0]).is_file(), m.page
            else:
                assert m in surfaces.APPS_BY_ID, m
        for s in area.shortcuts:
            assert s in surfaces.APPS_BY_ID or s in page_ids, s
            assert s not in [member_id(m) for m in area.members], f"{area.id} owns {s}: not a shortcut"


def test_old_area_ids_open_what_took_their_place():
    for old, new in OLD_IDS.items():
        assert old not in AREAS_BY_ID and resolve(old).id == new
    assert hub(SimpleNamespace(), "plants_animals")["id"] == "homestead"
    assert resolve("nowhere") is None and top_of("kitchen") == "home"


def test_a_hub_shows_its_subdashboards_first_and_only_what_the_person_can_open(monkeypatch):
    monkeypatch.setattr(surfaces, "_visible", lambda context, app: app.module_id != "freedom")
    found = hub(SimpleNamespace(), "finances")
    names = [a["name"] for a in found["apps"]]
    assert names[:2] == ["Businesses", "Money"] and "Freedom" not in names
    assert [s["id"] for s in found["shortcuts"]] == ["dungeon"] and found["back"]["page"] == "index.html"
    assert hub(SimpleNamespace(), "kitchen")["back"] == {"name": "Home", "page": "hub.html?area=home"}
    assert hub(SimpleNamespace(), "nowhere") is None
    side = sidebar(SimpleNamespace())
    assert [a["id"] for a in side][:3] == ["dashboard", "home", "garage"] and side[0]["page"] == "index.html"
    assert [s["id"] for s in side[1]["subs"]][:2] == ["kitchen", "smart_devices"]


def test_no_area_hue_is_a_status_color():
    """DEC-0130 with Muse's H-0093: amber means needs you, red error, green ok, gold reward; no area wears any of them
    (no hue in green's band at all: homestead stays cyan), and Muse's set values hold."""
    import colorsys

    for a in AREAS:
        r, g, b = (int(a.hue[i:i + 2], 16) / 255 for i in (1, 3, 5))
        h, l, sat = colorsys.rgb_to_hls(r, g, b)
        deg = h * 360
        if sat > 0.25 and l < 0.85:
            assert not (80 <= deg <= 170), f"{a.id} is green ({a.hue})"
            assert not (35 <= deg <= 55 and l < 0.75), f"{a.id} is amber or gold ({a.hue})"
            assert not (deg <= 12 or deg >= 350), f"{a.id} is red ({a.hue})"
    hue = {a.id: a.hue for a in AREAS}
    assert hue["homestead"] == "#35d4ff" and hue["kitchen"] == "#e9d4a8" and hue["health"] == "#ff8a3d"
