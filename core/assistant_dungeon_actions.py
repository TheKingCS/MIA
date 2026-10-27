"""
core.assistant_dungeon_actions
================================

The Dungeon by voice (DEC-0046): "How much loot this week?", "I worked 9
hours, we were unstocked", "I picked up an overtime shift Saturday",
"Make it a quest". Each runs the same code as the screen (the action
kinds in core/dungeon_actions.py, the numbers in core/web_dungeon.py),
so the loot matches and "undo that" takes a run back.
"""

from __future__ import annotations

from datetime import date, timedelta

from core.assistant_actions import AssistantAction, AssistantActionRegistry
from core.assistant_goods_actions import _run

_WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


def _when(raw: str, forward: bool) -> str:
    """"today", "tomorrow", "yesterday", a weekday (the next one ahead
    when planning, the last one when logging) or a date, as YYYY-MM-DD."""
    text = str(raw or "").strip().lower()
    today = date.today()
    if text in ("", "today", "tonight"):
        return today.isoformat()
    if text == "tomorrow":
        return (today + timedelta(days=1)).isoformat()
    if text in ("yesterday", "last night"):
        return (today - timedelta(days=1)).isoformat()
    for i, name in enumerate(_WEEKDAYS):
        if name in text:
            gap = (i - today.weekday()) % 7 if forward else -((today.weekday() - i) % 7)
            return (today + timedelta(days=gap or (7 if forward and "next" in text else 0))).isoformat()
    return text


def _get_loot(context, arguments: dict) -> str:
    from core.web_dungeon import dungeon_page

    page = dungeon_page(context)
    if not page.get("available"):
        return "That one's for grown-ups."
    if not page["dungeons"]:
        return "No dungeon set up yet: Apps → The Dungeon, put in the job and its pay."
    said = []
    for v in page["dungeons"]:
        w = v["week"]
        if not v["set_up"]:
            said.append(f"{v['name']}: {w['hours']:g} hours this week; put in the pay an hour to see the loot.")
            continue
        line = f"{v['name']}: {w['earned_text']} loot this week from {w['hours']:g} hours"
        if w["bonus_text"]:
            line += f" ({w['bonus_text']} of it overtime boss bonus)"
        if w["projected"] != w["earned"]:
            line += f", {w['projected_text']} projected with the planned runs"
        ot = v["overtime_now"]
        if ot["in_overtime"]:
            line += f"; you're in overtime, {ot['hour_text']} an hour"
        elif ot["hours_to_overtime"] is not None and ot["hour_text"]:
            line += f"; overtime starts after {ot['hours_to_overtime']:g} more hours"
        line += f". This month: {v['month']['earned_text']} earned"
        if v["banked"]["count_month"]:
            line += f", {v['banked']['month_text']} banked from {v['banked']['count_month']} paycheck(s)"
        if v["pace"]["yearly_text"]:
            line += f". At this pace, {v['pace']['yearly_text']} a year before taxes"
        said.append(line + ".")
    nxt = page.get("next_dungeon")
    if nxt and nxt.get("ready"):
        said.append(f"The next dungeon (Freedom) is {nxt['progress_pct']:g}% unlocked.")
    return " ".join(said)


def _log_shift(context, arguments: dict) -> str:
    params = {"date": _when(arguments.get("day"), forward=False), "hours": arguments.get("hours"),
              "hard_mode": arguments.get("hard_mode") or "", "overtime": arguments.get("overtime") or ""}
    return _run(context, "dungeon.run", params)


def _plan_shift(context, arguments: dict) -> str:
    params = {"date": _when(arguments.get("day"), forward=True), "hours": arguments.get("hours"),
              "overtime": arguments.get("overtime") or ""}
    return _run(context, "dungeon.plan", params)


def _start_quest(context, arguments: dict) -> str:
    challenge = str(arguments.get("challenge") or "").strip()
    if not challenge:
        # "Make it a quest" right after a hard-mode run: that run's modifier.
        book = getattr(context, "dungeon", None)
        today = date.today().isoformat()
        run = next((r for r in (book.runs if book else []) if r.date == today and r.affixes), None)
        challenge = run.affixes[0] if run else ""
    if not challenge:
        return "Which challenge should be the quest?"
    return _run(context, "dungeon.quest", {"challenge": challenge, "goal": arguments.get("goal") or ""})


def register_dungeon_actions(registry: AssistantActionRegistry) -> None:
    registry.register(AssistantAction(
        name="get_dungeon_loot", domain="dungeon",
        description=("The Dungeon (work as a game): loot this week from hours worked, overtime boss bonus, projected "
                     "loot with planned shifts, this month earned and banked paychecks, the yearly pace."),
        parameters={"type": "object", "properties": {}, "required": []}, handler=_get_loot,
        trigger_phrases=("loot", "how much have i made", "how much did i make", "earned this week", "made this week",
                         "how much was my paycheck", "paycheck this week", "my overtime", "projected pay", "how much will i make", "the dungeon"),
        subjects=("loot", "paycheck", "overtime", "dungeon", "pay", "earned", "shift"),
    ))
    registry.register(AssistantAction(
        name="log_shift", domain="dungeon",
        description=("Log a work shift (clear a run in The Dungeon): hours worked, and what made it hard mode "
                     "(unstocked, short-staffed, a truck, equipment down, slammed, a mess)."),
        parameters={"type": "object", "properties": {
            "hours": {"type": "number", "description": "Hours worked."},
            "day": {"type": "string", "description": "today, yesterday, a weekday, or YYYY-MM-DD. Blank: today."},
            "hard_mode": {"type": "string", "description": "What made it hard, comma-separated, only if they said."},
            "overtime": {"type": "boolean", "description": "True only for a called-in overtime shift."}},
            "required": ["hours"]},
        handler=_log_shift,
        trigger_phrases=("i worked", "worked today", "log my shift", "log the shift", "cleared my shift",
                         "cleared the run", "clocked out", "hours today", "got off work"),
        subjects=("shift", "work", "hours", "run"),
    ))
    registry.register(AssistantAction(
        name="plan_shift", domain="dungeon",
        description="Put an upcoming work shift on the schedule (projected loot); an overtime shift is a boss.",
        parameters={"type": "object", "properties": {
            "day": {"type": "string", "description": "tomorrow, a weekday, or YYYY-MM-DD."},
            "hours": {"type": "number", "description": "Hours, only if they said."},
            "overtime": {"type": "boolean", "description": "True for an overtime shift."}},
            "required": ["day"]},
        handler=_plan_shift,
        trigger_phrases=("picked up a shift", "picked up an overtime", "working saturday", "working sunday",
                         "i'm working", "im working", "schedule a shift", "plan a shift", "overtime shift"),
        subjects=("shift", "overtime", "schedule"),
    ))
    registry.register(AssistantAction(
        name="start_quest", domain="dungeon",
        description=("The Game Master's quest: turn a real challenge (\"unstocked\", \"short-staffed\", or their words) "
                     "into a hard-mode mission with an XP reward."),
        parameters={"type": "object", "properties": {
            "challenge": {"type": "string", "description": "The challenge, in their words."},
            "goal": {"type": "string", "description": "What clearing it means, only if they said."}},
            "required": []},
        handler=_start_quest,
        trigger_phrases=("make it a quest", "make it a mission", "turn it into a quest", "accept the quest",
                         "take the quest"),
        subjects=("quest",),
    ))
