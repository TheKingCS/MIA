"""
core.questlines
=================

Questlines and seasons (DEC-0028, the game layer's seventh idea; Zac,
2026-10-17): linked chapters ("Harvest Home: Ch. 1 Bring it in → Ch. 2
Put it up → Ch. 3 Put the beds to bed"), seasonal starters, and MIA as
the quest-giver and narrator.

- A **questline** is an ordered list of chapters. Only the current
  chapter is a real mission (core/mission_manager.py, `assigned_by="mia"`),
  so it shows on Missions, counts its objectives and gives its rewards
  like any other. Finishing it opens the next chapter with MIA's line
  for it; finishing the last one finishes the questline (+ its credits,
  given with the last chapter's mission).
- **Seasons** follow the date and the person's hemisphere (their
  country, core/region.py). Each season offers its own starters; one
  started stays yours after the season ends. No countdowns, nothing
  lost (the guardrails in docs/GAME_LAYER.md).
- Starters are generic (never one person's names, places or things);
  some only show when MIA has something to hang them on (a greenhouse,
  vehicles). A person can also write their own: one chapter per line,
  "Title: objective; objective".

`QuestBook` is each person's own (a personal store). It writes through
atomic_write_text, so starting or removing a questline can be undone.
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from core.atomic_write import atomic_write_text
from core.data_recovery import notify_data_corruption
from core.logger import get_logger

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_FILE = "questlines.json"

SEASONS = ("Winter", "Spring", "Summer", "Fall")
SEASON_ICONS = {"Winter": "❄️", "Spring": "🌱", "Summer": "☀️", "Fall": "🍂"}
# Countries south of the equator: their seasons are the other way round.
SOUTHERN = frozenset({"AU", "NZ", "ZA", "AR", "CL", "UY", "PY", "BR", "PE", "BO", "NA", "BW", "ZW", "MZ", "MG",
                      "LS", "SZ", "FJ", "PG"})
CHAPTER_XP = (50, 75, 100, 125, 150)
FINISH_CREDITS = 100


def season_of(day: date, country: str = "") -> str:
    """Pure logic. Meteorological seasons (Dec–Feb is Winter up north,
    Summer down south)."""
    index = (day.month % 12) // 3  # Dec/Jan/Feb 0, Mar–May 1, Jun–Aug 2, Sep–Nov 3
    if (country or "").upper() in SOUTHERN:
        index = (index + 2) % 4
    return SEASONS[index]


def season_span(day: date, country: str = "") -> tuple[date, date]:
    """Pure logic. The first and last day of the season `day` is in."""
    start_month = day.month - ((day.month % 12) % 3)
    year = day.year
    if start_month <= 0:
        start_month += 12
        year -= 1
    start = date(year, start_month, 1)
    end_month, end_year = start_month + 3, year
    if end_month > 12:
        end_month -= 12
        end_year += 1
    from datetime import timedelta

    return start, date(end_year, end_month, 1) - timedelta(days=1)


def season_id(day: date, country: str = "") -> str:
    """Pure logic. "Fall 2026" (a Dec–Feb season takes the year it starts)."""
    return f"{season_of(day, country)} {season_span(day, country)[0].year}"


# ------------------------------------------------------------------ starters

@dataclass(frozen=True)
class Starter:
    starter_id: str
    name: str
    icon: str
    season: str  # one of SEASONS, or "" for any time of year
    summary: str
    # (title, MIA's line when it opens, objectives): an objective is
    # "text" or "text|target".
    chapters: tuple[tuple[str, str, tuple[str, ...]], ...]
    needs: str = ""  # "greenhouse" | "vehicles" | "" (always)


STARTERS: tuple[Starter, ...] = (
    Starter("homestead_spring", "Homestead Spring", "🌱", "Spring", "Get the garden going from bare beds to the first harvest.", (
        ("Prep The Beds", "Every harvest starts with dirt under your nails. Let's wake the beds up.",
         ("Clear out the old growth", "Add compost or fresh soil", "Plan what goes where")),
        ("Plant", "The beds are ready. Time to put something in them.", ("Start seeds or buy starts", "Plant them out", "Water them in")),
        ("First Harvest", "Something you planted is ready. Go get it.", ("Pick your first harvest", "Cook or share something you grew")),
    ), needs="greenhouse"),
    Starter("spring_cleaning", "Spring Cleaning", "🧹", "Spring", "A fresh start for the house, one room at a time.", (
        ("Declutter", "Before cleaning, lighten the load.", ("Clear out one closet or drawer", "Bag up what you don't use")),
        ("Deep Clean", "Now the part that makes it shine.", ("Deep clean the kitchen", "Deep clean the bathroom", "Wash the windows")),
        ("Let It Go", "Last step: get it out the door.", ("Donate, sell or recycle the pile",)),
    )),
    Starter("spring_tune_up", "Spring Tune-Up", "🔧", "Spring", "Get your vehicles and gear ready for the warm months.", (
        ("Inspect", "Winter's over. Let's see what it left behind.", ("Check the tires", "Check the fluids", "Wash off the winter grime")),
        ("Service", "Fix what the inspection found.", ("Do any service that's due", "Log it in Maintenance")),
    ), needs="vehicles"),
    Starter("summer_adventure", "Summer Adventure", "🏕️", "Summer", "Plan it, go, and bring the story home.", (
        ("Plan It", "Somewhere you've been meaning to go. Pick it.", ("Pick a place", "Pick a day", "Pack the gear")),
        ("Go", "Today's the day. Go see it.", ("Get out there",)),
        ("Tell The Story", "Every adventure deserves its story.", ("Write about it in your journal", "Save a few photos")),
    )),
    Starter("summer_strong", "Summer Strong", "💪", "Summer", "Use the long days to build a habit that lasts.", (
        ("Show Up", "Strength starts with just showing up.", ("Work out|3",)),
        ("Keep Going", "You've started. Now it's a habit.", ("Work out|6",)),
        ("Go Further", "Push one thing past where you were.", ("Set a new personal best",)),
    )),
    Starter("harvest_home", "Harvest Home", "🧺", "Fall", "Bring the garden in and get it ready for next year.", (
        ("Bring It In", "The garden's been working all year. Time to collect.", ("Harvest what's ready", "Weigh or count it")),
        ("Put It Up", "Make it last into winter.", ("Preserve, freeze or dry some of it",)),
        ("Put The Beds To Bed", "Tuck the beds in so spring starts easy.", ("Clear the spent plants", "Mulch or cover the beds")),
    ), needs="greenhouse"),
    Starter("ready_for_winter", "Ready For Winter", "🏠", "Fall", "Get the house and the car ready before the cold sets in.", (
        ("Check The House", "Cold's coming. Let's make sure the house is ready.", ("Test the heating", "Change the furnace filter", "Test the smoke and CO alarms")),
        ("Seal It Up", "Keep the warm in.", ("Seal drafty doors or windows", "Clean the gutters")),
        ("Winter Kit", "Last thing: be ready on the road.", ("Put a winter kit in the car",)),
    )),
    Starter("winter_workshop", "Winter Workshop", "🪚", "Winter", "Make something with your hands while it's cold out.", (
        ("Plan A Build", "Every build starts on paper.", ("Pick something to make", "List what you need")),
        ("Build It", "Sawdust time.", ("Finish the build",)),
        ("Show It Off", "You made that. Show someone.", ("Take a photo of it", "Show it to someone")),
    )),
    Starter("cozy_kitchen", "Cozy Kitchen", "🍲", "Winter", "Warm food, new recipes, and people to share them with.", (
        ("Something New", "Let's try something you've never cooked.", ("Cook a recipe you've never made",)),
        ("Cook For Someone", "Food tastes better shared.", ("Cook a meal for someone else",)),
        ("Batch It", "Future you will thank you.", ("Batch cook for the week",)),
    )),
    Starter("year_in_review", "Year In Review", "📜", "Winter", "Look back at your year and pick where the next one goes.", (
        ("Read Your Story", "You've done more this year than you remember. Let's look.", ("Read your year in the Chronicle",)),
        ("Reflect", "What mattered most?", ("Write a reflection in your journal",)),
        ("Next Year's Quest", "Pick one thing to aim at next.", ("Add a mission for next year",)),
    )),
    Starter("new_skill", "Learn Something New", "🎓", "", "Pick up a skill from scratch and stick with it.", (
        ("Pick It", "What have you always wanted to be able to do?", ("Pick a skill to learn", "Find one good way to learn it")),
        ("Practice", "Little and often beats once and done.", ("Practice it|5",)),
        ("Show It", "Prove it to yourself.", ("Do it in front of someone, or make something with it",)),
    )),
    Starter("closer_to_people", "Closer To People", "🤝", "", "Make time for the people who matter.", (
        ("Reach Out", "Someone would love to hear from you.", ("Message someone you haven't talked to in a while|2",)),
        ("Get Together", "Better in person.", ("Spend time with a friend or family member",)),
        ("Do Something Kind", "Small things count.", ("Do something nice for someone, just because",)),
    )),
)
STARTER_BY_ID = {s.starter_id: s for s in STARTERS}


def parse_objective(text: str) -> tuple[str, float]:
    """Pure logic. "Work out|3" -> ("Work out", 3.0); "Plant" -> ("Plant", 1.0)."""
    words, _, target = str(text).partition("|")
    try:
        number = max(1.0, float(target)) if target.strip() else 1.0
    except ValueError:
        number = 1.0
    return words.strip(), number


def parse_chapters(text: str) -> list[dict]:
    """Pure logic. A person's own questline, one chapter per line:
    "Prep the beds: clear them; add compost" -> a chapter titled "Prep The
    Beds" with two objectives. A line without objectives is its own one."""
    chapters = []
    for raw in str(text or "").splitlines():
        line = raw.strip().lstrip("-•*0123456789.) ").strip()
        if not line:
            continue
        title, _, rest = line.partition(":")
        objectives = [o.strip() for o in re.split(r"[;,]", rest) if o.strip()] if rest.strip() else [title.strip()]
        chapters.append({"title": title.strip().title() if title.strip().islower() else title.strip(),
                         "story": "", "objectives": objectives})
    return chapters


