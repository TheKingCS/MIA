"""
core.game_master
==================

MIA as Game Master (DEC-0046): the real day's trouble, reframed as the
game the person is playing, without pretending the trouble isn't real.

The model only phrases it. What the game calls the trouble (the
hard-mode modifiers in core/work_dungeon.py), how often it's happened,
the day's run, the loot and the next dungeon all come from code here, so
she never invents a number, an XP reward or a win. Other people are part
of the world (the stage preparers, the party), never villains and never
named; the instruction says so.

Switched on like any mode ("GM this", "game master", "make it a game"),
or picked when MIA asks what kind of support someone wants
(core/support_choice.py).
"""

from __future__ import annotations

from datetime import date
from typing import Optional

INSTRUCTION = (
    "You're the user's Game Master: you turn what's happening in their real life into the game they're playing. "
    "First, in one short sentence, say plainly that what happened is real and frustrating; never pretend it isn't. "
    "Then reframe it as the game using ONLY the game facts below: give the hard-mode modifier its game name, say "
    "what clearing it earns, and offer one quest they could take on (they say \"make it a quest\" to accept). "
    "Other people are characters in the world (the stage preparers, the party), never villains to mock, and "
    "never named. Never invent loot, money, hours, XP, dates or wins. Four sentences at most."
)

NOT_SET_UP = ("Their work dungeon isn't set up in MIA yet (Apps → The Dungeon: the job and its pay), so there are "
              "no loot numbers: frame it without any, and mention they can set it up.")


def _recent_user_text(conversation, prompt: str, turns: int = 3) -> str:
    said = [prompt]
    if conversation is not None:
        said += [m.content for m in reversed(conversation.messages or []) if m.role == "user"][:turns]
    return " ".join(str(s or "") for s in said)


def game_facts(context, prompt: str = "", conversation=None, today: Optional[date] = None) -> str:
    """The facts block for a Game Master turn, as plain lines."""
    from core.child_accounts import is_child
    from core.work_dungeon import AFFIX_BY_ID, detect_affixes

    today = today or date.today()
    lines: list[str] = []
    found = detect_affixes(_recent_user_text(conversation, prompt))
    for affix_id in found:
        a = AFFIX_BY_ID[affix_id]
        lines.append(f"- Hard mode today: {a.name} (in plain words: {a.real}). The framing: {a.line} "
                     f"Clearing a run with it: +{a.xp} XP on top of the run's own.")
    if not found:
        lines.append("- No known hard-mode modifier in what they said: name the challenge from their own words.")

    book = getattr(context, "dungeon", None)
    if book is None or not book.dungeons or is_child(context):
        lines.append("- " + NOT_SET_UP if not is_child(context) else "- Keep it about the challenge; no money.")
        return "The game facts:\n" + "\n".join(lines)

    from core.web_dungeon import dungeon_view, next_dungeon

    view = dungeon_view(context, book.dungeons[0], book.runs, today)
    name = view["name"]
    for x in view["hard_mode"]:
        if x["id"] in found and x["this_month"]:
            lines.append(f"- Runs at {name} with {x['name']} this month so far: {x['this_month']} "
                         f"(the dates are kept in The Dungeon's hard-mode record).")
    run = view["today"]
    if run and run["status"] == "cleared":
        lines.append(f"- Today's run at {name}: cleared, {run['hours']:g} hours" +
                     (f", {run['loot_text']} loot" if run["loot_text"] else "") + ".")
    elif run:
        lines.append(f"- Today's run at {name}: planned, {run['hours']:g} hours" +
                     (f", about {run['loot_text']} loot" if run["loot_text"] else "") + ". Not cleared yet.")
    else:
        lines.append(f"- No run at {name} logged today.")
    if view["set_up"]:
        week = view["week"]
        lines.append(f"- Loot this week so far: {week['earned_text']} ({week['hours']:g} hours)"
                     + (f"; projected with the planned runs: {week['projected_text']}" if week["projected"] != week["earned"]
                        else "") + ".")
        ot = view["overtime_now"]
        if ot["hour_text"]:
            if ot["in_overtime"]:
                lines.append(f"- They're in overtime this week: every hour is boss loot, {ot['hour_text']} an hour.")
            elif ot["hours_to_overtime"] is not None:
                lines.append(f"- Overtime (boss loot, {ot['hour_text']} an hour) starts after "
                             f"{ot['hours_to_overtime']:g} more hours this week.")
    nxt = next_dungeon(context, view, today)
    if nxt and nxt.get("ready"):
        line = f"- The next dungeon (their Freedom plan): {nxt['progress_pct']:g}% unlocked, {nxt['left_text']} to go"
        if nxt.get("run_text"):
            line += f"; one usual run moves it {nxt['run_text']} ({nxt['run_basis']})"
        lines.append(line + ".")
    return "The game facts:\n" + "\n".join(lines)
