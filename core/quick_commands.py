"""
core.quick_commands
=====================

Things a person says that need no AI model (DEC-0020): "workout
complete", "step one of today's workout complete", "finished my
pull-ups", "today's lunch complete", "meal prep done", "this week's
meal plans complete", "I weigh 182", "had 40 g of protein", "handstand
45 seconds", "undo that". MIA's own code recognises them and does them
at once, through the same actions the screens use (core/fitness_actions.py),
so the mission, Kitchen and Workout all show it and "undo that" takes it
back. Anything else goes to the model as before (core/assistant_turn.py).

`parse()` is pure: a sentence -> (action kind, params), or None.
"""

from __future__ import annotations

import re
from typing import Optional

NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
                "ten": 10, "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6, "seventh": 7,
                "eighth": 8, "ninth": 9, "tenth": 10}
DONE = r"(?:done|complete|completed|finished|over|knocked out|in the books)"
FINISHED = r"(?:finished|done with|completed|did|crushed|knocked out)"
MEAL = r"(breakfast|lunch|dinner|supper|snack)"
UNDO = re.compile(r"^(?:undo(?: that| it| the last (?:one|thing))?|take (?:that|it) back|scratch that)$")
WEIGHT = re.compile(r"\b(?:i )?(?:weigh(?:ed)?(?: in)?(?: at)?|weight(?: is| was| today)?|weighing in at)\s*:?\s*"
                    r"(\d{2,4}(?:\.\d)?)\s*(lbs?|pounds|kgs?|kilos|kilograms)?\b")
PROTEIN = re.compile(r"\b(\d{1,3}(?:\.\d)?)\s*(?:g|grams?|gs)\s*(?:of\s+)?protein\b")
PROTEIN_HIT = re.compile(r"\b(?:hit|reached|made|got) (?:my |the )?protein(?: target| goal)?\b")
STEP = re.compile(r"\b(?:step|exercise|move|part)\s+(\d+|" + "|".join(NUMBER_WORDS) + r")\b")
STEP_ORDINAL = re.compile(r"\b(" + "|".join(w for w in NUMBER_WORDS if not w.isdigit()) + r")\s+(?:step|exercise)\b")
TRAINING = re.compile(rf"\b(?:workout|training|work ?out|lifting|session)(?:'s)?\s*(?:is\s+|was\s+)?{DONE}\b"
                      rf"|\b{FINISHED}\s+(?:my\s+|today'?s\s+|the\s+)?(?:workout|training|session)\b"
                      r"|\bi\s+(?:worked out|trained|lifted)\b")
MEAL_DONE = re.compile(rf"\b{MEAL}(?:'s)?\s*(?:is\s+|was\s+)?(?:{DONE}|eaten)\b|\b(?:ate|had|finished|eaten)\s+"
                       rf"(?:my\s+|today'?s\s+|the\s+)?{MEAL}\b")
PREP = re.compile(rf"\b(?:meal ?prep|prepping|prep)(?:'s)?\s*(?:is\s+|was\s+)?{DONE}\b|\b{FINISHED}\s+(?:the\s+|my\s+)?"
                  rf"(?:meal ?prep|prep)\b|\bweek'?s meal plans?\s*(?:is\s+|are\s+)?{DONE}\b")
HOLD = re.compile(r"\b(\d{1,4}(?:\.\d)?)\s*(?:s|sec|secs|seconds)\b")
TODAY_KEY = "today"  # replaced with today's date by handle()
SKILL_WORDS = ("handstand", "l-sit", "l sit", "crow", "plank", "muscle-up", "muscle up", "hollow hold", "dead hang",
               "frog pose", "planche", "front lever", "back lever")


def _clean(text: str) -> str:
    text = text.lower().replace("’", "'").strip()
    return re.sub(r"(?<!\d)[.,](?!\d)|[.,](?=\s|$)|[!?;]+", " ", text).strip()  # keeps 182.4


def _number(word: str) -> int:
    return int(word) if word.isdigit() else NUMBER_WORDS[word]