# ------------------------------------------------------------------ the store

@dataclass
class Chapter:
    title: str
    story: str = ""
    objectives: list[str] = field(default_factory=list)
    mission_id: Optional[str] = None
    done_on: str = ""

    @staticmethod
    def from_dict(data: dict) -> "Chapter":
        return Chapter(title=str(data.get("title") or "Chapter"), story=str(data.get("story") or ""),
                       objectives=[str(o) for o in data.get("objectives") or []],
                       mission_id=data.get("mission_id") or None, done_on=str(data.get("done_on") or ""))


@dataclass
class Questline:
    quest_id: str
    name: str
    icon: str = "🗺️"
    summary: str = ""
    season: str = ""  # "Fall 2026" for a seasonal starter, "" otherwise
    starter_id: str = ""
    chapters: list[Chapter] = field(default_factory=list)
    started_on: str = ""
    finished_on: str = ""

    @property
    def current(self) -> int:
        """The index of the chapter being played (len(chapters) once finished)."""
        return next((i for i, c in enumerate(self.chapters) if not c.done_on), len(self.chapters))

    @property
    def finished(self) -> bool:
        return bool(self.finished_on)

    @staticmethod
    def from_dict(data: dict) -> "Questline":
        return Questline(quest_id=str(data["quest_id"]), name=str(data.get("name") or "Questline"),
                         icon=str(data.get("icon") or "🗺️"), summary=str(data.get("summary") or ""),
                         season=str(data.get("season") or ""), starter_id=str(data.get("starter_id") or ""),
                         chapters=[Chapter.from_dict(c) for c in data.get("chapters") or []],
                         started_on=str(data.get("started_on") or ""), finished_on=str(data.get("finished_on") or ""))


