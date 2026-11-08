"""
core.recreation
=================

Recreation in the health cluster (DEC-0098, build plan step 12; Zac,
2026-11-06: "Playing sports for recreation should somehow be tracked in an
activity log that may connect with workouts or as part of the health apps
cluster").

**A game or a sport played** is one entry: what, with whom, how long, how
hard (1 to 10, or words: easy, moderate, hard...), and when. Logged by
voice ("played pickleball for an hour with Sam, it was hard": `parse()`,
through `play.log`) or on a screen. Each one:

- counts toward **training load** (`load()`), by session-RPE: minutes times
  effort, the standard way to put different activities on one scale.
  Workouts count beside it by their minutes (they have no effort recorded,
  so they're shown, never guessed into the load);
- earns **skill XP** by the sport (`SPORTS`: pickleball trains coordination
  and athleticism, hiking endurance...);
- is a **life event** (`played`), so it shows in the history, the seasons,
  the Operating Journal's counts and the Chronicle's "Week Of Play".

The people named are kept in the person's own folder, like the rest of it.
`recreation.load` (core/loops.py) watches the week's load against the four
weeks before it (the acute-to-chronic ratio: a jump past 1.5 is the usual
sign of doing too much too soon), the person's to see. The Play screen
(`screen()`) shows six weeks of it as bars and each game's effort in a word
(`effort_word()`, DEC-0113).
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from core import life_events
from core.at_rest import open_text
from core.atomic_write import atomic_write_text

FILE_NAME = "recreation.json"
EFFORT_WORDS = {"easy": 3, "light": 3, "relaxed": 2, "chill": 2, "casual": 3, "moderate": 5, "steady": 5, "decent": 5,
                "good": 5, "solid": 6, "hard": 7, "tough": 7, "intense": 8, "brutal": 9, "exhausting": 9, "max": 10}
DEFAULT_EFFORT = 5
# sport words -> the skills it trains (data/skill_definitions.json ids)
SPORTS = (
    (r"pickleball|tennis|badminton|squash|ping ?pong|table tennis|racquetball|padel", ("coordination", "athleticism")),
    (r"basketball|soccer|football|hockey|volleyball|rugby|lacrosse|ultimate|frisbee|handball", ("athleticism", "endurance")),
    (r"hik(e|ing)|run(ning)?|jog(ging)?|cycl(e|ing)|bik(e|ing)|swim(ming)?|row(ing)?|paddl\w*|kayak\w*|ski(ing)?",
     ("endurance",)),
    (r"climb(ing)?|boulder(ing)?", ("strength", "coordination")),
    (r"golf|disc golf|bowling|darts|archery|cornhole|horseshoes", ("coordination",)),
    (r"martial arts|karate|judo|jiu.?jitsu|bjj|boxing|wrestling|kickboxing|mma", ("coordination", "strength")),
    (r"yoga|dance|dancing|skat(e|ing)|surf(ing)?", ("mobility", "coordination")),
)
ACUTE_CHRONIC_HIGH = 1.5
# games that aren't among the sports above (they earn the default, athleticism; "a video game" isn't one of them)
GAMES = (r"chess|checkers|cards|poker|board games?|catch|tag|pool|billiards|foosball|spikeball|kickball|dodgeball|"
         r"softball|baseball|wiffle ?ball|pickup")


# ------------------------------------------------------------------ reading what was said (pure)

_PLAYED = re.compile(r"^(?:i |we |just )*(?:played|went|did|got in|had)\s+(?:a (?:game|round|match) of\s+|some\s+|a\s+)?(.+)$",
                     re.IGNORECASE)
_MINUTES = re.compile(r"\b(?:for\s+)?(an?|half an|one|two|three|\d+(?:\.\d+)?)\s*(hours?|hrs?|h|minutes?|mins?|m)\b",
                      re.IGNORECASE)
_WITH = re.compile(r"\bwith\s+(.+?)(?=,|\.|;| and it was\b| it was\b| for \b|$)", re.IGNORECASE)
_EFFORT_N = re.compile(r"\b(?:effort|rpe|intensity)\s*(?:of\s*)?(\d{1,2})\b|\b(\d{1,2})\s*(?:/|out of)\s*10\b", re.IGNORECASE)
_NUM = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "half an": 0.5}


def parse(text: str) -> Optional[dict]:
    """Pure logic. "played pickleball for an hour with Sam and Jo, it was hard" -> {what, minutes, effort, with}.
    None when it isn't about playing something."""
    said = " ".join(str(text or "").split()).rstrip(".!")
    m = _PLAYED.match(said)
    if not m:
        return None
    rest = m.group(1)
    sport = re.split(r"\s+(?:for|with|at|this|today|yesterday|last)\b|,|\band it was\b|\bit was\b", rest, 1,
                     flags=re.IGNORECASE)[0].strip()
    sport = re.sub(r"^(?:a|an|the|some)\s+", "", sport, flags=re.IGNORECASE)
    if not sport or not any(re.search(rf"\b({w})\b", sport.lower()) for w in [w for w, _s in SPORTS] + [GAMES]):
        return None  # "went to the store" or "played that song again" isn't a game
    minutes = 0.0
    found = _MINUTES.search(rest)
    if found:
        n = _NUM.get(found.group(1).lower(), None)
        n = float(found.group(1)) if n is None else n
        minutes = n * 60 if found.group(2).lower().startswith("h") else n
    effort = None
    number = _EFFORT_N.search(rest)
    if number:
        effort = int(number.group(1) or number.group(2))
    else:
        for word, value in EFFORT_WORDS.items():
            if re.search(rf"\b{word}\b", rest.lower()) and word not in sport.lower():
                effort = value
                break
    people = []
    with_ = _WITH.search(rest)
    if with_:
        people = [p.strip() for p in re.split(r",|\band\b|&", with_.group(1)) if p.strip()][:8]
    when = date.today() - timedelta(days=1) if re.search(r"\byesterday\b", rest, re.IGNORECASE) else date.today()
    return {"what": sport[:60].lower(), "minutes": round(minutes, 1), "effort": effort, "with": people,
            "date": when.isoformat()}


