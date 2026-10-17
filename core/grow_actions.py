"""
core.grow_actions
===================

The grow lab's actions (DEC-0030 phase D, core/grow_lab.py) on the action
contract: proposed in plain words, approved, run, undoable.

- `batch.add/edit/delete`; `batch.harvest`; `batch.lost`.
- `grow.reading`: a measurement into the Data Logger; the sentence says
  when it's outside the range (MIA only ever warns).
- `grow.range`: the person's own safe range for a measure in a system.
- `grow.system` / `grow.system_remove`: name a tank, bed or room.
- `experiment.add/edit/delete`; `experiment.include` (a batch into it);
  `experiment.conclude`.
"""

from __future__ import annotations

from core.actions import ACTION_TYPES, ActionError, ActionType, _need
from core.record_actions import Field, Record, record_kinds

BATCH = Record("batch", "batch", "batch_id", "get_batch", "add_batch", "update_batch", "delete_batch",
               store="grow_lab", fields=(
                   Field("crop", "What's planted", "text", True), Field("variety", "Variety", "text"),
                   Field("asset_id", "Where (a tank or bed: add it under Assets)", "pick", options=("places",), say="where"),
                   Field("method", "How (aquaponics, soil…)", "text", say="method"),
                   Field("planted", "Planted on", "date"), Field("count", "How many plants or seeds", "int", say="count"),
                   Field("cost", "What it cost (seeds, starts)", "money", say="cost"),
                   Field("notes", "Notes", "textarea")))
EXPERIMENT = Record("experiment", "experiment", "experiment_id", "get_experiment", "add_experiment", "update_experiment",
                    "delete_experiment", store="grow_lab", fields=(
                        Field("question", "The question (e.g. Which lettuce grows best in Tank A?)", "text", True,
                              say="question"),
                        Field("conclusion", "What you found", "textarea", say="conclusion")))


def _lab(context):
    return _need(context, "grow_lab")


def _num(params, name, label, required=True, allow_negative=False):
    raw = params.get(name)
    if raw in (None, ""):
        if required:
            raise ActionError(f"{label} is needed.")
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        raise ActionError(f"{label} has to be a number.") from None
    if value < 0 and not allow_negative:
        raise ActionError(f"{label} can't be negative.")
    return value


def _batch(context, params):
    b = _lab(context).get_batch(str(params.get("batch_id") or ""))
    if b is None:
        raise ActionError("That batch isn't there anymore.")
    return b


def _yes(value) -> bool:
    return str(value).lower() in ("1", "true", "yes", "on")


def _harvest_describe(context, params) -> str:
    b = _batch(context, params)
    amount = _num(params, "amount", "How much")
    if not amount:
        raise ActionError("How much was harvested?")
    unit = str(params.get("unit") or "").strip()
    return f"Harvest {amount:g} {unit + ' ' if unit else ''}of {b.crop}" + (" (the last of it)" if _yes(params.get("done")) else "")


def _harvest(context, params) -> str:
    b = _batch(context, params)
    _lab(context).harvest(b.batch_id, _num(params, "amount", "How much"), str(params.get("unit") or ""),
                          str(params.get("note") or ""), _yes(params.get("done")))
    return f"Harvest of {b.crop} recorded."


def _lost_describe(context, params) -> str:
    b = _batch(context, params)
    n = int(_num(params, "how_many", "How many", required=False) or 0)
    if not n and not _yes(params.get("all")):
        raise ActionError("How many were lost?")
    why = str(params.get("why") or "").strip()
    what = "all of it" if _yes(params.get("all")) else f"{n}"
    return f"Record {what} of {b.crop} lost" + (f": {why}" if why else "")


def _lost(context, params) -> str:
    b = _batch(context, params)
    n = int(_num(params, "how_many", "How many", required=False) or 0)
    if _yes(params.get("all")):
        n = max(n, b.count - b.lost)
    _lab(context).lose(b.batch_id, n, str(params.get("why") or ""), _yes(params.get("all")))
    return "Noted. Every loss is data for next time."


def _measure(params):
    from core.grow_lab import MEASURES

    measure = str(params.get("measure") or "")
    if measure not in MEASURES:
        raise ActionError("Pick what you measured.")
    return measure


def _system(context, params) -> str:
    """The place: a Greenhouse asset's id (`place` or `asset_id`), or a
    name typed for an older place (`system`)."""
    place = str(params.get("place") or params.get("asset_id") or "").strip()
    if place:
        if _lab(context).asset(place) is None and place.lower() not in (s.lower() for s in _lab(context).systems):
            raise ActionError("That tank or bed isn't there anymore.")
        return place
    system = " ".join(str(params.get("system") or "").split())
    if not system:
        raise ActionError("Which tank, bed or room?")
    return system


def _where(context, place: str) -> str:
    return _lab(context).place_name(place)


