"""
core.world_intel_actions
=========================

World Intelligence's actions (DEC-0170, core/world_intel.py) on the action contract: proposed in plain words,
approved, run, undoable (every one writes world_intel.json or the person's settings through the atomic write).

- `world_intel.switch`: World Intelligence on or off for this person (DEC-0053: switching it on is the asking).
- `world_watch.add`: a watch in the person's own words, with its areas, how often and a price ceiling.
- `world_watch.pause` / `world_watch.remove`: pause, resume or remove one.
- `world_find.save`: keep a find (it stays past 90 days); engaging, for the gate's pace (DEC-0171).
- `world_find.not_for_me`: "not for me"; passing, for the gate's pace.
- `world_source.mute`: no watch reads a source (mute: yes), or it's read again (mute: no).
"""

from __future__ import annotations

from core.actions import ACTION_TYPES, ActionError, ActionType, _need
from core.world_intel import TOPIC, is_on, phrases


def _book(context):
    """The person's World Intelligence store, or ActionError."""
    return _need(context, "world_intel")


def _yes(value) -> bool:
    """A yes from a form or a tool: yes, true, on, 1."""
    return str(value or "").strip().lower() in ("yes", "true", "on", "1")


def _list(raw) -> list[str]:
    """A list from a list or a comma-separated string."""
    items = raw if isinstance(raw, (list, tuple)) else str(raw or "").split(",")
    return [str(x).strip() for x in items if str(x).strip()]


# ------------------------------------------------------------------ on and off


def _switch_describe(context, params) -> str:
    """The approval sentence for `world_intel.switch`."""
    if _yes(params.get("on")):
        return ("Turn on World Intelligence: MIA reads the sources your watches name, a few times a day, sending only "
                "your watches' words")
    return "Turn off World Intelligence (watches stop; finds stay)"


def _switch_execute(context, params) -> str:
    """Does `world_intel.switch`."""
    from core import person_settings

    on = _yes(params.get("on"))
    person_settings.put(context, "world.on", on)
    return "World Intelligence is on." if on else "World Intelligence is off. Your watches and finds are kept."


# ------------------------------------------------------------------ watches


def _areas(params) -> list[str]:
    """The areas named, checked against the catalog's."""
    from core.world_sources import AREAS

    areas = _list(params.get("areas"))
    bad = [a for a in areas if a not in AREAS]
    if bad:
        raise ActionError(f"I don't know the area {', '.join(bad)}. The areas: {', '.join(AREAS)}.")
    return areas


def _hours(params) -> int:
    """How many hours between runs (default 6, at least 1)."""
    try:
        return max(1, int(float(params.get("every_hours") or 6)))
    except (TypeError, ValueError):
        raise ActionError("How many hours between looks?") from None


def _price(params) -> float:
    """The price ceiling (0: none)."""
    try:
        return max(0.0, float(str(params.get("max_price") or 0).replace("$", "").replace(",", "")))
    except ValueError:
        raise ActionError("What's the most it should cost?") from None


def _add_describe(context, params) -> str:
    """The approval sentence for `world_watch.add`."""
    from core.region import money
    from core.world_sources import AREA_NAMES

    words = " ".join(str(params.get("words") or "").split())
    if not phrases(words):
        raise ActionError("What should I watch for?")
    areas = _areas(params)
    where = ", ".join(AREA_NAMES[a].lower() for a in areas) if areas else "every source"
    extra = []
    if _yes(params.get("search")):
        extra.append("and your search engine")
    if _price(params):
        extra.append(f"up to {money(_price(params), ',.0f')}")
    return f"Watch for “{words}” in {where}" + (" " + ", ".join(extra) if extra else "") + \
        f", every {_hours(params)} hours"


def _add_execute(context, params) -> str:
    """Does `world_watch.add`."""
    words = " ".join(str(params.get("words") or "").split())
    try:
        watch = _book(context).add_watch(params.get("name") or words, words, _areas(params), _list(params.get("sources")),
                                         _yes(params.get("search")), _hours(params), _price(params))
    except ValueError as problem:
        raise ActionError(str(problem)) from None
    tail = "" if is_on(context) else " World Intelligence is off: turn it on and I'll start looking."
    return f"Watching for “{watch.words}”.{tail}"


def _watch(context, params):
    """The watch the params name (watch_id, or `watch` in words); ActionError when none or several."""
    book = _book(context)
    found = book.get_watch(str(params.get("watch_id") or "")) or book.find_watch(params.get("watch") or "")
    if found is None:
        raise ActionError("Which watch? Say its name.")
    return found


