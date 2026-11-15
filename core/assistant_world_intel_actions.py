"""
core.assistant_world_intel_actions
====================================

World Intelligence by voice (DEC-0170, DEC-0125: everything the World page does, said):
- "What have you found?" (`world_finds`): the best new finds, each with its source.
- "Watch for greenhouse panels" (`watch_for`): proposes `world_watch.add` in the person's own words.
- "What are you watching for?" (`list_watches`).
- "Stop watching for greenhouse panels" (`stop_watching`), "pause the panels watch" (`pause_watch`).
- "Save that find" / "not for me" (`save_find`, `not_for_me`): the newest find offered, or one named.
- "Turn on world intelligence" (`world_intelligence_switch`).

Each change goes through the same action the page's button uses (core/world_intel_actions.py), so the checks and the undo
are the same either way.
"""

from __future__ import annotations

from core.assistant_actions import AssistantAction, AssistantActionRegistry
from core.assistant_goods_actions import _run


def _finds(context, arguments: dict) -> str:
    """Tool world_finds: the best new finds, each named with its source, from the World page."""
    from core.web_world_intel import found_sentence, world_page

    return found_sentence(world_page(context))


def _watch_for(context, arguments: dict) -> str:
    """Tool watch_for: proposes `world_watch.add` with the person's words (and areas, a ceiling, search)."""
    return _run(context, "world_watch.add", {"words": arguments.get("words") or "", "name": arguments.get("name") or "",
                                             "areas": arguments.get("areas") or "",
                                             "search": arguments.get("search") or "",
                                             "every_hours": arguments.get("every_hours") or "",
                                             "max_price": arguments.get("max_price") or ""})


def _list_watches(context, arguments: dict) -> str:
    """Tool list_watches: every watch with what it's found and when it last looked."""
    from core.web_world_intel import world_page

    page = world_page(context)
    if not page.get("available"):
        return "World Intelligence isn't on this MIA."
    if not page["watches"]:
        return "I'm not watching for anything yet."
    said = "; ".join(f"{w['name']} ({'paused' if w['paused'] else str(w['found']) + ' found'}, last looked "
                     f"{w['last_run']})" for w in page["watches"])
    off = "" if page["on"] else " World Intelligence is off, so none of them are running."
    return f"Watching for: {said}.{off}"


def _stop(context, arguments: dict) -> str:
    """Tool stop_watching: proposes `world_watch.remove` for the watch named."""
    return _run(context, "world_watch.remove", {"watch": arguments.get("watch") or ""})


def _pause(context, arguments: dict) -> str:
    """Tool pause_watch: proposes `world_watch.pause` (or resume, with resume: yes) for the watch named."""
    resume = str(arguments.get("resume") or "").lower() in ("yes", "true", "1")
    return _run(context, "world_watch.pause", {"watch": arguments.get("watch") or "", "paused": "no" if resume else "yes"})


def _latest(context, arguments: dict) -> str:
    """The find meant: one named by id, else the newest offered new find, else the newest new one ("")."""
    book = getattr(context, "world_intel", None)
    if book is None:
        return ""
    wanted = str(arguments.get("discovery_id") or "")
    if wanted and book.get(wanted):
        return wanted
    new = [d for d in book.discoveries if d.status == "new"]
    offered = sorted((d for d in new if d.offered_at), key=lambda d: d.offered_at)
    pick = offered[-1] if offered else (sorted(new, key=lambda d: d.found_at)[-1] if new else None)
    return pick.discovery_id if pick else ""


def _save(context, arguments: dict) -> str:
    """Tool save_find: proposes `world_find.save` for the find meant."""
    found = _latest(context, arguments)
    return _run(context, "world_find.save", {"discovery_id": found}) if found else "There's no find to save."


def _not_for_me(context, arguments: dict) -> str:
    """Tool not_for_me: proposes `world_find.not_for_me` for the find meant."""
    found = _latest(context, arguments)
    return _run(context, "world_find.not_for_me", {"discovery_id": found}) if found else "There's no find to set aside."