def _reading_describe(context, params) -> str:
    from core.grow_lab import MEASURES, check_range

    system, measure = _system(context, params), _measure(params)
    value = _num(params, "value", "The reading", allow_negative=True)
    label, unit = MEASURES[measure]
    low, high, _mine = _lab(context).range_for(system, measure)
    side = check_range(value, low, high)
    warn = f" (that's {side}: your range is {low if low is not None else '–'} to {high if high is not None else '–'})" if side else ""
    return f"{_where(context, system)}: {label} {value:g}{(' ' + unit) if unit else ''}{warn}"


def _reading(context, params) -> str:
    from core.grow_lab import MEASURES, series_id

    system, measure = _system(context, params), _measure(params)
    value = _num(params, "value", "The reading", allow_negative=True)
    if _lab(context).asset(system) is None:
        _lab(context).add_system(system)
    _need(context, "data_logger").add_reading(series_id(system, measure), value, MEASURES[measure][1],
                                              str(params.get("note") or ""))
    return f"{MEASURES[measure][0]} logged for {_where(context, system)}."


def _range_describe(context, params) -> str:
    from core.grow_lab import MEASURES

    system, measure = _system(context, params), _measure(params)
    low = _num(params, "low", "Low end", required=False, allow_negative=True)
    high = _num(params, "high", "High end", required=False, allow_negative=True)
    if low is None and high is None:
        raise ActionError("Set a low end, a high end, or both.")
    if low is not None and high is not None and low > high:
        raise ActionError("The low end has to be below the high end.")
    return f"{_where(context, system)}: keep {MEASURES[measure][0]} between {low if low is not None else 'anything'} and " \
        f"{high if high is not None else 'anything'}"


def _range(context, params) -> str:
    system, measure = _system(context, params), _measure(params)
    _lab(context).set_range(system, measure, _num(params, "low", "Low end", False, True),
                            _num(params, "high", "High end", False, True))
    return "Range saved. MIA will flag readings outside it."


def _experiment(context, params):
    e = _lab(context).get_experiment(str(params.get("experiment_id") or ""))
    if e is None:
        raise ActionError("That experiment isn't there anymore.")
    return e


def _include_describe(context, params) -> str:
    e, b = _experiment(context, params), _batch(context, params)
    return f"{'Take' if b.batch_id in e.batch_ids else 'Add'} {b.crop}{' (' + b.variety + ')' if b.variety else ''} " \
        f"{'out of' if b.batch_id in e.batch_ids else 'to'} the experiment"


def _include(context, params) -> str:
    e, b = _experiment(context, params), _batch(context, params)
    ids = [i for i in e.batch_ids if i != b.batch_id] if b.batch_id in e.batch_ids else e.batch_ids + [b.batch_id]
    _lab(context).update_experiment(e.experiment_id, batch_ids=ids)
    return "Experiment updated."


def _conclude_describe(context, params) -> str:
    e = _experiment(context, params)
    if not str(params.get("conclusion") or "").strip():
        raise ActionError("Write what you found.")
    return f"Conclude: {e.question}"


def _conclude(context, params) -> str:
    e = _experiment(context, params)
    _lab(context).update_experiment(e.experiment_id, conclusion=str(params["conclusion"]).strip(), status="Concluded")
    return "Concluded. That's knowledge for next season."


def _register() -> None:
    kinds = list(record_kinds(BATCH)) + list(record_kinds(EXPERIMENT)) + [
        ActionType("batch.harvest", "Harvest", {"batch_id": "the batch", "amount": "how much", "unit": "lb, heads…",
                                                "note": "notes", "done": "the last of it"}, _harvest_describe, _harvest),
        ActionType("batch.lost", "Lost Some", {"batch_id": "the batch", "how_many": "how many", "why": "why", "all": "all of it"},
                   _lost_describe, _lost),
        ActionType("grow.reading", "Log Reading", {"place": "the tank or bed", "measure": "what", "value": "the reading", "note": "notes"},
                   _reading_describe, _reading),
        ActionType("grow.range", "Set Range", {"place": "the tank or bed", "measure": "what", "low": "low end", "high": "high end"},
                   _range_describe, _range),
        ActionType("grow.system", "Add Place", {"system": "a tank, bed or room"},
                   lambda c, p: f"Add {_system(c, p)} to the grow lab", lambda c, p: f"{_lab(c).add_system(_system(c, p))} added."),
        ActionType("grow.system_remove", "Remove", {"system": "the place"},
                   lambda c, p: f"Remove {_system(c, p)} from the list (its readings stay)",
                   lambda c, p: (_lab(c).remove_system(_system(c, p)), "Removed.")[1]),
        ActionType("experiment.include", "Include", {"experiment_id": "the experiment", "batch_id": "the batch"},
                   _include_describe, _include),
        ActionType("experiment.conclude", "Conclude", {"experiment_id": "the experiment", "conclusion": "what you found"},
                   _conclude_describe, _conclude),
    ]
    from dataclasses import replace

    helping = {"batch.harvest", "batch.lost", "grow.reading"}  # a child can help in the garden (never money)
    for kind in kinds:
        ACTION_TYPES[kind.kind] = replace(kind, child_ok=True) if kind.kind in helping else kind


_register()
