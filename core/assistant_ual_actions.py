"""
core.assistant_ual_actions
============================

The Universal Action Layer by voice (DEC-0165, core/ual.py): "what can you
do with this: ..." answers with the same offer the palette and the phone
show for the same words. "Save this to my inbox: ..." or "make this a
mission: ..." go through the same catalogue. By voice, saying it is the
yes, as for every voice tool: the action is checked and run by the action
contract, and "undo that" takes it back.

The shelf (UI-4, core/shelf.py): "keep this on my shelf: ..." is the catalogue's Keep On My Shelf; "what's on my
shelf" lists it, numbered; "summarise 1 and 3 from my shelf" runs a catalogue action on those entries as one
selection (core.shelf.combined); "take 2 off my shelf" or "clear my shelf" takes things off.

"Let selections search the web" (or "stop ...") is the same switch as the
Settings screen's: Research This and Verify These Claims are offered only
while it's on.

What the person dictates is captured like any selection: it is information,
never instructions (the catalogue decides what can be done with it).
"""

from __future__ import annotations

from core.assistant_actions import AssistantAction, AssistantActionRegistry


def _capture(arguments: dict):
    """The words the person gave, as a capture from voice."""
    from core.ual import Capture

    return Capture.from_dict({"text": arguments.get("text") or "", "source_app": "voice", "device": "voice"})


def _offer(context, arguments: dict) -> str:
    """Tool actions_for_this: what MIA can do with the words given, right away and with a yes (core/ual.offer)."""
    from core import ual

    try:
        return ual.offer_sentence(ual.offer(context, _capture(arguments)))
    except ual.UalError as problem:
        return str(problem)


def _do(context, arguments: dict) -> str:
    """Tool do_with_this: runs a catalogue action on the words given. A read or prepare action answers (and when it
    offers a way to keep the result, says to press it on the screen); an act action is checked and run as the
    screen's approval would (core.actions.run_as_tool), so it can be undone."""
    from core import ual
    from core.actions import run_as_tool

    spec = ual.BY_ID.get(str(arguments.get("action") or ""))
    try:
        capture = _capture(arguments)
        if spec is None or not ual.may_offer(context, spec, capture):
            return "I can't do that with it. " + ual.offer_sentence(ual.offer(context, capture))
        if spec.tier == ual.ACT:
            return run_as_tool(context, spec.kind, spec.params(capture))
        result = ual.run(context, spec.id, capture)["result"]
        said = str(result.get("text") or "Done.")
        follow = result.get("follow")
        return said + (f" To keep it, press {follow['label']} on the screen (Ctrl+K, or the phone's MIA card)."
                       if follow else "")
    except ual.UalError as problem:
        return str(problem)


def _online(context, arguments: dict) -> str:
    """Tool selections_search_web: turns the person's switch for Research and Verify on or off (`setting.set`,
    the same as the Settings screen's toggle)."""
    from core import ual
    from core.actions import run_as_tool

    return run_as_tool(context, "setting.set", {"key": ual.ONLINE_KEY, "value": bool(arguments.get("on"))})


def _shelf(context, arguments: dict) -> str:
    """Tool whats_on_my_shelf: what's on the person's shelf, numbered (core/shelf.said)."""
    from core.shelf import said

    return said(context)


def _use_shelf(context, arguments: dict) -> str:
    """Tool use_my_shelf: runs a catalogue action on the shelf entries named (numbers as listed, or all) as one
    selection. Read and prepare actions answer; an act action is checked and run as the screen's approval would."""
    from core import ual
    from core.actions import run_as_tool
    from core.shelf import ShelfError, combined, shelf_of

    spec = ual.BY_ID.get(str(arguments.get("action") or ""))
    try:
        capture = combined(shelf_of(context).find(arguments.get("which") or "all"))
    except ShelfError as problem:
        return str(problem)
    if spec is None or spec.id == "keep_shelf" or not ual.may_offer(context, spec, capture):
        return "I can't do that with those. " + ual.offer_sentence(ual.offer(context, capture))
    try:
        if spec.tier == ual.ACT:
            return run_as_tool(context, spec.kind, spec.params(capture))
        return str(ual.run(context, spec.id, capture)["result"].get("text") or "Done.")
    except ual.UalError as problem:
        return str(problem)


