"""
core.web_why
==============

"My Why" on the web (DEC-0125: the why chain was voice-only; "Remember
Why", docs/COGNITIVE_EXTENSION_PROPOSAL.md slice B). The person's reasons
as chains ("Factory work → Pay off debt → Control over my time"), each
link with the reason in their own words, whether it's done (and why), and
the facts behind it from their own records (core/why_graph.py builds
them; this only shapes them for the page), then what changed since the
first monthly checkpoint and recent wins.

Changes are actions, so the page and voice agree and "undo that" takes
each back (intents.json writes through atomic_write_text):

- `why.link`: one goal serves a bigger one, with the reason (either goal
  made from its name when it's new; by voice, link_my_reason).
- `why.unlink`: a goal no longer leads to anything bigger
  (unlink_my_reason).
- `why.achieve`: a goal is marked Achieved, so it's spoken of as done
  (mark_goal_achieved).

MIA never invents a reason: every link and reason here is one the person
gave. Reading the page never records a checkpoint (asking by voice does,
once a month).
"""

from __future__ import annotations

from core.actions import ACTION_TYPES, ActionError, ActionType, _need


def why_page(context, today=None) -> dict:
    """The page's data: the chains (each link's id, name, reason, done and why, evidence), what changed, recent wins,
    and every goal (for the "serves" picker); {"available": False} without goals on this MIA."""
    from core.why_graph import build_why_sheet

    intents = getattr(context, "intents", None)
    if intents is None:
        return {"available": False}
    sheet = build_why_sheet(context, today, record_checkpoint=False)
    goals = sorted(intents.all_intents(), key=lambda i: i.name.lower())
    return {"available": True,
            "chains": [[{"id": l.intent_id, "name": l.name, "reason": l.reason, "done": l.done,
                         "done_because": l.done_because, "evidence": list(l.evidence)} for l in chain]
                       for chain in sheet.chains],
            "changes": list(sheet.changes), "wins": list(sheet.wins),
            "goals": [{"id": g.intent_id, "name": g.name, "serves": g.serves_intent_id or "",
                       "achieved": g.status in ("Achieved", "Archived")} for g in goals]}


# ------------------------------------------------------------------ actions


def _goal(context, key: str, params, make: bool = False):
    """The goal the params name by id (`<key>_id`) or, with make, by name (`<key>`: an existing one by its exact name,
    else a new one); ActionError when there's neither."""
    intents = _need(context, "intents")
    found = intents.get_intent(str(params.get(f"{key}_id") or ""))
    if found is not None:
        return found, False
    name = " ".join(str(params.get(key) or "").split()).rstrip(".")
    if not name:
        raise ActionError("Which goal?" if key == "goal" else "What is it for?")
    same = next((i for i in intents.all_intents() if i.name.lower() == name.lower()), None)
    if same is not None or not make:
        if same is None:
            raise ActionError(f"There's no goal called {name}.")
        return same, False
    return name[:1].upper() + name[1:], True


def _name_of(goal) -> str:
    """A goal's name: a new goal (not made yet) is just its name."""
    return goal if isinstance(goal, str) else goal.name


def _describe_link(context, params) -> str:
    """The approval sentence for why.link: "Factory work → Pay off debt: to get out from under it"; a goal can't serve
    itself, and a link back the other way is refused."""
    goal, _ = _goal(context, "goal", params, make=True)
    serves, _ = _goal(context, "serves", params, make=True)
    if _name_of(goal).lower() == _name_of(serves).lower():
        raise ActionError("Those are the same goal. What is it for?")
    if not isinstance(goal, str) and not isinstance(serves, str) and \
            context.intents.would_create_cycle(goal.intent_id, serves.intent_id):
        raise ActionError(f"{serves.name} already leads to {goal.name}, so it can't go the other way too.")
    reason = str(params.get("reason") or "").strip()
    return f"{_name_of(goal)} → {_name_of(serves)}" + (f": {reason}" if reason else "")


def _link(context, params) -> str:
    """Does why.link: makes either goal when it's new, then links them with the reason in the person's words."""
    from core.why_graph import chain_text_for

    _describe_link(context, params)
    goal, new_goal = _goal(context, "goal", params, make=True)
    serves, new_serves = _goal(context, "serves", params, make=True)
    intents = context.intents
    goal = intents.add_intent(goal) if new_goal else goal
    serves = intents.add_intent(serves) if new_serves else serves
    intents.set_serves(goal.intent_id, serves.intent_id, str(params.get("reason") or "").strip() or None)
    return f"Linked: {chain_text_for(context, goal.intent_id)}."


def _describe_unlink(context, params) -> str:
    """The approval sentence for why.unlink; a goal that leads nowhere is refused."""
    goal, _ = _goal(context, "goal", params)
    if not goal.serves_intent_id:
        raise ActionError(f"{goal.name} isn't linked to anything bigger.")
    bigger = context.intents.get_intent(goal.serves_intent_id)
    return f"Unlink {goal.name} from {bigger.name if bigger else 'what it served'}"


def _unlink(context, params) -> str:
    """Does why.unlink."""
    goal, _ = _goal(context, "goal", params)
    context.intents.set_serves(goal.intent_id, None)
    return f"{goal.name} no longer leads to anything bigger."


def _describe_achieve(context, params) -> str:
    """The approval sentence for why.achieve; a goal already achieved is refused."""
    goal, _ = _goal(context, "goal", params)
    if goal.status in ("Achieved", "Archived"):
        raise ActionError(f"{goal.name} is already marked {goal.status.lower()}.")
    return f"Mark {goal.name} achieved"


def _achieve(context, params) -> str:
    """Does why.achieve: the goal is Achieved, so the chain speaks of it as done."""
    goal, _ = _goal(context, "goal", params)
    context.intents.update_intent(goal.intent_id, status="Achieved")
    return f"{goal.name}: achieved. That's a real milestone."


WHY_ACTIONS = {a.kind: a for a in (
    ActionType("why.link", "Link", {"goal": "what you're doing (or goal_id)", "serves": "what it's for (or serves_id)",
                                    "reason": "why, in your words (optional)"}, _describe_link, _link),
    ActionType("why.unlink", "Unlink", {"goal_id": "the goal"}, _describe_unlink, _unlink),
    ActionType("why.achieve", "Achieved", {"goal_id": "the goal"}, _describe_achieve, _achieve),
)}
ACTION_TYPES.update(WHY_ACTIONS)
