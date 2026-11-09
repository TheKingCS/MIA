"""
The glasses cards for the apps that only had an ask (core/glasses_cards.py, 2026-11-08): every one builds a panel
without a store and in a real household, shows the page assembler's facts in at most five short lines, flags what
needs the person in amber and only what's broken in red, and lets the glasses change nothing but an open promise.
"""

import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

from core import glasses, glasses_cards as gc

TODAY = date(2026, 11, 8)
SCHEMA = Path(__file__).resolve().parent.parent / "docs" / "schema"


def _example(name):
    """A screen's demo data (docs/schema/<name>.example.json): the page assembler's real shape."""
    return json.loads((SCHEMA / f"{name}.example.json").read_text(encoding="utf-8"))


def _builders():
    """Every new card's (app, item, builder)."""
    return [(app, item, build) for app, items in gc.PANELS.items() for item, _label, build in items]


@pytest.mark.parametrize("app,item,build", _builders())
def test_every_card_builds_a_short_panel_with_nothing_set_up(app, item, build):
    panel = build(SimpleNamespace(config=None), TODAY)
    assert set(panel) >= {"title", "lines", "more", "empty"} and len(panel["lines"]) <= glasses.MAX_LINES
    assert panel["lines"] or panel["empty"]


def test_every_card_builds_in_a_real_household(tmp_path, monkeypatch):
    from tests.engine_world import build_world

    world = build_world(tmp_path, monkeypatch)
    for app, item, build in _builders():
        panel = build(world, TODAY)
        assert len(panel["lines"]) <= glasses.MAX_LINES, (app, item)
        for line in panel["lines"]:
            assert line["tone"] in ("", "attention", "bad") and (
                "action" not in line or line["action"]["kind"] in glasses.GLASSES_KINDS), (app, item)


def test_every_app_but_passwords_and_sight_has_a_card_on_the_glasses():
    from core.web_surfaces import APPS

    missing = {a.module_id for a in APPS} - set(glasses.PANELS) - glasses.NOT_ON_GLASSES
    assert missing == {"passwords", "sight"}  # no secrets on the glasses; Look waits on the glasses' camera


def test_deadlines_need_you_in_amber_and_say_when_and_who(monkeypatch):
    import core.web_compliance as wc

    monkeypatch.setattr(wc, "compliance_page", lambda context, today=None: _example("compliance"))
    panel = gc._compliance_due(SimpleNamespace(), TODAY)
    first = panel["lines"][0]
    assert first["text"].startswith("Federal income tax return") and "58 days late" in first["detail"]
    assert {line["tone"] for line in panel["lines"]} == {"attention"}


def test_a_camera_with_a_problem_is_red_and_a_working_one_says_so(monkeypatch):
    import core.security_cams as sc

    page = _example("security")
    page["cameras"] = [dict(page["cameras"][0]), dict(page["cameras"][0], name="Barn", problem="It didn't answer.")]
    monkeypatch.setattr(sc, "security_page", lambda context: page)
    lines = gc._security_cameras(SimpleNamespace(), TODAY)["lines"]
    assert lines[0]["detail"].endswith("working") and lines[0]["tone"] == ""
    assert lines[1] == {"text": "Barn", "detail": "It didn't answer.", "tone": "bad"}


def test_only_an_open_promise_can_be_marked_done_from_the_glasses(monkeypatch):
    import core.life_notes as ln

    page = {"kinds": [{"kind": "commitment", "title": "Promises", "notes": [
        {"id": "n1", "line": "a promise to Sam: fix his gate", "status": "open", "at": "2026-11-06", "due": "2026-11-07"},
        {"id": "n2", "line": "a promise: call her", "status": "done", "at": "2026-10-30", "due": ""}]},
        {"kind": "idea", "title": "Ideas", "notes": [{"id": "n4", "line": "an idea: honey", "status": "open", "at": "2026-11-01", "due": ""}]}]}
    monkeypatch.setattr(ln, "screen", lambda context: page)
    [promise] = gc.PANELS["life_notes"][0][2](SimpleNamespace(), TODAY)["lines"]
    assert promise["tone"] == "attention" and promise["action"] == {"kind": "life_note.done", "label": "Done",
                                                                     "params": {"note_id": "n1"}}
    [idea] = gc.PANELS["life_notes"][1][2](SimpleNamespace(), TODAY)["lines"]
    assert "action" not in idea


def test_the_flock_rewards_and_orders_read_the_page_figures(monkeypatch):
    import core.game_layer as gl
    import core.web_business as wb
    import core.web_flock as wf

    monkeypatch.setattr(wf, "flock_page", lambda context, today=None: _example("flock"))
    monkeypatch.setattr(gl, "shop_page", lambda context: _example("shop"))
    monkeypatch.setattr(wb, "business_page", lambda context, today=None: _example("business"))
    eggs = gc._flock_today(SimpleNamespace(), TODAY)["lines"]
    assert eggs[0]["text"] == "7 eggs today" and "65 this week" in eggs[0]["detail"]
    shop = gc._shop_rewards(SimpleNamespace(), TODAY)["lines"]
    assert shop[0]["text"] == "850 credits" and any(line["detail"].endswith("ready") for line in shop[1:])
    orders = gc._business_orders(SimpleNamespace(), TODAY)["lines"]
    assert orders and all("action" not in line for line in orders)  # money stays a readout on the glasses


def test_the_menu_puts_the_new_cards_before_the_asks():
    from core.web_surfaces import APPS

    flock = next(a for a in APPS if a.module_id == "flock")
    menu = glasses.menu_for(flock)
    assert menu[0] == {"id": "eggs", "label": "Eggs", "type": "panel"} and menu[1]["type"] == "ask"


def test_a_card_face_shows_its_first_line_and_needs_you_when_a_line_does(monkeypatch):
    import core.web_compliance as wc

    monkeypatch.setattr(wc, "compliance_page", lambda context, today=None: _example("compliance"))
    face = gc.status(SimpleNamespace(), "compliance", TODAY)
    assert face == {"line": "Federal income tax return (Form 1040)", "tone": "attention"}
    assert gc.status(SimpleNamespace(), "diagnostics", TODAY) == {}  # an expensive read shows no face line
    assert gc.status(SimpleNamespace(config=None), "flock", TODAY) == {}  # nothing to show, no line
