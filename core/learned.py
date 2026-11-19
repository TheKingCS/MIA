"""
core.learned
============

What MIA has learned about him on her own, each habit with its evidence and its own reset (DEC-0282, LS-10,
REQ-LS-004). Three kinds today:

- **pace**: how many of a kind of message she offers a day, learned from what he opens, uses or passes over
  (core/communication_gate.py, DEC-0171); reset, she starts that kind again from its usual pace;
- **break**: a kind she stopped offering for a while because he kept dismissing it; reset, she may offer it again;
- **style**: how she answers on one dimension (length, tone...), learned from his A/B picks (core/response_style.py,
  DEC-0138); reset, she forgets those picks.

**What no reset touches** (DEC-0282): his grants and standing yeses, a break he asked for, the stop, and anything he
set himself (a style he chose outright, a setting). Each reset changes one habit, through the action `learned.reset`
(undoable, since the stores write through atomic_write_text).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from core.actions import ACTION_TYPES, ActionError, ActionType


@dataclass
class Habit:
    """One learned habit: its id (`kind:name`), what she does, the evidence, and what a reset does."""
    habit_id: str
    what: str
    evidence: str
    reset_does: str

    def as_dict(self) -> dict:
        """For a screen."""
        return asdict(self)


def habits(context) -> list[Habit]:
    """Every habit she has learned on her own, from the stores that keep them; none from a store that's missing."""
    out: list[Habit] = []
    gate = getattr(context, "communication", None)
    if gate is not None:
        for row in gate.pace():
            if row["why"].startswith("I'm still learning"):
                continue
            out.append(Habit(f"pace:{row['topic']}", f"I offer {row['label']} up to {row['a_day']} a day",
                             row["why"][0].upper() + row["why"][1:] + ".", "I go back to its usual pace and learn again."))
        for row in gate.inferred_breaks():
            until = row["until"].strftime("%B %d").replace(" 0", " ")
            out.append(Habit(f"break:{row['topic']}", f"I'm not offering {row['label']} until {until}",
                             "You dismissed several of these in a row.", "I may offer them again."))
    style = getattr(context, "response_style", None)
    if style is not None:
        from core.response_style import DIMENSIONS

        for dimension in DIMENSIONS:
            if not style.learned_only(dimension):
                continue
            counts = style.tally(dimension)
            value, times = counts.most_common(1)[0]
            out.append(Habit(f"style:{dimension}", f"I answer {value.replace('_', ' ')} ({dimension.replace('_', ' ')})",
                             f"You picked it {times} of {sum(counts.values())} times.",
                             "I forget those picks and answer in my usual way."))
    return out


def _find(context, params) -> Habit:
    """The habit the params name (`habit_id`, or `habit` in words matched against what she does); ActionError when
    none."""
    wanted = str(params.get("habit_id") or "").strip()
    words = str(params.get("habit") or "").strip().lower()
    for habit in habits(context):
        if habit.habit_id == wanted or (words and words in habit.what.lower()):
            return habit
    raise ActionError("Which one? Say it as \"What I've learned\" on the Apps page lists it.")


def _describe(context, params) -> str:
    """The approval sentence for `learned.reset`."""
    habit = _find(context, params)
    return f"Forget what I learned: {habit.what}. {habit.reset_does}"


def _execute(context, params) -> str:
    """Does `learned.reset`: one habit, nothing else."""
    habit = _find(context, params)
    kind, _, name = habit.habit_id.partition(":")
    if kind == "pace":
        context.communication.relearn(name)
    elif kind == "break":
        context.communication.resume(name)
    elif kind == "style":
        context.response_style.relearn(name)
    return f"Forgotten: {habit.what}."


ACTION_TYPES["learned.reset"] = ActionType(
    "learned.reset", "Forget this", {"habit_id": "the habit", "habit": "or what it is, in words"}, _describe, _execute)