def _take_off(context, arguments: dict) -> str:
    """Tool take_off_my_shelf: takes the named entries off (numbers as listed), or everything for "all", through the
    action contract so "undo that" puts them back."""
    from core.actions import run_as_tool
    from core.shelf import ShelfError, shelf_of

    which = arguments.get("which") or ""
    if str(which).strip().lower() in ("all", "everything"):
        return run_as_tool(context, "shelf.clear", {})
    try:
        found = shelf_of(context).find(which)
    except ShelfError as problem:
        return str(problem)
    if not found:
        return "Say which: a number from your shelf, or all."
    return " ".join(run_as_tool(context, "shelf.remove", {"entry_id": e.entry_id}) for e in found)


def register_ual_actions(registry: AssistantActionRegistry) -> None:
    """Registers the Universal Action Layer's tools: actions_for_this, do_with_this and selections_search_web; and
    the shelf's: whats_on_my_shelf, use_my_shelf and take_off_my_shelf (UI-4). do_with_this is also reached by "how
    does this connect" and "how should I use this" (the `connect` action)."""
    from core import ual

    ready = [s.id for s in ual.SPECS if s.ready]
    registry.register(AssistantAction(
        name="actions_for_this", domain="ual",
        description="What MIA can do with a piece of text the person gives (find what they know about it, save it, "
                    "make a mission or project from it, remember it).",
        parameters={"type": "object", "properties": {
            "text": {"type": "string", "description": "The words they want something done with, exactly as given."},
        }, "required": ["text"]}, handler=_offer,
        trigger_phrases=("what can you do with this", "what can i do with this", "do something with this"),
        subjects=("selection",),
    ))
    registry.register(AssistantAction(
        name="do_with_this", domain="ual",
        description="Do one thing with a piece of text the person gives: " + ", ".join(ready) + ".",
        parameters={"type": "object", "properties": {
            "action": {"type": "string", "enum": ready, "description": "Which action."},
            "text": {"type": "string", "description": "The words to act on, exactly as given."},
        }, "required": ["action", "text"]}, handler=_do,
        trigger_phrases=("save this to my inbox", "send this to my inbox", "make this a mission", "keep this on my shelf",
                         "put this on my shelf",
                         "start a project from this", "find what i know about", "how does this connect",
                         "how does this relate", "what does this mean for my", "connect this to",
                         "use this knowledge"),
        subjects=("selection",),
    ))
    which = {"type": "string", "description": "Which things on the shelf: numbers as listed (\"1, 3\"), or all."}
    registry.register(AssistantAction(
        name="whats_on_my_shelf", domain="ual",
        description="What's on the person's shelf (things they sent there to use later), numbered, with days left.",
        parameters={"type": "object", "properties": {}, "required": []}, handler=_shelf,
        trigger_phrases=("what's on my shelf", "whats on my shelf", "show my shelf", "my shelf"),
        subjects=("shelf",),
    ))
    registry.register(AssistantAction(
        name="use_my_shelf", domain="ual",
        description="Do one thing with things on the person's shelf, together as one selection: "
                    + ", ".join(r for r in ready if r != "keep_shelf") + ".",
        parameters={"type": "object", "properties": {
            "action": {"type": "string", "enum": [r for r in ready if r != "keep_shelf"], "description": "Which action."},
            "which": which,
        }, "required": ["action"]}, handler=_use_shelf,
        trigger_phrases=("from my shelf", "on my shelf together", "combine my shelf", "use my shelf"),
        subjects=("shelf",),
    ))
    registry.register(AssistantAction(
        name="take_off_my_shelf", domain="ual",
        description="Take things off the person's shelf: numbers as listed, or all.",
        parameters={"type": "object", "properties": {"which": which}, "required": ["which"]}, handler=_take_off,
        trigger_phrases=("off my shelf", "clear my shelf", "empty my shelf"),
        subjects=("shelf",),
    ))
    registry.register(AssistantAction(
        name="selections_search_web", domain="ual",
        description="Turn on or off letting Research This and Verify These Claims search the web (a few words from "
                    "the selection, through the person's own search engine).",
        parameters={"type": "object", "properties": {
            "on": {"type": "boolean", "description": "True to let selections search the web, false to stop it."},
        }, "required": ["on"]}, handler=_online,
        trigger_phrases=("selections search the web", "research this online", "verify claims online",
                         "stop searching the web for selections"),
        subjects=("selection", "web"),
    ))
