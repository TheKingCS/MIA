"""
tests/test_web_trades.py — Trade Master on the web (core/web_trades.py, DEC-0149): the library groups every job and
diagnosis by trade, a job or diagnosis opens in full, and the walkthrough shows the step in focus with its hold, the
phases, and what a stopped or finished session says.
"""

from datetime import datetime
from types import SimpleNamespace

from core import trade_session as js, trades, web_trades


def _ctx(session=None):
    """A context with a job store holding `session` (or none going)."""
    return SimpleNamespace(trade_session=SimpleNamespace(live=lambda: session))


def test_library_groups_every_job_and_diagnosis_by_trade():
    trades._loaded()
    groups = web_trades.library()
    ids = {it["id"] for g in groups for it in g["items"]}
    assert set(trades.JOBS) | set(trades.DIAGNOSES) == ids
    assert all(g["items"] for g in groups)
    assert all(it["status_word"] for g in groups for it in g["items"])


def test_a_job_opens_with_its_phases_holds_and_rules():
    o = web_trades.opened("chicken_coop")
    assert o["kind"] != "diagnosis" and o["phases"] and o["steps"] >= 12
    assert any(s["hold"] for p in o["phases"] for s in p["steps"])
    assert len(o["sources"]) >= 2


def test_a_diagnosis_opens_with_its_first_check():
    o = web_trades.opened("toilet_running")
    assert o["kind"] == "diagnosis" and o["first"] and o["checks"] >= 2


def test_an_unknown_item_opens_to_nothing():
    assert web_trades.opened("no_such_job") is None


def test_the_walkthrough_shows_the_step_its_hold_and_phases():
    s = js.start(trades.JOBS["chicken_coop"], datetime(2026, 11, 9, 9))
    w = web_trades.walkthrough(_ctx(s))
    assert w["status"] == "working" and w["step_text"] and w["why"]
    assert w["progress"]["step"] == 1
    assert [p["state"] for p in w["phases"]][0] == "now"
    hold_at = next(i for i, (_p, _j, st) in enumerate(trades.JOBS["chicken_coop"].steps()) if st.hold)
    s.at = hold_at
    w = web_trades.walkthrough(_ctx(s))
    assert w["hold"] and not w["checked"]
    js.confirm(s)
    assert web_trades.walkthrough(_ctx(s))["checked"]


def test_a_diagnosis_walkthrough_asks_its_check():
    s = js.start(trades.DIAGNOSES["toilet_running"], datetime(2026, 11, 9, 9))
    w = web_trades.walkthrough(_ctx(s))
    assert w["kind"] == "diagnosis" and w["ask"] and w["step_text"] == w["ask"]


def test_a_stopped_session_says_what_to_do_instead():
    s = js.start(trades.JOBS["chicken_coop"], datetime(2026, 11, 9, 9))
    rule = next(iter(trades.STOP_RULES.values()))
    js.stop(s, rule)
    w = web_trades.walkthrough(_ctx(s))
    assert w["status"] == "stopped" and w["stopped"] == rule.instead and w["phases"] == []


def test_the_screen_opens_the_job_being_worked_when_none_is_picked():
    s = js.start(trades.JOBS["workshop"], datetime(2026, 11, 9, 9))
    d = web_trades.screen(_ctx(s))
    assert d["available"] and d["opened"]["id"] == "workshop" and d["live"]["item_id"] == "workshop"


def test_without_a_job_store_the_screen_says_it_isnt_there():
    d = web_trades.screen(SimpleNamespace(), "")
    assert d["available"] is False and d["live"] is None and d["opened"] is None
