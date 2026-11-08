"""About MIA (DEC-0142): the page reads every line from the facts, and a missing source is a quiet gap."""

from types import SimpleNamespace

import core.web_about as wa


def test_the_scale_tiles_come_only_from_numbers_the_map_has():
    tiles = wa.numbers({"architecture": {"core": 10, "gui": 5}, "capabilities": {"tools": 0}, "decisions": [1, 2]})
    assert [(t["label"], t["value"]) for t in tiles] == [("Files of code", 15), ("Decisions on record", 2)]
    assert wa.numbers({}) == []


def test_the_page_has_her_line_her_specialties_and_an_honest_line_about_a_stranger():
    page = wa.screen(SimpleNamespace())
    assert page["about"].startswith("I'm MIA") and page["numbers"] and page["specialties"]
    assert all(s["title"] and s["line"] for s in page["specialties"])
    assert "getting to know you" in page["you"]["line"] and page["you"]["directions"] == []


def test_a_source_that_breaks_leaves_a_gap_not_an_error(monkeypatch):
    from core import system_map

    monkeypatch.setattr(system_map, "assemble", lambda: (_ for _ in ()).throw(RuntimeError("no repo")))
    page = wa.screen(SimpleNamespace())
    assert page["numbers"] == [] and page["about"] == ""
