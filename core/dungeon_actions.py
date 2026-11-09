"""
core.dungeon_actions
======================

The Dungeon's actions (DEC-0046, core/work_dungeon.py) on the action
contract: proposed in plain words with the loot they bring, approved,
run, undoable.

- `dungeon.add/edit/delete`: a dungeon (the job: pay an hour, overtime,
  the pay week, a shift differential and its days, the paycheck's words
  in the bank, take-home share).
- `dungeon.run`: clear a run (a shift worked): the hours, what made it
  hard mode, and any tips. Today's planned run, if there is one, is the
  one cleared.
- `dungeon.tips`: a run's tips, counted after the shift.
- `dungeon.plan`: put a run on the schedule (an overtime boss when it's
  a called-in shift).
- `dungeon.run_delete`: take a run back.
- `dungeon.quest`: the Game Master turns a hard-mode modifier (or the
  person's own words) into a mission to clear, with its reward.
"""

from __future__ import annotations

from datetime import date

from core.actions import ACTION_TYPES, ActionError, ActionType, _need
from core.record_actions import Field, Record, record_kinds
from core.work_dungeon import AFFIX_BY_ID, DAYS, affix_names, boss_bonus, loot, parse_affixes, run_xp, split_hours

DUNGEON = Record("dungeon", "dungeon", "dungeon_id", "get_dungeon", "add_dungeon", "update_dungeon", "delete_dungeon",
                 store="dungeon", fields=(
                     Field("name", "Name (the job, the store, the plant…)", "text", True),
                     Field("hourly", "Pay an hour (before taxes)", "money", default=0, say="pay an hour"),
                     Field("overtime_multiplier", "Overtime pays (1.5 = time and a half)", "amount", default=1.5,
                           say="overtime rate", quiet_default=True),
                     Field("overtime_after", "Overtime after (hours a week; 0 = none)", "amount", default=40,
                           say="overtime after", quiet_default=True),
                     Field("week_starts", "The pay week starts on", "choice", options=DAYS, default="Monday",
                           say="pay week starts", quiet_default=True),
                     Field("shift_hours", "A usual shift (hours)", "amount", default=8, say="usual shift",
                           quiet_default=True),
                     Field("break_minutes", "Unpaid break each shift (minutes)", "amount", default=0,
                           say="unpaid break", quiet_default=True),
                     Field("differential", "Shift differential (extra an hour; 0 = none)", "money", default=0,
                           say="shift differential", quiet_default=True),
                     Field("differential_days", "The days it's paid (e.g. Saturday, Sunday or weekends)", "text",
                           say="differential days"),
                     Field("payer", "What the paycheck says in the bank", "text", say="paycheck words"),
                     Field("take_home_pct", "Take-home share, % (blank: MIA learns it from the bank)", "amount",
                           default=0, say="take-home share"),
                     Field("notes", "Notes", "textarea")))


def _money(x: float) -> str:
    """An amount in the person's currency."""
    from core.region import money

    return money(x)


def _book(context):
    """The person's Dungeon store, or ActionError when it isn't here."""
    return _need(context, "dungeon")


def _dungeon(context, params):
    """The dungeon the params name, or the only one when there's just one; ActionError asking which, or to set one up."""
    book = _book(context)
    wanted = str(params.get("dungeon_id") or "")
    found = book.get_dungeon(wanted) if wanted else (book.dungeons[0] if len(book.dungeons) == 1 else None)
    if found is None:
        raise ActionError("Which dungeon?" if book.dungeons and not wanted else "That dungeon isn't there anymore."
                          if wanted else "Set up your dungeon first (Apps → The Dungeon: the job and its pay).")
    return found


def _day(params) -> str:
    """The date in the params (blank or "today" is today), or ActionError."""
    raw = str(params.get("date") or "").strip()
    if not raw or raw.lower() == "today":
        return date.today().isoformat()
    try:
        return date.fromisoformat(raw[:10]).isoformat()
    except ValueError:
        raise ActionError("The date has to look like 2026-10-27.") from None


def _hours(params, d, needed: bool = True) -> float:
    """The hours in the params (0 to 24), or the dungeon's usual shift when blank; with needed=False a blank is 0."""
    raw = params.get("hours")
    if raw in (None, ""):
        if not needed:
            return 0.0
        return float(d.shift_hours or 0) or _no_hours()
    try:
        value = float(raw)
    except (TypeError, ValueError):
        raise ActionError("Hours has to be a number.") from None
    if value <= 0 or value > 24:
        raise ActionError("A run is between 0 and 24 hours.")
    return value


