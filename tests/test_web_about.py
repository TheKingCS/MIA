"""About MIA (DEC-0142, DEC-0057): the page reads every line from the facts, a missing source is a quiet gap, and
how her apps are doing is counted by status on the asking device."""

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


def test_her_apps_are_counted_by_status_with_what_isnt_simply_working_broken_first():
    from core.web_about import apps_health

    rows = [{"name": "Kitchen", "status": "implemented", "why": "built and working", "evidence": "verified"},
            {"name": "Greenhouse", "status": "partial", "why": "No sensors yet.", "evidence": "verified"},
            {"name": "Power", "status": "malfunctioning", "why": "it broke 2 times this week", "evidence": "inferred"},
            {"name": "Look on the glasses", "status": "planned", "why": "the glasses' camera", "evidence": "verified"}]
    health = apps_health(rows)
    assert [(c["word"], c["n"]) for c in health["counts"]] == [("Working", 1), ("Broke This Week", 1), ("Partly", 1),
                                                               ("Planned", 1)]
    assert [n["name"] for n in health["notes"]] == ["Power", "Greenhouse", "Look on the glasses"]
    assert health["notes"][0]["evidence"] == "inferred" and apps_health([]) == {"counts": [], "notes": []}


def test_the_page_carries_how_her_apps_are_doing_on_the_asking_device():
    from types import SimpleNamespace

    from core.web_about import screen

    page = screen(SimpleNamespace(), "phone")
    assert page["apps"]["counts"] and all(c["n"] for c in page["apps"]["counts"])
    assert screen(SimpleNamespace(), "toaster")["apps"] == screen(SimpleNamespace(), "pc")["apps"]
