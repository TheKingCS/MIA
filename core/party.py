"""
core.party
============

Party and guild (DEC-0028, the game layer's tenth idea; Zac, 2026-10-17):
the household plays together.

- **Raids** are co-op household missions (a spring-cleaning raid): a
  group quest (core/mission_manager.py's `participant_profile_ids`) with
  its objectives shared out between the people who join, round the
  table. Everyone in it gets the same reward when it's done. MIA has a
  few starters; anyone can write their own.
- **The leaderboard** is opt-in, per person (`party.leaderboard` in
  core/person_settings.py). Only people who switched it on are on it,
  and it counts wins this week (things done, never money, never what
  wasn't done) so it cheers rather than shames (DEC-0014).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

RAID_XP = 100


@dataclass(frozen=True)
class Raid:
    raid_id: str
    name: str
    icon: str
    summary: str
    objectives: tuple[str, ...]


RAIDS: tuple[Raid, ...] = (
    Raid("spring_cleaning", "Spring-Cleaning Raid", "🧹", "Everyone takes a room. Meet in the middle.",
         ("Kitchen deep clean", "Bathroom deep clean", "Living room reset", "Windows and mirrors", "Clear out a closet",
          "Take the donations out")),
    Raid("yard_day", "Yard Day Raid", "🌿", "Many hands make the yard look great.",
         ("Mow", "Weed the beds", "Trim the edges", "Rake or blow the leaves", "Haul the yard waste")),
    Raid("garage", "Garage Raid", "🔧", "Take back the garage together.",
         ("Pull everything out", "Sort keep / donate / toss", "Sweep the floor", "Put it back where it belongs")),
    Raid("kitchen_reset", "Kitchen Reset Raid", "🍽️", "A fresh kitchen in one push.",
         ("Clean out the fridge", "Wipe the cupboards", "Sort the pantry", "Scrub the stove", "Take out the trash and recycling")),
    Raid("game_night", "Game Night Prep", "🎲", "Set up a night in, together.",
         ("Pick the games", "Make the snacks", "Set up the table", "Invite someone")),
)
RAID_BY_ID = {r.raid_id: r for r in RAIDS}


def share_out(objectives: list[str], people: list[str]) -> list[tuple[str, str]]:
    """Pure logic. Each objective to a person, round the table."""
    if not people:
        return []
    return [(o, people[i % len(people)]) for i, o in enumerate(objectives)]


def week_of(day: date) -> tuple[date, date]:
    monday = day - timedelta(days=day.weekday())
    return monday, monday + timedelta(days=6)


# ------------------------------------------------------------------ the household


def _me(context) -> Optional[str]:
    from core.person_settings import person_id

    return person_id(context)


def members(context) -> list:
    """Everyone in my household (me first)."""
    profiles = getattr(context, "profiles", None)
    if profiles is None:
        return []
    me = _me(context)
    households = getattr(context, "households", None)
    people = profiles.list_profiles()
    if households is not None and me:
        hid = households.household_of(me)
        people = households.members(hid) if hid else people
    return sorted(people, key=lambda p: (p.profile_id != me, (p.name or "").lower()))


def opted_in(context, profile_id: str) -> bool:
    config = getattr(context, "config", None)
    record = (config.get(f"profiles.{profile_id}") or {}) if config is not None else {}
    return bool((record.get("settings") or {}).get("party.leaderboard"))


def start_raid(context, name: str, icon: str, summary: str, objectives: list[str], people: list[str]):
    """A household raid: one group mission, objectives shared out."""
    missions = context.missions
    mission = missions.add_mission(name=name, icon=icon or "⚔️", summary=summary, mission_type="HOUSEHOLD RAID",
                                   region="Household", reward_xp=RAID_XP, profile_id=None,
                                   participant_profile_ids=list(people))
    for objective, who in share_out(objectives, people):
        missions.add_objective(mission.mission_id, objective, "tally", 1.0, assigned_profile_id=who)
    return missions.get_mission(mission.mission_id)


def _wins(context, people: list, since: date, until: date) -> dict[str, int]:
    """Wins this week per person: the household's history (stamped with
    who did it) plus each person's own (workouts and the like). Never
    money, never what wasn't done."""
    from core.life_events import MONEY_TYPES, WINS, LifeEventLog

    counted: dict[str, int] = {p.profile_id: 0 for p in people}
    seen: set[str] = set()
    from core.life_events import folder_of

    logs = [getattr(context, "life_events", None)]
    missions = getattr(context, "missions", None)
    if missions is not None:  # Missions are the device's; their history is where the store keeps it
        logs.append(LifeEventLog(context, folder_of(missions)))
    try:
        from core.personal_data import _profiles_dir

        logs += [LifeEventLog(context, _profiles_dir() / p.profile_id) for p in people]
    except Exception:
        pass
    wins = set(WINS) | {"questline_finished", "explored", "caught_up", "skill_practice", "training_done"}
    for log_ in logs:
        if log_ is None:
            continue
        for event in log_.all_events():
            if event.event_id in seen or event.type not in wins or event.type in MONEY_TYPES:
                continue
            if not (since.isoformat() <= event.day <= until.isoformat()):
                continue
            seen.add(event.event_id)
            if event.profile_id in counted:
                counted[event.profile_id] += 1
    return counted