def _no_hours() -> float:
    """Raises ActionError asking how many hours (when there's no usual shift to fall back on)."""
    raise ActionError("How many hours?")


def _flag(raw) -> bool:
    """Whether a param says yes (true, yes, on, overtime, boss...)."""
    return str(raw).strip().lower() in ("1", "true", "yes", "on", "overtime", "boss")


def _when(day: str) -> str:
    """"today" or "on <date>"."""
    return "today" if day == date.today().isoformat() else f"on {day}"


def _with(context, d, run_date: str, hours: float, run_id: str = "") -> tuple[float, float]:
    """This run's (regular, overtime) hours among the week's cleared runs."""
    from core.work_dungeon import Run

    others = [r for r in _book(context).runs if r.run_id != run_id]
    probe = Run(run_id="__probe", dungeon_id=d.dungeon_id, date=run_date, hours=hours, created_at="9999")
    return split_hours(d, others + [probe])["__probe"]


def _loot_words(d, regular: float, overtime: float, run=None) -> str:
    """What a run earns in words (" about <money> loot" with its shift differential and tips when the run is given,
    plus the boss bonus when there's overtime), or "" when the job has no pay rate and there are no tips.
    """
    from core.work_dungeon import run_differential, run_loot

    tips = float(getattr(run, "tips", 0) or 0)
    if not d.hourly and not tips:
        return ""
    worth = run_loot(d, run, regular, overtime) if run is not None else loot(d, regular, overtime)
    words = f" — about {_money(worth)} loot"
    diff = run_differential(d, run) if run is not None else 0.0
    if diff or tips:
        words += " (" + ", ".join(b for b in (f"{_money(diff)} an hour differential" if diff else "",
                                              f"{_money(tips)} tips" if tips else "") if b) + ")"
    if overtime:
        words += f" ({overtime:g} h overtime: boss bonus {_money(boss_bonus(d, overtime))})"
    return words


# ---------------------------------------------------------------- a run


def _run_plan(context, params):
    """What clearing a run takes: the dungeon, the day (blank: the shift's own day, so a night shift cleared after
    midnight counts for the day it began), the hours (the planned run's when blank), hard-mode modifiers, whether it's
    a boss, the planned run if any, a note, and the tips taken.
    """
    d = _dungeon(context, params)
    if str(params.get("date") or "").strip().lower() in ("", "today"):
        # A night shift cleared after midnight counts for the day it started (core/the_loop.py).
        from core.the_loop import shift_day_for

        day = shift_day_for(context, d.dungeon_id).isoformat()
    else:
        day = _day(params)
    planned = _book(context).planned_on(d.dungeon_id, day)
    hours = _hours(params, d, needed=planned is None) or (planned.hours if planned else 0.0)
    affixes = parse_affixes(params.get("hard_mode") or params.get("affixes") or "")
    boss = _flag(params.get("overtime")) or (planned.boss if planned else False)
    return d, day, hours, affixes, boss, planned, str(params.get("note") or "").strip(), _tips_of(params)


def _tips_of(params) -> float:
    """The tips in the params (blank: none), or ActionError."""
    raw = params.get("tips")
    if raw in (None, ""):
        return 0.0
    try:
        value = float(str(raw).replace("$", "").replace(",", "").strip())
    except ValueError:
        raise ActionError("Tips have to be an amount.") from None
    if value < 0:
        raise ActionError("Tips can't be less than nothing.")
    return round(value, 2)


def _run_describe(context, params) -> str:
    """The sentence the approval card shows for `dungeon.run` (Propose); raises ActionError when it can't be done. It says the hours, hard mode, the loot (with the run's
    shift differential and tips) and the XP."""
    from core.work_dungeon import Run

    d, day, hours, affixes, boss, planned, _, tips = _run_plan(context, params)
    regular, overtime = _with(context, d, day, hours, planned.run_id if planned else "")
    hard = affix_names(affixes)
    text = f"Clear {_when(day)}'s {hours:g}-hour run at {d.name}"
    if hard:
        text += f", on hard mode ({', '.join(hard)})"
    probe = Run(run_id="__probe", dungeon_id=d.dungeon_id, date=day, hours=hours, tips=tips,
                differential=planned.differential if planned else None)
    text += _loot_words(d, regular, overtime, probe)
    return text + f"; +{run_xp(hours, affixes, boss or overtime > 0)} XP"


