"""
tests.test_bench_builds
=========================

His builds on My Bench (core/bench_builds.py): saved by name (the same name on the same board a new version), kept
sealed through atomic writes, listed newest first and by voice; Mark It Built says each Component DB count it changes
and the parts he has no record of, then takes them; deleting one.
"""

from types import SimpleNamespace

import pytest

from core import bench_builds
from core.actions import ACTION_TYPES, ActionError

PARTS = [{"id": "pir", "spec": "hcsr501"}, {"id": "led", "spec": "led"}, {"id": "r1", "spec": "resistor"},
         {"id": "r2", "spec": "resistor"}]
WIRES = [["pir.vcc", "VIN"], ["pir.gnd", "GND"]]


class _Parts:
    """A stand-in Component DB: an HC-SR501 (2) and resistors (30)."""

    def __init__(self):
        """Its parts."""
        self.items = [SimpleNamespace(component_id="c1", name="HC-SR501 PIR", category="Sensor", quantity=2),
                      SimpleNamespace(component_id="c2", name="Resistor 220", category="Resistor", quantity=30)]

    def all_components(self):
        """Every part."""
        return self.items

    def adjust_quantity(self, component_id, delta):
        """A count up or down, never below 0."""
        item = next(i for i in self.items if i.component_id == component_id)
        item.quantity = max(0, item.quantity + delta)
        return item


def _context(tmp_path):
    """A context with a build book on tmp_path and the stand-in Component DB."""
    return SimpleNamespace(bench_builds=bench_builds.BuildBook(data_dir=tmp_path), components=_Parts())


def test_a_build_is_saved_by_name_and_the_same_name_is_a_new_version(tmp_path):
    """Saved: kept on disk; saved again by the same name on the same board: replaced, not doubled; nothing on the
    board or no name: refused."""
    context = _context(tmp_path)
    save = ACTION_TYPES["benchbuild.save"]
    said = save.describe(context, {"name": "Shed light", "parts": PARTS, "wires": WIRES})
    assert said == 'Save "Shed light": 4 parts and 2 wires'
    save.execute(context, {"name": "Shed light", "board": "nano", "parts": PARTS, "wires": WIRES, "sketch": "x"})
    save.execute(context, {"name": "shed light", "board": "nano", "parts": PARTS[:2], "wires": WIRES})
    kept = bench_builds.BuildBook(data_dir=tmp_path).all()
    assert len(kept) == 1 and len(kept[0]["parts"]) == 2
    with pytest.raises(ActionError):
        save.describe(context, {"name": "Empty", "parts": [], "wires": []})
    assert bench_builds._list_tool(context, {}) == "Your bench builds: shed light (nano, 2 parts)."


def test_marking_it_built_says_each_count_then_takes_the_parts(tmp_path):
    """The card: the HC-SR501 2 to 1, the resistors 30 to 28, the LED not in his Component DB; done: the counts down
    and the build marked built; deleted: gone."""
    context = _context(tmp_path)
    build = context.bench_builds.save("Shed light", "nano", PARTS, WIRES)
    said = ACTION_TYPES["benchbuild.built"].describe(context, {"build_id": build["id"]})
    assert "HC-SR501 PIR: 2 to 1" in said and "Resistor 220: 30 to 28" in said and "Not in your Component DB: LED" in said
    ACTION_TYPES["benchbuild.built"].execute(context, {"build_id": build["id"]})
    assert [i.quantity for i in context.components.items] == [1, 28] and context.bench_builds.get(build["id"])["built"]
    ACTION_TYPES["benchbuild.remove"].execute(context, {"build_id": build["id"]})
    assert context.bench_builds.all() == []
    with pytest.raises(ActionError):
        ACTION_TYPES["benchbuild.built"].describe(context, {"build_id": build["id"]})