def party_page(context, today: Optional[date] = None) -> dict:
    """Missions → Party: the household, raids going and to start, and
    the opt-in leaderboard."""
    from core.mission_actions import is_mine
    from core.web_progress import level_block

    today = today or date.today()
    me = _me(context)
    people = members(context)
    names = {p.profile_id: p.name for p in people}
    missions = getattr(context, "missions", None)
    raids = []
    if missions is not None:
        for m in missions.all_missions():
            if m.mission_type != "HOUSEHOLD RAID" or not is_mine(m, me):
                continue
            if m.status != "active" and (m.updated_at or "")[:10] < (today - timedelta(days=30)).isoformat():
                continue
            done, total = missions.group_objective_progress(m.mission_id)
            crew = []
            for pid in m.participant_profile_ids:
                mine_done, mine_total = missions.individual_objective_progress(m.mission_id, pid)
                crew.append({"name": names.get(pid, "someone"), "me": pid == me, "done": mine_done, "total": mine_total})
            raids.append({"id": m.mission_id, "name": m.name, "icon": m.icon, "summary": m.summary, "status": m.status,
                          "done": done, "total": total, "percent": round(100 * done / total) if total else 0,
                          "ready": bool(total) and done == total and m.status == "active", "crew": crew,
                          "objectives": [{"index": i, "description": o.description,
                                          "for": names.get(o.assigned_profile_id, "anyone"),
                                          "mine": o.assigned_profile_id in (None, me),
                                          "done": (missions.objective_progress(m.mission_id, i) or 0) >= o.target}
                                         for i, o in enumerate(m.objectives)],
                          "reward": f"+{m.reward_xp} XP each" if m.reward_xp else ""})
    monday, sunday = week_of(today)
    board_people = [p for p in people if opted_in(context, p.profile_id)]
    wins = _wins(context, board_people, monday, sunday) if board_people else {}
    board = sorted(({"name": p.name, "me": p.profile_id == me, "wins": wins.get(p.profile_id, 0),
                     "level": level_block(p)["level"]} for p in board_people),
                   key=lambda r: (-r["wins"], r["name"].lower()))
    for i, row in enumerate(board):
        row["medal"] = ("🥇", "🥈", "🥉")[i] if len(board) >= 3 and i < 3 and row["wins"] else ""
    return {
        "available": missions is not None,
        "household": [{"id": p.profile_id, "name": p.name, "me": p.profile_id == me, "level": level_block(p)["level"],
                       "on_board": opted_in(context, p.profile_id)} for p in people],
        "raids": sorted(raids, key=lambda r: (r["status"] != "active", not r["ready"], r["name"])),
        "starters": [{"id": r.raid_id, "name": r.name, "icon": r.icon, "summary": r.summary,
                      "objectives": list(r.objectives)} for r in RAIDS],
        "leaderboard": {"on": bool(me) and opted_in(context, me), "week": [monday.isoformat(), sunday.isoformat()],
                        "rows": board},
        "picks": {"people": [{"id": p.profile_id, "name": p.name} for p in people]},
    }
