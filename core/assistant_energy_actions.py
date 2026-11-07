"""
core.assistant_energy_actions
===============================

Energy by voice (T-0053, from the weekly interconnection audit, DEC-0108):
"how's the solar doing?", "what did the generator read last?". The energy
store (core/energy_manager.py: solar, a generator, propane, tracked by hand)
had no Assistant tool, so nothing about it could be asked out loud.

`get_energy` reads every source (or the one named) with the latest reading on
each of its meters and when it was taken. Read only: readings are still
logged on the Power screen.
"""

from __future__ import annotations

from core.assistant_actions import AssistantAction, AssistantActionRegistry


def _latest(store, source) -> list[str]:
    """Each meter's latest reading for a source, said plainly ("output 4.2 kWh on 2026-11-06")."""
    out = []
    for meter in store.energy_source_meter_names(source.source_id):
        readings = sorted(store.energy_source_readings(source.source_id, meter), key=lambda r: r.timestamp)
        if readings:
            last = readings[-1]
            out.append(f"{meter} {last.value:g}{(' ' + last.unit) if last.unit else ''} on {last.timestamp[:10]}")
    return out


def _action_get_energy(context, arguments: dict) -> str:
    """Tool get_energy: each energy source (or the one named) with its latest reading on every meter."""
    store = getattr(context, "energy", None)
    if store is None:
        return "Energy tracking isn't on this MIA."
    sources = store.all_energy_sources()
    if not sources:
        return "No energy sources yet: add one under Apps → Power (solar, a generator, propane...)."
    named = str(arguments.get("source") or "").strip().lower()
    if named:
        sources = [s for s in sources if named in s.name.lower() or named in s.source_type.lower()] or sources
    said = []
    for s in sources:
        latest = _latest(store, s)
        said.append(f"{s.name} ({s.source_type}): " + ("; ".join(latest) if latest else "no readings yet") + ".")
    return " ".join(said)


def register_energy_actions(registry: AssistantActionRegistry) -> None:
    """Registers the get_energy tool."""
    registry.register(AssistantAction(
        name="get_energy", domain="power",
        description=("The energy sources tracked by hand (solar, a generator, propane, a utility meter) and each "
                     "one's latest readings."),
        parameters={"type": "object", "properties": {
            "source": {"type": "string", "description": "Which source, only if they named one."}}, "required": []},
        handler=_action_get_energy,
        trigger_phrases=("how's the solar", "how is the solar", "solar doing", "generator reading", "propane level",
                         "energy readings", "my energy", "solar output", "how much power did", "the generator read"),
        subjects=("solar", "generator", "propane", "energy"),
    ))