def _run_execute(context, params) -> str:
    """Does `dungeon.run` once approved, and says what happened. Today's planned run is cleared (else a new run added),
    with its tips; XP, credits (one per hour) and Teamwork, Organization (hard mode) and Endurance (a boss) skill XP
    are granted; the loot said includes the shift differential and tips.
    """
    from core.gamification import SkillWeight, grant_xp

    from core.work_dungeon import run_loot

    d, day, hours, affixes, boss, planned, note, tips = _run_plan(context, params)
    book = _book(context)
    if planned is not None:
        run = book.clear_run(planned.run_id, hours=hours, affixes=affixes, note=note, tips=tips or None)
    else:
        run = book.add_run(d.dungeon_id, day, hours, affixes=affixes, boss=boss, note=note, tips=tips)
    regular, overtime = split_hours(d, book.runs)[run.run_id]
    is_boss = overtime > 0 or run.boss
    xp = run_xp(run.hours, run.affixes, is_boss)
    weights = [SkillWeight("teamwork", 2)]
    if run.affixes:
        weights.append(SkillWeight("organization", 2))
    if is_boss:
        weights.append(SkillWeight("endurance", 2))
    title = "⚔ Boss down!" if is_boss else ("🔥 Hard mode cleared!" if run.affixes else "⚔ Run cleared!")
    grant_xp(context, xp, title, f"{run.hours:g} h at {d.name}.", credits=int(run.hours), skill_weights=weights)
    said = f"Run cleared: +{xp} XP"
    if d.hourly or run.tips:
        said += f", {_money(run_loot(d, run, regular, overtime))} loot"
        if overtime:
            said += f" ({_money(boss_bonus(d, overtime))} of it boss bonus)"
    return said + "."


def _plan_values(context, params):
    """What planning a run takes: the dungeon, a day not in the past, the hours, and whether it's overtime."""
    d = _dungeon(context, params)
    day = _day(params)
    if day < date.today().isoformat():
        raise ActionError("That day's gone: clear the run instead if you worked it.")
    hours = _hours(params, d)
    return d, day, hours, _flag(params.get("overtime"))


def _plan_describe(context, params) -> str:
    """The sentence the approval card shows for `dungeon.plan` (Propose); raises ActionError when it can't be done. It works out the projected loot (with that day's shift
    differential) as if the run were already on the schedule.
    """
    from core.work_dungeon import Run

    d, day, hours, boss = _plan_values(context, params)
    probe = Run(run_id="__probe", dungeon_id=d.dungeon_id, date=day, hours=hours, status="planned", created_at="9999")
    regular, overtime = split_hours(d, _book(context).runs + [probe], include_planned=True)["__probe"]
    kind = "an overtime boss" if boss or overtime else "a run"
    return f"Plan {kind} at {d.name} {_when(day)}: {hours:g} hours" + _loot_words(d, regular, overtime, probe).replace(
        " loot", " projected loot")


def _plan_execute(context, params) -> str:
    """Does `dungeon.plan` once approved, and says what happened."""
    d, day, hours, boss = _plan_values(context, params)
    _book(context).add_run(d.dungeon_id, day, hours, status="planned", boss=boss)
    return "On the schedule."


def _tips_describe(context, params) -> str:
    """The sentence the approval card shows for `dungeon.tips`: the run, and its tips before and after."""
    run = _run_of(context, params)
    tips = _tips_of(params)
    before = f" (was {_money(run.tips)})" if run.tips else ""
    return f"Tips for {run.date}'s run: {_money(tips)}{before}"


def _tips_execute(context, params) -> str:
    """Does `dungeon.tips`: the run's tips, counted after the shift, and its loot with them."""
    from core.work_dungeon import run_loot

    run = _run_of(context, params)
    book = _book(context)
    try:
        book.set_tips(run.run_id, _tips_of(params))
    except ValueError as problem:
        raise ActionError(str(problem)) from None
    d = book.get_dungeon(run.dungeon_id)
    regular, overtime = split_hours(d, book.runs, include_planned=True).get(run.run_id, (run.hours, 0.0))
    return f"Tips kept: {_money(run.tips)}. That run's loot is {_money(run_loot(d, run, regular, overtime))}."