def skills_for(what: str) -> tuple[str, ...]:
    """Pure logic. The skills a game or sport grows, from its name (athleticism when it isn't one she knows)."""
    for words, skills in SPORTS:
        if re.search(rf"\b({words})\b", (what or "").lower()):
            return skills
    return ("athleticism",)


def effort_of(value) -> int:
    """Pure logic. 1 to 10 from a number or a word; the middle when it's not said."""
    if value in (None, ""):
        return DEFAULT_EFFORT
    if isinstance(value, str) and not value.strip().isdigit():
        return EFFORT_WORDS.get(value.strip().lower(), DEFAULT_EFFORT)
    return max(1, min(10, int(value)))


# ------------------------------------------------------------------ the store

class RecreationLog:
    """One person's games and sports (context.recreation)."""

    def __init__(self, context=None, data_dir: Optional[Path] = None) -> None:
        """Loads what was played from the person's folder (recreation.json, or data/)."""
        self.context = context
        self.data_dir = Path(data_dir) if data_dir is not None else Path(__file__).resolve().parent.parent / "data"
        self._file = self.data_dir / FILE_NAME
        self.entries: list[dict] = []
        self._load()

    def _load(self) -> None:
        """Reads what was played; a missing or unreadable file gives nothing. Sealed on disk (DEC-0126): open_text reads it sealed or plain, and one that won't open is copied aside and counts as damaged."""
        try:
            self.entries = json.loads(open_text(self._file)).get("played", [])
        except (OSError, ValueError):
            self.entries = []

    def _save(self) -> None:
        """Writes what was played atomically."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._file, json.dumps({"played": self.entries}, indent=1, ensure_ascii=False))

    def log(self, what: str, minutes: float = 0.0, effort=None, people: Optional[list] = None,
            day: Optional[str] = None) -> dict:
        """Keeps one game or sport played: what, minutes, effort (its level, and whether they said one), who with, the
        day, and its load (minutes times effort). It's a life event, and earns XP (5 to 25, by time) in the skills it grows.
        """
        what = " ".join(str(what or "").split()).lower()
        if not what:
            raise ValueError("What did you play?")
        minutes = max(0.0, float(minutes or 0))
        level = effort_of(effort)
        entry = {"id": uuid.uuid4().hex[:10], "what": what[:60], "minutes": minutes, "effort": level,
                 "effort_said": effort not in (None, ""), "with": [str(p)[:40] for p in (people or [])][:8],
                 "date": day or date.today().isoformat(), "load": round(minutes * level, 1)}
        self.entries.append(entry)
        self._save()
        summary = f"Played {what}" + (f", {minutes:g} min" if minutes else "") + \
                  (f" with {', '.join(entry['with'])}" if entry["with"] else "")
        life_events.record(self, "played", summary, [f"played:{entry['id']}"],
                           {"date": entry["date"], "minutes": minutes, "effort": level, "load": entry["load"]})
        if self.context is not None and getattr(self.context, "profiles", None) is not None:
            from core.gamification import SkillWeight, grant_xp

            xp = max(5, min(25, int(minutes // 6) or 5))
            grant_xp(self.context, xp, "\U0001F3D3 Game on!", f"{what.capitalize()} counts: {xp} XP.",
                     skill_weights=[SkillWeight(s, xp) for s in skills_for(what)])
        return entry

    def delete(self, entry_id: str) -> None:
        """Removes one entry."""
        self.entries = [e for e in self.entries if e["id"] != entry_id]
        self._save()


# ------------------------------------------------------------------ training load

def load(context, today: Optional[date] = None, weeks: int = 5) -> list[dict]:
    """The last `weeks` weeks (Monday to Sunday), oldest first: play minutes and load, workout minutes."""
    today = today or date.today()
    start = today - timedelta(days=today.weekday())
    spans = [(start - timedelta(weeks=i), start - timedelta(weeks=i) + timedelta(days=6)) for i in range(weeks)][::-1]
    log = getattr(context, "recreation", None)
    played = log.entries if log is not None else []
    worked = getattr(context, "workout", None)
    sessions = worked.all_sessions() if worked is not None and hasattr(worked, "all_sessions") else []
    out = []
    for a, b in spans:
        mine = [e for e in played if a.isoformat() <= e["date"] <= b.isoformat()]
        lifts = [s for s in sessions if a.isoformat() <= (s.date or "") <= b.isoformat()]
        out.append({"week": a.isoformat(), "played": len(mine), "play_minutes": sum(e["minutes"] for e in mine),
                    "play_load": round(sum(e["load"] for e in mine), 1),
                    "workouts": len(lifts), "workout_minutes": round(sum(s.duration_minutes or 0 for s in lifts), 1)})
    return out


def acute_chronic(weeks: list[dict]) -> Optional[float]:
    """Pure logic. This week's play load against the average of the four before it (None without a base)."""
    if len(weeks) < 5:
        return None
    base = sum(w["play_load"] for w in weeks[-5:-1]) / 4
    return round(weeks[-1]["play_load"] / base, 2) if base > 0 else None


