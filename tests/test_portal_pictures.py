"""
Portal Pictures (core/portal_pictures.py, DEC-0140 / DEC-0130): the person puts one of their own paintings in an area's
portal in the Nexus, or has MIA paint one for it, and can put it back to the original; each person's Nexus is their
own. Uses the stand-in ComfyUI from tests/test_art_studio.py.
"""

import pytest

from core import art_studio, portal_pictures
from core.actions import ACTION_TYPES, ActionError
from tests.test_art_studio import PNG, comfy, ctx  # noqa: F401  (the fixtures)


def _painted(ctx, comfy, words, use="portal", area=""):
    """Paints on this thread and settles it; returns the new picture's id."""
    art_studio.start(ctx, words, use, apply=bool(area), engine=comfy, wait=True, area=area)
    return art_studio.settle(ctx)[0]["art_id"]


def test_a_portal_shows_the_original_until_the_person_picks_their_own(ctx, comfy):
    from core.web_nexus import portal_art

    assert portal_pictures.picture(ctx, "garage") == portal_art("garage")
    art_id = _painted(ctx, comfy, "a lantern-lit workshop in the pines")
    action = ACTION_TYPES["portal.picture"]
    assert action.describe(ctx, {"area": "garage", "art": art_id}).startswith("Show the painting of a lantern-lit workshop")
    assert "shows your painting" in action.execute(ctx, {"area": "garage", "art": art_id})
    assert portal_pictures.picture(ctx, "garage") == f"/api/art/{art_id}/image"
    assert portal_pictures.chosen(ctx) == {"garage": art_id}
    assert "back to its original" in action.execute(ctx, {"area": "garage", "art": ""})
    assert portal_pictures.picture(ctx, "garage") == portal_art("garage")
    with pytest.raises(ActionError, match="already shows its original"):
        action.describe(ctx, {"area": "garage", "art": ""})
    with pytest.raises(ActionError, match="no area"):
        action.describe(ctx, {"area": "attic", "art": art_id})
    with pytest.raises(ActionError, match="isn't one of yours"):
        action.describe(ctx, {"area": "garage", "art": "nope"})


def test_a_painting_asked_for_a_portal_goes_in_it_when_done(ctx, comfy):
    art_id = _painted(ctx, comfy, "a misty glasshouse at dawn", area="plants_animals")
    assert portal_pictures.chosen(ctx) == {"plants_animals": art_id}
    from core.themes import for_shell

    assert "backdrop" not in for_shell(ctx)  # a portal picture never becomes the background


def test_a_deleted_painting_leaves_the_portal_on_its_original(ctx, comfy):
    from core.art_studio import _delete

    art_id = _painted(ctx, comfy, "a quiet harbour", area="recreation")
    _delete(ctx, {"id": art_id})
    assert portal_pictures.chosen(ctx) == {} and not portal_pictures.picture(ctx, "recreation").startswith("/api/")


def test_the_page_lists_each_area_with_where_its_picture_came_from(ctx, comfy):
    art_id = _painted(ctx, comfy, "a lantern-lit workshop", area="garage")
    page = portal_pictures.screen(ctx)
    by_id = {a["id"]: a for a in page["areas"]}
    assert by_id["garage"]["source"] == "yours" and by_id["garage"]["art_id"] == art_id
    assert all(a["source"] in ("original", "none") for a in page["areas"] if a["id"] != "garage")
    assert page["paintings"][0]["id"] == art_id and page["engine"]["available"] in (True, False)


def test_by_voice_she_paints_for_a_portal_and_puts_paintings_in_them(ctx, comfy, monkeypatch):
    import time

    from core.assistant_art_actions import _action_paint, _action_portal_picture

    monkeypatch.setattr(art_studio, "engine_for", lambda context: comfy)
    assert "go in that portal" in _action_paint(ctx, {"description": "a candle-lit library", "portal": "the learning portal"})
    for _ in range(200):
        if art_studio.settle(ctx):
            break
        time.sleep(0.02)
    art_id = ctx.art.all()[0]["id"]
    assert portal_pictures.chosen(ctx) == {"learning": art_id}
    assert "shows your painting" in _action_portal_picture(ctx, {"portal": "kitchen", "picture": "library"})
    assert "back to its original" in _action_portal_picture(ctx, {"portal": "Kitchen", "picture": "original"})
    assert "Which area" in _action_portal_picture(ctx, {"portal": "the moon", "picture": "library"})
    assert "Want me to paint one" in _action_portal_picture(ctx, {"portal": "garage", "picture": "a submarine"})