def _pause_describe(context, params) -> str:
    """The approval sentence for `world_watch.pause`."""
    w = _watch(context, params)
    return ("Resume" if not _yes(params.get("paused", "yes")) else "Pause") + f" the watch “{w.name}”"


def _pause_execute(context, params) -> str:
    """Does `world_watch.pause` (paused: yes pauses, no resumes)."""
    w = _watch(context, params)
    paused = _yes(params.get("paused", "yes"))
    _book(context).set_paused(w.watch_id, paused)
    return f"Paused “{w.name}”." if paused else f"“{w.name}” is watching again."


def _remove_execute(context, params) -> str:
    """Does `world_watch.remove`."""
    w = _watch(context, params)
    _book(context).remove_watch(w.watch_id)
    return f"Stopped watching for “{w.name}”. What it found stays until it's old."


# ------------------------------------------------------------------ finds


def _find(context, params):
    """The find named by discovery_id, or ActionError."""
    found = _book(context).get(str(params.get("discovery_id") or ""))
    if found is None:
        raise ActionError("That find isn't here any more.")
    return found


def _engaged(context, how: str) -> None:
    """Tells the gate what the person did with a find (DEC-0171): saving engages; "not for me" passes."""
    gate = getattr(context, "communication", None)
    if gate is not None:
        gate.note_engagement(topic=TOPIC, how=how)


def _save_execute(context, params) -> str:
    """Does `world_find.save`: keeps the find and counts as engaging with World Intelligence's messages."""
    f = _find(context, params)
    _book(context).set_status(f.discovery_id, "saved")
    _engaged(context, "acted")
    return f"Saved “{f.title}” (from {f.source_name})."


def _not_for_me_execute(context, params) -> str:
    """Does `world_find.not_for_me`: sets it aside (it won't be offered again) and tells the gate it was passed over,
    which eases how often finds are sent."""
    f = _find(context, params)
    _book(context).set_status(f.discovery_id, "not_for_me")
    _engaged(context, "passed")  # seen and judged not for them: that kind's pace eases (never a break by itself)
    return f"Set aside “{f.title}”."


def _source(params):
    """The source the params name (source_id, or `source` by its name); ActionError when none or several."""
    from core import world_sources

    wanted = str(params.get("source_id") or "")
    found = world_sources.source(wanted) if wanted else None
    if found is None:
        words = " ".join(str(params.get("source") or "").lower().split())
        some = [s for s in world_sources.CATALOG if words and words in s.name.lower()]
        found = some[0] if len(some) == 1 else None
    if found is None:
        raise ActionError("Which source? Say its name as the World page shows it.")
    return found


def _mute_execute(context, params) -> str:
    """Does `world_source.mute`."""
    src = _source(params)
    mute = _yes(params.get("mute", "yes"))
    _book(context).set_muted(src.source_id, mute)
    return f"I won't read {src.name} for your watches." if mute else f"I'll read {src.name} again."


def _register() -> None:
    """Adds World Intelligence's kinds to ACTION_TYPES (switch, watches, finds, muting a source). Runs once, when this
    module is imported."""
    kinds = [
        ActionType("world_intel.switch", "World Intelligence", {"on": "yes to turn on, no to turn off"},
                   _switch_describe, _switch_execute),
        ActionType("world_watch.add", "Watch For", {"words": "what to look for (phrases, by commas)",
                                                    "name": "a name (optional)", "areas": "areas (optional)",
                                                    "search": "yes: also search the web", "every_hours": "hours",
                                                    "max_price": "most it should cost (optional)"},
                   _add_describe, _add_execute),
        ActionType("world_watch.pause", "Pause", {"watch_id": "the watch", "watch": "or its name",
                                                  "paused": "yes pauses, no resumes"},
                   _pause_describe, _pause_execute),
        ActionType("world_watch.remove", "Stop Watching", {"watch_id": "the watch", "watch": "or its name"},
                   lambda c, p: f"Stop watching for “{_watch(c, p).name}”", _remove_execute),
        ActionType("world_find.save", "Save", {"discovery_id": "the find"},
                   lambda c, p: f"Save “{_find(c, p).title}”", _save_execute),
        ActionType("world_find.not_for_me", "Not for Me", {"discovery_id": "the find"},
                   lambda c, p: f"Set aside “{_find(c, p).title}”", _not_for_me_execute),
        ActionType("world_source.mute", "Mute", {"source_id": "the source", "source": "or its name",
                                                 "mute": "yes mutes, no reads it again"},
                   lambda c, p: ("Stop reading " if _yes(p.get("mute", "yes")) else "Read again: ") + _source(p).name,
                   _mute_execute),
    ]
    for k in kinds:
        ACTION_TYPES[k.kind] = k


_register()