def _run_of(context, params):
    """The run the params name, or ActionError."""
    run = _book(context).get_run(str(params.get("run_id") or ""))
    if run is None:
        raise ActionError("That run isn't there anymore.")
    return run


def _delete_describe(context, params) -> str:
    """The sentence the approval card shows for `dungeon.run_delete` (Propose); raises ActionError when it can't be done. The XP a cleared run earned stays."""
    run = _run_of(context, params)
    d = _book(context).get_dungeon(run.dungeon_id)
    kind = "planned run" if run.status == "planned" else "run"
    return f"Take back the {run.hours:g}-hour {kind} at {d.name if d else 'work'} on {run.date}" + (
        " (the XP it earned stays)" if run.status == "cleared" else "")


def _delete_execute(context, params) -> str:
    """Does `dungeon.run_delete` once approved, and says what happened."""
    _book(context).delete_run(_run_of(context, params).run_id)
    return "Taken back."


# ---------------------------------------------------------------- the Game Master's quest


def _quest_values(context, params):
    """A quest made from a challenge: a known hard-mode modifier (its name, line and XP) or the person's own words
    (a side quest), the goal, and the reward (25 XP plus the modifier's).
    """
    raw = str(params.get("challenge") or "").strip()
    if not raw:
        raise ActionError("Which challenge should become the quest?")
    affix_id = parse_affixes(raw)[0]
    a = AFFIX_BY_ID.get(affix_id)
    name = f"Hard Mode: {a.name}" if a else f"Side Quest: {raw[:50].rstrip('.')}"
    summary = a.line if a else f"The Game Master's quest: {raw}."
    goal = str(params.get("goal") or "").strip() or (
        "Clear the run on hard mode" if a else "Clear it")
    xp = 25 + (a.xp if a else 5)
    return name, summary, goal, xp, a


def _quest_describe(context, params) -> str:
    """The sentence the approval card shows for `dungeon.quest` (Propose); raises ActionError when it can't be done."""
    name, summary, goal, xp, _ = _quest_values(context, params)
    return f"A new quest, “{name}”: {goal.lower()}. Reward +{xp} XP"


def _quest_execute(context, params) -> str:
    """Does `dungeon.quest` once approved, and says what happened. It's a hard side-quest mission MIA assigns, with one objective and its
    reward.
    """
    from core.gamification import SkillWeight

    name, summary, goal, xp, a = _quest_values(context, params)
    missions = _need(context, "missions")
    m = missions.add_mission(name, assigned_by="mia", icon="⚔", summary=summary, difficulty="HARD",
                             mission_type="SIDE QUEST", reward_xp=xp, reward_credits=10,
                             skill_rewards=[SkillWeight("organization" if a else "problem_solving", 3)])
    missions.add_objective(m.mission_id, goal, "tally", 1)
    return f"Quest accepted: {name}. +{xp} XP when it's cleared (Missions)."


def _register() -> None:
    """Adds the dungeon record kinds and the run, plan, take-back, tips and quest kinds to ACTION_TYPES. Runs once, when
    this module is imported.
    """
    kinds = list(record_kinds(DUNGEON)) + [
        ActionType("dungeon.run", "Clear A Run", {"dungeon_id": "the dungeon", "date": "the day (blank: today)",
                                                 "hours": "hours worked", "hard_mode": "what made it hard",
                                                 "overtime": "a called-in overtime shift", "note": "a note",
                                                 "tips": "tips taken (optional)"},
                   _run_describe, _run_execute),
        ActionType("dungeon.plan", "Plan A Run", {"dungeon_id": "the dungeon", "date": "the day", "hours": "hours",
                                                 "overtime": "an overtime shift"}, _plan_describe, _plan_execute),
        ActionType("dungeon.run_delete", "Take Back", {"run_id": "the run"}, _delete_describe, _delete_execute),
        ActionType("dungeon.tips", "Add Tips", {"run_id": "the run", "tips": "the tips taken"},
                   _tips_describe, _tips_execute),
        ActionType("dungeon.quest", "Make It A Quest", {"challenge": "the hard-mode modifier, or the challenge in words",
                                                        "goal": "what clearing it means"},
                   _quest_describe, _quest_execute),
    ]
    for k in kinds:
        ACTION_TYPES[k.kind] = k


_register()
