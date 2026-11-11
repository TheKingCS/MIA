"""
Portal Pictures (core/portal_pictures.py, DEC-0140; the Nexus's portals are the person's stories since DEC-0153): the
person puts one of their own paintings in a story's portal in the Nexus, or has MIA paint one for it, and can put it
back to the original; each person's Nexus is their own. Uses the stand-in ComfyUI from tests/test_art_studio.py.
"""

import pytest

from core import art_studio, portal_pictures
from core.actions import ACTION_TYPES, ActionError
from tests.test_art_studio import PNG, comfy  # noqa: F401  (the fixtures)
from tests.test_art_studio import ctx as art_ctx  # noqa: F401


@pytest.fixture
def ctx(art_ctx, tmp_path):
    """The art context with two stories in Living Worlds: The Ember Road (Dragon Coast) and Quiet Harbour."""
    from core.living_worlds import LivingWorldsBook

    book = LivingWorldsBook(art_ctx, data_dir=tmp_path / "worlds")
    coast = book.create_universe("Dragon Coast", "fantasy")
    book.create_campaign(coast.universe_id, "The Ember Road")
    book.create_campaign(book.create_universe("Lighthouse", "mystery").universe_id, "Quiet Harbour")
    art_ctx.living_worlds = book
    return art_ctx


def _id(ctx, name):
    """A story's portal id by its name."""
    return next(c.campaign_id for c in ctx.living_worlds.campaigns if c.name == name)


def _painted(ctx, comfy, words, use="portal", area=""):
    """Paints on this thread and settles it; returns the new picture's id."""
    art_studio.start(ctx, words, use, apply=bool(area), engine=comfy, wait=True, area=area)
    return art_studio.settle(ctx)[0]["art_id"]


def test_a_portal_shows_the_original_until_the_person_picks_their_own(ctx, comfy):
    from core.web_nexus import portal_art

    road = _id(ctx, "The Ember Road")
    assert portal_pictures.picture(ctx, road) == portal_art(road)
    art_id = _painted(ctx, comfy, "a lantern-lit workshop in the pines")
    action = ACTION_TYPES["portal.picture"]
    assert action.describe(ctx, {"area": road, "art": art_id}).startswith("Show the painting of a lantern-lit workshop")
    assert "The Ember Road portal shows your painting" in action.execute(ctx, {"area": road, "art": art_id})
    assert portal_pictures.picture(ctx, road) == f"/api/art/{art_id}/image"
    assert portal_pictures.chosen(ctx) == {road: art_id}
    assert "back to its original" in action.execute(ctx, {"area": road, "art": ""})
    assert portal_pictures.picture(ctx, road) == portal_art(road)
    with pytest.raises(ActionError, match="already shows its original"):
        action.describe(ctx, {"area": road, "art": ""})
    with pytest.raises(ActionError, match="no portal"):
        action.describe(ctx, {"area": "garage", "art": art_id})  # an area isn't a portal any more
    with pytest.raises(ActionError, match="isn't one of yours"):
        action.describe(ctx, {"area": road, "art": "nope"})


def test_a_painting_asked_for_a_portal_goes_in_it_when_done(ctx, comfy):
    harbour = _id(ctx, "Quiet Harbour")
    art_id = _painted(ctx, comfy, "a misty glasshouse at dawn", area=harbour)
    assert portal_pictures.chosen(ctx) == {harbour: art_id}
    from core.themes import for_shell

    assert "backdrop" not in for_shell(ctx)  # a portal picture never becomes the background


def test_a_deleted_painting_leaves_the_portal_on_its_original(ctx, comfy):
    from core.art_studio import _delete

    harbour = _id(ctx, "Quiet Harbour")
    art_id = _painted(ctx, comfy, "a quiet harbour", area=harbour)
    _delete(ctx, {"id": art_id})
    assert portal_pictures.chosen(ctx) == {} and not portal_pictures.picture(ctx, harbour).startswith("/api/")


def test_the_page_lists_each_portal_with_where_its_picture_came_from(ctx, comfy):
    road = _id(ctx, "The Ember Road")
    art_id = _painted(ctx, comfy, "a lantern-lit workshop", area=road)
    page = portal_pictures.screen(ctx)
    by_id = {a["id"]: a for a in page["areas"]}
    assert set(by_id) == {road, _id(ctx, "Quiet Harbour"), "new_world"}
    assert by_id[road]["source"] == "yours" and by_id[road]["art_id"] == art_id
    assert all(a["source"] in ("original", "none") for a in page["areas"] if a["id"] != road)
    assert page["paintings"][0]["id"] == art_id and page["engine"]["available"] in (True, False)


def test_by_voice_she_paints_for_a_portal_and_puts_paintings_in_them(ctx, comfy, monkeypatch):
    import time

    from core.assistant_art_actions import _action_paint, _action_portal_picture

    monkeypatch.setattr(art_studio, "engine_for", lambda context: comfy)
    assert "go in that portal" in _action_paint(ctx, {"description": "a candle-lit library", "portal": "the Dragon Coast portal"})
    for _ in range(200):
        if art_studio.settle(ctx):
            break
        time.sleep(0.02)
    art_id = ctx.art.all()[0]["id"]
    assert portal_pictures.chosen(ctx) == {_id(ctx, "The Ember Road"): art_id}
    assert "shows your painting" in _action_portal_picture(ctx, {"portal": "quiet harbour", "picture": "library"})
    assert "back to its original" in _action_portal_picture(ctx, {"portal": "Quiet Harbour", "picture": "original"})
    assert "Which portal" in _action_portal_picture(ctx, {"portal": "the moon", "picture": "library"})
    assert "Want me to paint one" in _action_portal_picture(ctx, {"portal": "the ember road", "picture": "a submarine"})