def lines(context, today: Optional[date] = None) -> list[str]:
    """Plain lines for a fact sheet: this week's play and the load beside the weeks before."""
    weeks = load(context, today)
    if not any(w["played"] or w["workouts"] for w in weeks):
        return []
    now = weeks[-1]
    out = [f"Played this week: {now['played']} time{'s' if now['played'] != 1 else ''}, {now['play_minutes']:g} min, "
           f"load {now['play_load']:g} (minutes × effort); workouts {now['workouts']}, {now['workout_minutes']:g} min."]
    out.append("Play load by week: " + ", ".join(f"{w['play_load']:g}" for w in weeks) + " (the last is this week).")
    ratio = acute_chronic(weeks)
    if ratio is not None:
        out.append(f"This week's play load is {ratio:g} times the four weeks before"
                   + (" (past 1.5, a jump that usually means easing off a little)." if ratio > ACUTE_CHRONIC_HIGH else "."))
    return out


def effort_word(effort) -> str:
    """Pure logic. An effort (1 to 10) in a word for the Play screen (the design canvas, DEC-0113): Easy up to 3,
    Moderate up to 6, Hard from 7."""
    effort = float(effort or DEFAULT_EFFORT)
    return "Easy" if effort <= 3 else "Moderate" if effort <= 6 else "Hard"


def screen(context, today: Optional[date] = None) -> dict:
    """Recreation's web screen (web/play.html): the latest games (each with its effort in a word), and the last six
    weeks' load, as the canvas's bars."""
    log = getattr(context, "recreation", None)
    played = sorted(log.entries, key=lambda e: e["date"], reverse=True)[:30] if log is not None else []
    return {"played": [{**{k: e[k] for k in ("id", "what", "minutes", "effort", "with", "date", "load")},
                        "effort_word": effort_word(e["effort"])} for e in played],
            "weeks": load(context, today, weeks=6), "lines": lines(context, today), "efforts": EFFORT_WORDS}