def parse(text: str, plan: Optional[dict] = None, today_training: Optional[dict] = None,
          planned: Optional[dict] = None) -> Optional[tuple[str, dict]]:
    """Pure logic. What a short sentence asks for, or None (let the model
    have it). Long messages and questions are never commands."""
    said = _clean(text)
    if not said or len(said.split()) > 14 or said.endswith("?") or text.strip().endswith("?"):
        return None
    if said.startswith(("how ", "what ", "when ", "why ", "should ", "can ", "could ", "do ", "does ", "is ", "are ")):
        return None
    if UNDO.match(said):
        return ("undo", {})
    match = WEIGHT.search(said)
    if match:
        unit = match.group(2) or ""
        params = {"weight": match.group(1)}
        if unit:
            params["unit"] = "kg" if unit.startswith("k") else "lb"
        return ("fitness.weigh_in", params)
    if PROTEIN_HIT.search(said):
        return ("fitness.habit", {"habit": "protein"})
    match = PROTEIN.search(said)
    if match:
        return ("fitness.protein", {"grams": match.group(1)})
    if PREP.search(said):
        return ("fitness.habit", {"habit": "prep"})
    match = STEP.search(said) or STEP_ORDINAL.search(said)
    if match and re.search(DONE + r"|" + FINISHED, said):
        return ("fitness.step", {"step": str(_number(match.group(1)))})
    for index, exercise in enumerate((today_training or {}).get("exercises") or []):
        name = exercise.get("name", "").lower()
        if name and len(name) > 2 and re.search(r"\b" + re.escape(name.rstrip("s")), said) \
                and re.search(DONE + r"|" + FINISHED, said):
            return ("fitness.step", {"step": str(index + 1)})
    if TRAINING.search(said):
        return ("fitness.training_done", {})
    match = MEAL_DONE.search(said)
    if match:
        meal = next(g for g in match.groups() if g)
        meal = "dinner" if meal == "supper" else meal
        slot = (planned or {}).get(meal)
        if slot:  # the meal planned for today: its recipe and nutrition
            return ("fitness.food", {"meal": meal, "recipe_id": slot["recipe_id"], "servings": slot.get("servings", 1),
                                     "planned_id": f"{TODAY_KEY}:{meal}"})
        packed = bool(((plan or {}).get("meals") or {}).get("packed_lunch"))
        if meal == "lunch" and packed:
            return ("fitness.habit", {"habit": "lunch"})
        return ("fitness.food", {"meal": meal, "name": meal.capitalize()})
    seconds = HOLD.search(said)
    if seconds:
        skills = [s.get("skill", "") for s in (plan or {}).get("skill_tree") or []] + list(SKILL_WORDS)
        skill = next((s for s in skills if s and s.lower() in said), None)
        if skill:
            return ("fitness.skill", {"skill": skill.title(), "seconds": seconds.group(1)})
    return None


def _workout(context, text: str) -> Optional[str]:
    """The live workout's spoken controls (DEC-0055, core/training_session.py):
    "start my workout", "twelve", "next set", "pause", "make that 10",
    "I'm done"... ahead of everything else while a workout is going."""
    from datetime import datetime

    from core import training_session as ts
    from core.actions import ActionError

    store = getattr(context, "training", None)
    if store is None:
        return None
    live, now = store.live(), datetime.now()
    if live is not None:
        ts.settle(live, now)
    found = ts.parse_training(text, live.status if live is not None else None)
    if found is None:
        return None
    kind, params = found
    if kind == "say":
        return ts.say(live, now)
    if kind == "ask":
        return "How many did you get?"
    actions = getattr(context, "actions", None)
    if actions is None:
        return None
    try:
        proposal = actions.propose(context, kind, params, proposed_by="mia")
        done = actions.approve(context, proposal.proposal_id)
    except ActionError as problem:
        return str(problem)
    return done.result if done.status == "executed" else (done.result or "That didn't work; nothing was changed.")


def handle(context, text: str) -> Optional[str]:
    """Does it, if it's a quick command; returns MIA's reply, or None."""
    from core.actions import ActionError
    from core.person_settings import person_id

    said = _workout(context, text)
    if said is not None:
        return said

    fit = getattr(context, "fitness", None)
    plan = fit.plan if fit is not None else None
    training = None
    if fit is not None:
        try:
            training = fit.today_training()
        except Exception:
            training = None
    from datetime import date

    today = date.today().isoformat()
    planned = fit.planned(today) if fit is not None else {}
    found = parse(text, plan, training, planned)
    if found is not None and found[1].get("planned_id", "").startswith(TODAY_KEY):
        found[1]["planned_id"] = found[1]["planned_id"].replace(TODAY_KEY, today, 1)
    if found is None:
        return None
    kind, params = found
    if kind == "undo":
        from core.undo_log import undo_last

        change = undo_last(context, person_id(context))
        if change is None:
            return "There's nothing to undo."
        if fit is not None:
            from core.fitness_missions import sync

            sync(context)
        return "Undone."
    actions = getattr(context, "actions", None)
    if actions is None or fit is None:
        return None
    try:
        proposal = actions.propose(context, kind, params, proposed_by="mia")
        done = actions.approve(context, proposal.proposal_id)
    except ActionError as problem:
        return str(problem)
    if done.status != "executed":
        return done.result or "That didn't work; nothing was changed."
    return f"{done.result} (Say “undo that” to take it back.)"