def _switch(context, arguments: dict) -> str:
    """Tool world_intelligence_switch: proposes `world_intel.switch` on or off."""
    on = str(arguments.get("on") or "yes").lower() not in ("no", "off", "false", "0")
    return _run(context, "world_intel.switch", {"on": "yes" if on else "no"})


def register_world_intel_actions(registry: AssistantActionRegistry) -> None:
    """Registers World Intelligence's tools: world_finds, watch_for, list_watches, stop_watching, pause_watch,
    save_find, not_for_me and world_intelligence_switch."""
    none = {"type": "object", "properties": {}, "required": []}
    watch_named = {"type": "object", "properties": {"watch": {"type": "string", "description": "the watch's name"}},
                   "required": ["watch"]}
    registry.register(AssistantAction(
        name="world_finds", domain="world_intel", description="What World Intelligence has found lately, with sources.",
        parameters=none, handler=_finds,
        trigger_phrases=("what have you found", "anything new from my watches", "what did you find",
                         "world intelligence", "any finds"),
        subjects=("find", "watch", "world"),
    ))
    registry.register(AssistantAction(
        name="watch_for", domain="world_intel",
        description="Start watching news, releases, research and listings for something, in the person's own words.",
        parameters={"type": "object", "properties": {
            "words": {"type": "string", "description": "what to look for, exactly as the person said it; phrases by commas"},
            "name": {"type": "string", "description": "a short name (optional)"},
            "areas": {"type": "string", "description": "optional: self, ai, tech, smart_home, homestead, energy, grants, money, science, news, listings"},
            "search": {"type": "string", "description": "yes to also search the web for it"},
            "every_hours": {"type": "string", "description": "how often, in hours (optional)"},
            "max_price": {"type": "string", "description": "the most it should cost (optional)"}},
            "required": ["words"]},
        handler=_watch_for,
        trigger_phrases=("watch for", "keep an eye out for", "keep an eye on", "let me know if you see",
                         "watch the news for", "look out for"),
        subjects=("watch",),
    ))
    registry.register(AssistantAction(
        name="list_watches", domain="world_intel", description="What World Intelligence is watching for.",
        parameters=none, handler=_list_watches,
        trigger_phrases=("what are you watching for", "my watches", "what are you keeping an eye on"),
        subjects=("watch",),
    ))
    registry.register(AssistantAction(
        name="stop_watching", domain="world_intel", description="Stop one of World Intelligence's watches.",
        parameters=watch_named, handler=_stop,
        trigger_phrases=("stop watching for", "stop watching", "stop keeping an eye on"),
        subjects=("watch",),
    ))
    registry.register(AssistantAction(
        name="pause_watch", domain="world_intel", description="Pause one of World Intelligence's watches, or resume it.",
        parameters={"type": "object", "properties": {
            "watch": {"type": "string", "description": "the watch's name"},
            "resume": {"type": "string", "description": "yes to resume it instead"}}, "required": ["watch"]},
        handler=_pause,
        trigger_phrases=("pause the watch", "pause watching", "resume the watch", "resume watching"),
        subjects=("watch",),
    ))
    registry.register(AssistantAction(
        name="save_find", domain="world_intel", description="Keep a find World Intelligence brought up.",
        parameters={"type": "object", "properties": {"discovery_id": {"type": "string", "description": "optional"}},
                    "required": []},
        handler=_save,
        trigger_phrases=("save that find", "keep that find", "save that one", "save the find"),
        subjects=("find",),
    ))
    registry.register(AssistantAction(
        name="not_for_me", domain="world_intel", description="Set aside a find World Intelligence brought up.",
        parameters={"type": "object", "properties": {"discovery_id": {"type": "string", "description": "optional"}},
                    "required": []},
        handler=_not_for_me,
        trigger_phrases=("not for me", "not interested in that find", "skip that find"),
        subjects=("find",),
    ))
    registry.register(AssistantAction(
        name="world_intelligence_switch", domain="world_intel", description="Turn World Intelligence on or off.",
        parameters={"type": "object", "properties": {"on": {"type": "string", "description": "yes or no"}},
                    "required": []},
        handler=_switch,
        trigger_phrases=("turn on world intelligence", "turn off world intelligence", "start watching the world",
                         "stop world intelligence"),
        subjects=("world",),
    ))
