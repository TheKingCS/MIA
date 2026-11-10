"""
core.assistant_cooking_actions
================================

Cook mode by voice (DEC-0113 cook mode, DEC-0125: full use both ways). With
flour on your hands: "start cooking the chili", "next step", "go back", "what
step am I on", "go to step 4", "set a rice timer for 18 minutes", "stop the
rice timer", "I made it", "stop cooking". Each tool runs the same action kind
the Kitchen's buttons do (core/cooking_actions.py), checked then run, so the
words and the numbers match the screen and "undo that" takes a move back.
"""

from __future__ import annotations

import re
from datetime import datetime

from core.assistant_actions import AssistantAction


def _run(context, kind: str, params: dict) -> str:
    """A cook-mode action kind, checked then run, as the screen does; its own words when it can't."""
    from core.actions import run_as_tool

    return run_as_tool(context, kind, params)


def find_recipe(recipes: list, words: str):
    """Pure logic. The recipe the words name: the exact name, else one whose name is in the words or holds them,
    else the one sharing the most words with them (ignoring "the", "my", "recipe"). None when nothing shares a word."""
    said = (words or "").strip().lower()
    if not said or not recipes:
        return None
    for r in recipes:
        if r.name.lower() == said:
            return r
    for r in recipes:
        if r.name.lower() in said or said in r.name.lower():
            return r
    noise = {"the", "my", "a", "recipe", "some", "for", "of"}
    want = set(re.findall(r"[a-z]+", said)) - noise
    scored = [(len(want & set(re.findall(r"[a-z]+", r.name.lower()))), r) for r in recipes]
    best = max(scored, key=lambda x: x[0])
    return best[1] if best[0] else None


def _start(context, arguments: dict) -> str:
    """Tool cook_start: starts cook mode for the recipe they named."""
    kitchen = getattr(context, "kitchen", None)
    if kitchen is None:
        return "The Kitchen isn't on this MIA."
    recipe = find_recipe([r for r in kitchen.all_recipes() if not r.locked], str(arguments.get("recipe") or ""))
    if recipe is None:
        return "Which recipe? Say its name, like \"start cooking the chili\"."
    return _run(context, "cooking.start", {"recipe_id": recipe.recipe_id})


def _step(context, arguments: dict) -> str:
    """Tool cook_step: next, back, a step by number, or where they are (and which timers are done)."""
    from core import cooking_session as cs

    move = str(arguments.get("move") or "where").lower()
    if arguments.get("step"):
        return _run(context, "cooking.go_to", {"step": arguments["step"]})
    if move in ("next", "back"):
        return _run(context, "cooking." + move, {})
    store = getattr(context, "cooking", None)
    s = store.live() if store is not None else None
    if s is None:
        return "Nothing's cooking. Say \"start cooking\" and the recipe."
    return cs.say(s, datetime.now())


def _timer(context, arguments: dict) -> str:
    """Tool cook_timer: starts a named timer for some minutes, or stops one."""
    name = str(arguments.get("name") or "Timer").strip() or "Timer"
    if str(arguments.get("stop") or "").lower() in ("yes", "true", "1") or arguments.get("stop") is True:
        return _run(context, "cooking.timer_cancel", {"name": name})
    if not arguments.get("minutes"):
        return "How many minutes?"
    return _run(context, "cooking.timer", {"name": name, "minutes": arguments["minutes"]})


def _finish(context, arguments: dict) -> str:
    """Tool cook_finish: "I made it" logs the meal (and uses up the pantry), or stops without logging."""
    made = str(arguments.get("made") or "yes").lower() not in ("no", "false", "0")
    if not made:
        return _run(context, "cooking.stop", {})
    return _run(context, "cooking.made", {"pantry": arguments.get("pantry") or "yes"})


def register_cooking_actions(registry) -> None:
    """Registers cook mode's voice tools: cook_start, cook_step, cook_timer and cook_finish."""
    s = {"type": "string"}
    registry.register(AssistantAction(
        name="cook_start", domain="kitchen",
        description="Start cook mode for a recipe: its steps one at a time, with timers. 'Start cooking the chili'.",
        parameters={"type": "object", "properties": {"recipe": {**s, "description": "The recipe's name as they said it."}},
                    "required": ["recipe"]},
        handler=_start,
        trigger_phrases=("start cooking", "let's cook", "cook mode", "walk me through", "start the recipe"),
        subjects=("cooking",),
    ))
    registry.register(AssistantAction(
        name="cook_step", domain="kitchen",
        description="Move through the recipe being cooked: next step, back a step, go to a step by number, or say "
                    "where they are.",
        parameters={"type": "object", "properties": {
            "move": {**s, "enum": ["next", "back", "where"], "description": "Next, back, or where (repeat the step)."},
            "step": {"type": "integer", "description": "A step number, only if they said one."}}, "required": []},
        handler=_step,
        trigger_phrases=("next step", "previous step", "go back a step", "what step", "repeat that step", "go to step",
                         "read the step"),
        subjects=("step",),
    ))
    registry.register(AssistantAction(
        name="cook_timer", domain="kitchen",
        description="Start a named cooking timer for some minutes (it keeps running across steps), or stop one.",
        parameters={"type": "object", "properties": {
            "name": {**s, "description": "What it's for: rice, simmer, oven..."},
            "minutes": {"type": "number", "description": "How long, in minutes."},
            "stop": {**s, "description": "'yes' to stop that timer."}}, "required": []},
        handler=_timer,
        trigger_phrases=("set a timer", "timer for", "start a timer", "stop the timer", "cancel the timer"),
        subjects=("timer",),
    ))
    registry.register(AssistantAction(
        name="cook_finish", domain="kitchen",
        description="Finish cook mode: 'I made it' logs the meal and takes it out of the pantry; 'stop cooking' ends "
                    "it without logging.",
        parameters={"type": "object", "properties": {
            "made": {**s, "description": "'yes' when they made it, 'no' to stop without logging."},
            "pantry": {**s, "description": "'no' to leave the pantry as it is, only if they said."}}, "required": []},
        handler=_finish,
        trigger_phrases=("i made it", "it's done cooking", "stop cooking", "finished cooking", "dinner's ready"),
        subjects=("cooking",),
    ))