class QuestBook:
    def __init__(self, context, data_dir: Optional[Path] = None) -> None:
        self.context = context
        self.data_dir = Path(data_dir) if data_dir is not None else _DATA_DIR
        self._file = self.data_dir / _FILE
        self.quests: list[Questline] = []
        self._load()

    def _load(self) -> None:
        self.quests = []
        if not self._file.exists():
            return
        try:
            raw = json.loads(self._file.read_text(encoding="utf-8"))
            self.quests = [Questline.from_dict(q) for q in raw.get("quests") or []]
        except (json.JSONDecodeError, OSError, TypeError, ValueError, KeyError, AttributeError):
            log.exception("questlines.json unreadable — starting empty.")
            notify_data_corruption(self.context, _FILE)

    def reload(self) -> None:
        self._load()

    def _save(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._file, json.dumps({"quests": [asdict(q) for q in self.quests]}, indent=2,
                                                 ensure_ascii=False))

    def get(self, quest_id: str) -> Optional[Questline]:
        return next((q for q in self.quests if q.quest_id == quest_id), None)

    def add(self, name: str, chapters: list[dict], icon: str = "🗺️", summary: str = "", season: str = "",
            starter_id: str = "") -> Questline:
        quest = Questline(quest_id=uuid.uuid4().hex[:10], name=name, icon=icon or "🗺️", summary=summary,
                          season=season, starter_id=starter_id,
                          chapters=[Chapter(title=c["title"], story=c.get("story", ""), objectives=list(c["objectives"]))
                                    for c in chapters],
                          started_on=date.today().isoformat())
        self.quests.append(quest)
        self._save()
        return quest

    def remove(self, quest_id: str) -> None:
        self.quests = [q for q in self.quests if q.quest_id != quest_id]
        self._save()

    def save(self) -> None:
        self._save()


