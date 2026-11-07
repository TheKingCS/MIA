"""
tests.test_assistant_energy_actions
=====================================

Energy by voice (core/assistant_energy_actions.py, T-0053): each source with
its latest reading per meter, one named source, and the empty cases.
"""

from __future__ import annotations

from types import SimpleNamespace

from core.assistant_energy_actions import _action_get_energy


def _reading(value, unit, when):
    """A stand-in data-logger reading."""
    return SimpleNamespace(value=value, unit=unit, timestamp=when)


def _store():
    """Two sources: solar with an output meter read twice, a generator never read."""
    solar = SimpleNamespace(source_id="s1", name="Roof Solar", source_type="Solar")
    gen = SimpleNamespace(source_id="g1", name="Backup", source_type="Generator")
    readings = {("s1", "output"): [_reading(4.2, "kWh", "2026-11-06T18:00"), _reading(3.1, "kWh", "2026-11-05T18:00")]}
    return SimpleNamespace(
        all_energy_sources=lambda: [solar, gen],
        energy_source_meter_names=lambda sid: [m for s, m in readings if s == sid],
        energy_source_readings=lambda sid, m: readings[(sid, m)])


def test_each_source_says_its_latest_reading():
    """The newest reading per meter is said with its unit and day; a source with none says so; one named narrows
    it; no store or no sources says what to do."""
    context = SimpleNamespace(energy=_store())
    said = _action_get_energy(context, {})
    assert said == "Roof Solar (Solar): output 4.2 kWh on 2026-11-06. Backup (Generator): no readings yet."
    assert _action_get_energy(context, {"source": "generator"}) == "Backup (Generator): no readings yet."
    assert _action_get_energy(SimpleNamespace(), {}) == "Energy tracking isn't on this MIA."
    empty = SimpleNamespace(energy=SimpleNamespace(all_energy_sources=lambda: []))
    assert _action_get_energy(empty, {}).startswith("No energy sources yet")
