"""
core.assistant_ual_actions
============================

The Universal Action Layer by voice (DEC-0165, core/ual.py): "what can you
do with this: ..." answers with the same offer the palette and the phone
show for the same words. "Save this to my inbox: ..." or "make this a
mission: ..." go through the same catalogue. By voice, saying it is the
yes, as for every voice tool: the action is checked and run by the action
contract, and "undo that" takes it back.

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


def register_ual_actions(registry: AssistantActionRegistry) -> None:
    """Registers the Universal Action Layer's tools: actions_for_this, do_with_this and selections_search_web."""
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
        trigger_phrases=("save this to my inbox", "send this to my inbox", "make this a mission",
                         "start a project from this", "find what i know about"),
        subjects=("selection",),
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
