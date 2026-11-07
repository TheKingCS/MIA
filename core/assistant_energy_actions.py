"""
core.assistant_energy_actions
===============================

Energy by voice (T-0053, from the weekly interconnection audit, DEC-0108):
"how's the solar doing?", "what did the generator read last?". The energy
store (core/energy_manager.py: solar, a generator, propane, tracked by hand)
had no Assistant tool, so nothing about it could be asked out loud.

`get_energy` reads every source (or the one named) with the latest reading on
each of its meters and when it was taken. `log_energy_reading` (2026-11-07,
DEC-0125: what the Power screen does, by voice too) logs one through the
screen's own action (`energy.reading`), on the meter named or the source's
latest, so "undo that" takes it back.
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


def _number(raw):
    """Pure logic. A reading as a number ("62", "62%", "3.8 kWh"), or None."""
    import re

    found = re.search(r"-?\d+(?:\.\d+)?", str(raw if raw is not None else ""))
    return float(found.group()) if found else None


def _action_log_energy_reading(context, arguments: dict) -> str:
    """Tool log_energy_reading: logs a reading on the named source (its meter named, else its latest one, else
    "Level") through energy.reading; undoable."""
    from core.actions import ActionError

    store, actions = getattr(context, "energy", None), getattr(context, "actions", None)
    if store is None or actions is None:
        return "Energy tracking isn't on this MIA."
    named = " ".join(str(arguments.get("source") or "").lower().split())
    found = [s for s in store.all_energy_sources() if named and (named in s.name.lower() or named in s.source_type.lower())]
    if len(found) != 1:
        names = ", ".join(s.name for s in (found or store.all_energy_sources()))
        return f"Which source? {names}." if names else "No energy sources yet: add one under Apps → Power."
    value = _number(arguments.get("value"))
    if value is None:
        return f"What does {found[0].name} read?"
    source = found[0]
    meters = store.energy_source_meter_names(source.source_id)
    meter = str(arguments.get("meter") or "").strip() or (meters[-1] if meters else "Level")
    unit = str(arguments.get("unit") or "").strip()
    if not unit and "%" in str(arguments.get("value")) or unit.lower() in ("percent", "pct"):
        unit = "%"
    try:
        done = actions.approve(context, actions.propose(context, "energy.reading", {
            "source_id": source.source_id, "meter_name": meter, "value": value, "unit": unit}, proposed_by="mia").proposal_id)
    except ActionError as problem:
        return str(problem)
    if done.status != "executed":
        return done.result or "That didn't work; nothing was logged."
    return f"{done.result} (Say “undo that” to take it back.)"


def register_energy_actions(registry: AssistantActionRegistry) -> None:
    """Registers the get_energy and log_energy_reading tools."""
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
    registry.register(AssistantAction(
        name="log_energy_reading", domain="power",
        description="Log a reading the user took on an energy source: the propane level, the solar output, the "
                    "generator's fuel or hours.",
        parameters={"type": "object", "properties": {
            "source": {"type": "string", "description": "Which source: propane, solar, generator, or its name."},
            "value": {"type": "string", "description": "The reading, e.g. 60 or 60% or 3.8."},
            "unit": {"type": "string", "description": "%, kWh, gal, hours, only if they said one."},
            "meter": {"type": "string", "description": "Which meter, only if they named one."}}, "required": ["source", "value"]},
        handler=_action_log_energy_reading,
        trigger_phrases=("log the propane", "propane is at", "propane's at", "log the solar", "log the generator",
                         "generator is at", "solar made", "log a reading", "tank is at"),
        subjects=("solar", "generator", "propane"),
    ))
