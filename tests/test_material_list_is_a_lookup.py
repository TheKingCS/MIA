"""
tests.test_material_list_is_a_lookup
======================================

A materials question is a lookup (core/main_thread.call_changes, core/tool_loop._wants_change; live check,
2026-11-25: "what do I need to build garage shelves 8 feet wide?" reached for material_list, was taken for a change,
and the model answered with quantities of its own): material_list and cut_list change records only with keep set
true, whatever a small model sends for it; and the shelving list says how far apart its supports are.
"""

from types import SimpleNamespace

from core import build_calcs
from core.main_thread import call_changes
from core.tool_loop import _wants_change


def test_a_materials_list_changes_nothing_unless_it_is_kept():
    for keep in (None, "false", "0", False, "no"):
        assert not call_changes("material_list", {"structure": "shelving", "keep": keep}), keep
    assert call_changes("material_list", {"structure": "shed", "keep": "true"})
    assert not call_changes("cut_list", {"parts": "2 legs at 30 in 2x4"})
    assert call_changes("add_grocery_item", {"name": "milk"})
    reply = SimpleNamespace(tool_calls=[SimpleNamespace(name="material_list", arguments={"keep": "false"})])
    assert not _wants_change(None, reply)


def test_the_shelving_list_says_how_far_apart_its_supports_are():
    text = build_calcs.shelving(8).to_text()
    assert "a cross piece every 24 in" in text and "16 in apart" in text
