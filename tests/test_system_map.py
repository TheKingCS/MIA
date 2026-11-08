"""
tests.test_system_map
=======================

The one map of everything that makes MIA (core/system_map.py, DEC-0139): it assembles every category from the real
sources (decisions, loops, knowledge, learnings, stores, preferences, architecture, capabilities), renders a navigable
page, and a broken source becomes a noted gap rather than a crash.
"""

from core import system_map


def test_the_map_assembles_every_category_with_sane_counts():
    data = system_map.assemble()
    assert set(data) == {"architecture", "decisions", "capabilities", "loops", "knowledge", "learnings",
                         "stores", "preferences"}
    assert len(data["decisions"]) > 100  # the decisions log
    assert data["loops"]["active"] > 0 and data["capabilities"]["tools"] > 0
    assert data["stores"]["personal"] > 0 and data["stores"]["sealed"] > 0
    assert len(data["preferences"]["style_dimensions"]) == 4  # DEC-0138's four dimensions


def test_the_map_renders_a_navigable_page():
    page = system_map.render()
    for heading in ("# MIA", "## At a glance", "## Decisions", "## How she improves",
                    "## What she keeps", "## How you shape her"):
        assert heading in page
    assert "DEC-0138" in page  # a real decision id surfaces


def test_a_broken_source_is_a_gap_not_a_crash(monkeypatch):
    monkeypatch.setattr(system_map, "decisions", lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    data = system_map.assemble()
    assert data["decisions"] == []  # the gap, defaulted
    assert system_map.render(data)  # still renders