# ------------------------------------------------------------------ playing it


def _person(context):
    from core.person_settings import person_id

    return person_id(context)


def open_chapter(context, quest: Questline) -> Optional[object]:
    """Make the current chapter's mission (once). The last chapter also
    carries the questline's finishing credits."""
    index = quest.current
    if index >= len(quest.chapters):
        return None
    chapter = quest.chapters[index]
    missions = getattr(context, "missions", None)
    if missions is None:
        return None
    if chapter.mission_id and missions.get_mission(chapter.mission_id) is not None:
        return missions.get_mission(chapter.mission_id)
    last = index == len(quest.chapters) - 1
    mission = missions.add_mission(
        name=f"{quest.name}: {chapter.title}", assigned_by="mia", icon=quest.icon,
        summary=chapter.story or quest.summary, mission_type=f"QUEST · CH. {index + 1} OF {len(quest.chapters)}",
        region=quest.season or "Questline", reward_xp=CHAPTER_XP[min(index, len(CHAPTER_XP) - 1)],
        reward_credits=FINISH_CREDITS if last else 0, profile_id=_person(context))
    for objective in chapter.objectives:
        text, target = parse_objective(objective)
        missions.add_objective(mission.mission_id, text, "tally", target)
    chapter.mission_id = mission.mission_id
    context.quest_book.save()
    return mission


def advance(context, today: Optional[date] = None) -> list[str]:
    """Move every questline whose current chapter's mission is complete
    on to the next chapter. Returns what MIA says about it ("Chapter 2:
    Plant. The beds are ready…"), one line per step."""
    from core import life_events

    book = getattr(context, "quest_book", None)
    missions = getattr(context, "missions", None)
    if book is None or missions is None:
        return []
    today = today or date.today()
    said: list[str] = []
    for quest in book.quests:
        while not quest.finished:
            index = quest.current
            if index >= len(quest.chapters):
                quest.finished_on = today.isoformat()
                break
            chapter = quest.chapters[index]
            mission = missions.get_mission(chapter.mission_id) if chapter.mission_id else None
            if mission is None:
                open_chapter(context, quest)
                break
            if mission.status != "completed":
                break
            chapter.done_on = today.isoformat()
            if quest.current >= len(quest.chapters):
                quest.finished_on = today.isoformat()
                book.save()
                life_events.record(book, "questline_finished", f"Finished the questline {quest.name}",
                                   [f"quest:{quest.quest_id}"], {"chapters": len(quest.chapters)})
                said.append(f"{quest.icon} {quest.name} is complete: every chapter done. +{FINISH_CREDITS} credits.")
                break
            nxt = quest.chapters[quest.current]
            open_chapter(context, quest)
            said.append(f"{quest.icon} {quest.name}, Chapter {quest.current + 1}: {nxt.title}."
                        + (f" {nxt.story}" if nxt.story else ""))
        book.save() if said else None
    return said


def available(context, today: Optional[date] = None) -> list[Starter]:
    """The starters to offer now: this season's and the any-time ones,
    minus those the person is already playing this season, minus those
    MIA has nothing to hang on."""
    from core.region import country_of

    today = today or date.today()
    country = country_of(context) if getattr(context, "config", None) is not None else ""
    season = season_of(today, country)
    sid = season_id(today, country)
    book = getattr(context, "quest_book", None)
    playing = {(q.starter_id, q.season) for q in book.quests} if book is not None else set()
    started_any = {q.starter_id for q in book.quests if not q.finished} if book is not None else set()
    out = []
    for s in STARTERS:
        if s.season not in ("", season):
            continue
        if (s.starter_id, sid if s.season else "") in playing or s.starter_id in started_any:
            continue
        if s.needs and not _has(context, s.needs):
            continue
        out.append(s)
    return out


