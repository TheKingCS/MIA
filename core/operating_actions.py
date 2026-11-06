"""
core.operating_actions
========================

The Operating Journal (core/operating_journal.py, DEC-0097) through the action
contract (core/actions.py): `operating.add` (a line of how they mean to
operate), `operating.remove`, and `operating.rate` (a self-rated line, 1 to 5,
for this week). The journal writes through atomic_write_text, so "undo that"
takes a change back.
"""

from __future__ import annotations

from core.actions import ACTION_TYPES, ActionError, ActionType, _need


def _journal(context):
    return _need(context, "operating_journal")


def _line(context, params) -> dict:
    found = next((l for l in _journal(context).lines if l["id"] == str(params.get("line_id", ""))), None)
    if found is None:
        raise ActionError("That line isn't in your Operating Journal.")
    return found


def _describe_add(context, params) -> str:
    text = " ".join(str(params.get("text") or "").split())
    if not text:
        raise ActionError("Say how you want to operate.")
    return f"Add to your Operating Journal: \"{text[:120]}\""


def _add(context, params) -> str:
    from core.operating_journal import habit_from

    line = _journal(context).add(params.get("text", ""), str(params.get("section") or ""))
    h = habit_from(line["text"])
    if h["kind"] == "count":
        how = f"I'll check it against your {h['word']} each {h['per']}"
    elif h["kind"] == "spending":
        how = f"I'll check it against what's spent on {h['category']} each month"
    else:
        how = "I can't see that one in your records, so you rate it: say \"rate " + \
              " ".join(line["text"].split()[:3]).lower() + " 4\" any week"
    return f"In your Operating Journal. {how}."


def _describe_remove(context, params) -> str:
    return f"Take \"{_line(context, params)['text'][:80]}\" out of your Operating Journal"


def _remove(context, params) -> str:
    _journal(context).remove(_line(context, params)["id"])
    return "Taken out."


def _describe_rate(context, params) -> str:
    line = _line(context, params)
    try:
        score = int(params.get("score"))
    except (TypeError, ValueError):
        raise ActionError("Rate it from 1 to 5.") from None
    if not 1 <= score <= 5:
        raise ActionError("Rate it from 1 to 5.")
    return f"Rate \"{line['text'][:80]}\" {score} out of 5 this week"


def _rate(context, params) -> str:
    line = _line(context, params)
    _journal(context).rate(line["id"], int(params["score"]))
    return f"Noted: {int(params['score'])} out of 5 for \"{line['text'][:60]}\" this week."


OPERATING_ACTIONS = {a.kind: a for a in (
    ActionType("operating.add", "Add it", {"text": "how you mean to operate", "section": "values, priorities, day, "
               "week or rules"}, _describe_add, _add, child_ok=True),
    ActionType("operating.remove", "Take it out", {"line_id": "the line"}, _describe_remove, _remove, child_ok=True),
    ActionType("operating.rate", "Rate it", {"line_id": "the line", "score": "1 to 5"}, _describe_rate, _rate,
               child_ok=True),
)}
ACTION_TYPES.update(OPERATING_ACTIONS)