def _has(context, need: str) -> bool:
    try:
        if need == "greenhouse":
            grow = getattr(context, "grow_lab", None)
            if grow is not None and grow.batches:
                return True
            m = getattr(context, "maintenance", None)
            return m is not None and any(a.category == "Garden/Plant" for a in m.all_assets())
        if need == "vehicles":
            m = getattr(context, "maintenance", None)
            return m is not None and any(a.category == "Vehicle" for a in m.all_assets())
    except Exception:
        log.exception("questlines: couldn't check %s", need)
    return False


def start(context, starter_id: str, today: Optional[date] = None) -> Questline:
    from core.region import country_of

    starter = STARTER_BY_ID.get(starter_id)
    if starter is None:
        raise ValueError("That questline isn't one MIA knows.")
    today = today or date.today()
    country = country_of(context) if getattr(context, "config", None) is not None else ""
    quest = context.quest_book.add(
        starter.name, [{"title": t, "story": s, "objectives": list(o)} for t, s, o in starter.chapters],
        icon=starter.icon, summary=starter.summary, season=season_id(today, country) if starter.season else "",
        starter_id=starter.starter_id)
    open_chapter(context, quest)
    return quest


def season_note(context, today: Optional[date] = None) -> Optional[tuple[str, str, str]]:
    """MIA as quest-giver: (title, message, fingerprint) once a season,
    when it has starters to offer. None when there's nothing new."""
    from core.region import country_of

    today = today or date.today()
    country = country_of(context) if getattr(context, "config", None) is not None else ""
    offers = available(context, today)
    seasonal = [s for s in offers if s.season]
    if not seasonal:
        return None
    season = season_of(today, country)
    names = ", ".join(s.name for s in seasonal[:3])
    return (f"{SEASON_ICONS[season]} {season} questlines are here",
            f"{season} is here, and I have {len(seasonal)} {'questline' if len(seasonal) == 1 else 'questlines'} "
            f"for it: {names}. Start one from Missions → Quests whenever you like.",
            f"season:{season_id(today, country)}")


def quests_section(context, today: Optional[date] = None) -> dict:
    """Missions → Quests: the season, the questlines being played (each
    chapter done, current or still to come), what's on offer, and the
    finished ones."""
    from core.region import country_of

    today = today or date.today()
    advance(context, today)
    country = country_of(context) if getattr(context, "config", None) is not None else ""
    season = season_of(today, country)
    start_day, end_day = season_span(today, country)
    book = getattr(context, "quest_book", None)
    missions = getattr(context, "missions", None)

    def card(q: Questline) -> dict:
        chapters = []
        for i, c in enumerate(q.chapters):
            m = missions.get_mission(c.mission_id) if missions is not None and c.mission_id else None
            done, total = missions.group_objective_progress(m.mission_id) if m is not None else (0, len(c.objectives))
            state = "done" if c.done_on else ("current" if i == q.current else "locked")
            chapters.append({"index": i, "title": c.title, "story": c.story if state != "locked" else "",
                             "state": state, "mission_id": m.mission_id if m is not None else None,
                             "done": done, "total": total, "done_on": c.done_on,
                             "objectives": c.objectives if state != "locked" else []})
        return {"id": q.quest_id, "name": q.name, "icon": q.icon, "summary": q.summary, "season": q.season,
                "chapters": chapters, "current": q.current, "count": len(q.chapters),
                "percent": round(100 * sum(1 for c in q.chapters if c.done_on) / len(q.chapters)) if q.chapters else 0,
                "finished": q.finished, "finished_on": q.finished_on, "started_on": q.started_on,
                "reward": f"+{FINISH_CREDITS} credits at the end"}

    quests = book.quests if book is not None else []
    return {
        "available": book is not None,
        "season": {"name": season, "icon": SEASON_ICONS[season], "id": season_id(today, country),
                   "from": start_day.isoformat(), "to": end_day.isoformat()},
        "active": [card(q) for q in quests if not q.finished],
        "finished": sorted((card(q) for q in quests if q.finished), key=lambda c: c["finished_on"], reverse=True),
        "offers": [{"id": s.starter_id, "name": s.name, "icon": s.icon, "summary": s.summary,
                    "seasonal": bool(s.season), "chapters": [t for t, _s, _o in s.chapters]}
                   for s in available(context, today)],
    }
