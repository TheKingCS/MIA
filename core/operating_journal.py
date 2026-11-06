"""
core.operating_journal
========================

The Operating Journal (DEC-0097, build plan step 11; Zac, 2026-11-06: "a
template that is essentially a journal entry for how I want to operate, and
how I do operate so that MIA can learn my goals as well as my actual
routine").

**The template** is the person's own words, in sections: values,
priorities, the ideal day, the ideal week, and rules they keep. Each line is
also read by code (`habit_from()`) for something MIA can check in their
records:

- a count of something done in a week (workouts, meals logged, tasks done,
  missions, people caught up with), from their history
  (core/life_events.py);
- money in a category in a month, at most, from the budget.

A line code can't check is **self-rated**: the person rates it 1 to 5 in the
regular entry ("rate early mornings 4"), and that becomes its record.

**How they did** (`picture()`): every line against the last four weeks (or
months), as plain numbers and a trend by area, "3 of 4 weeks at your pace",
never a judgment, never a nudge of its own (DEC-0014). The question plan
`operating` puts it on a sheet ("am I living how I said I want to?"), and the
`journal.pace` loop is the person's to see, never a task.

Personal: in the person's own folder (`operating_journal.json`).
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from core.atomic_write import atomic_write_text

FILE_NAME = "operating_journal.json"
SECTIONS = ("values", "priorities", "day", "week", "rules")
SECTION_WORDS = {"values": "What I value", "priorities": "My priorities", "day": "My ideal day",
                 "week": "My ideal week", "rules": "Rules I keep"}
WEEKS = 4

# what a line can count, from the history: words -> (life event type, the area, the plain word)
COUNTED = (
    (r"work ?out|exercise|train(ing)?|lift|go to the gym|hit the gym|run\b|ride", "workout_logged", "health", "workouts"),
    (r"play (a |some )?(sports?|games?|pickleball|tennis|basketball|soccer|golf|ball)|get out and play", "played", "health",
     "games played"),
    (r"cook|meal ?prep|eat at home|home.?cooked|log (my )?meals", "meal_logged", "kitchen", "meals logged"),
    (r"(call|see|catch up with|visit|text) (a )?(friend|family|people|my (mom|dad|parents|brother|sister))",
     "caught_up", "people", "people caught up with"),
    (r"finish (a |my )?tasks?|get tasks done|clear (my )?tasks", "task_done", "tasks", "tasks done"),
    (r"missions?", "mission_completed", "growth", "missions completed"),
    (r"maintenance|upkeep", "maintenance_done", "home", "maintenance done"),
)
_TIMES = r"(\d+|once|twice|one|two|three|four|five|six|seven)\s*(?:times?|days?|nights?|x)?\s*(?:a|per|each|every)\s*(week|month)"
_NUMBER = {"once": 1, "one": 1, "twice": 2, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7}
_SPEND = re.compile(r"(?:spend|spending)\s+(?:no more than|under|less than|at most|max(?:imum)?|only)?\s*\$?\s*"
                    r"([0-9][0-9,]*(?:\.[0-9]+)?)\s*(?:dollars)?\s+(?:on|for)\s+([a-z &/'-]+?)\s*(?:a|per|each)\s+month",
                    re.IGNORECASE)
_DAILY = re.compile(r"\b(every|each) day\b|\bdaily\b", re.IGNORECASE)


# ------------------------------------------------------------------ reading a line (pure)

def habit_from(text: str) -> dict:
    """Pure logic. What a line of the template can be checked against: {kind, ...}."""
    said = " ".join(str(text or "").split())
    low = said.lower()
    spend = _SPEND.search(said)
    if spend:
        return {"kind": "spending", "category": spend.group(2).strip().title(), "per": "month",
                "target": float(spend.group(1).replace(",", "")), "at_most": True, "area": "money"}
    times = re.search(_TIMES, low)
    for words, event_type, area, plain in COUNTED:
        if re.search(rf"\b({words})", low):
            if times:
                n = times.group(1)
                return {"kind": "count", "type": event_type, "per": times.group(2),
                        "target": int(n) if n.isdigit() else _NUMBER[n], "at_most": False, "area": area, "word": plain}
            if _DAILY.search(low):
                return {"kind": "count", "type": event_type, "per": "week", "target": 7, "at_most": False,
                        "area": area, "word": plain}
    return {"kind": "self", "area": "self"}


# ------------------------------------------------------------------ the store

class OperatingJournal:
    """One person's journal (context.operating_journal): the template's lines, and their weekly ratings."""

    def __init__(self, context=None, data_dir: Optional[Path] = None) -> None:
        self.context = context
        self.data_dir = Path(data_dir) if data_dir is not None else Path(__file__).resolve().parent.parent / "data"
        self._file = self.data_dir / FILE_NAME
        self.lines: list[dict] = []
        self.ratings: list[dict] = []
        self._load()

    def _load(self) -> None:
        try:
            data = json.loads(self._file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        self.lines = list(data.get("lines", []))
        self.ratings = list(data.get("ratings", []))

    def _save(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._file, json.dumps({"lines": self.lines, "ratings": self.ratings[-2000:]}, indent=1,
                                                 ensure_ascii=False))

    def add(self, text: str, section: str = "") -> dict:
        text = " ".join(str(text or "").split())
        if not text:
            raise ValueError("Say how you want to operate.")
        habit = habit_from(text)
        section = section if section in SECTIONS else "rules"
        line = {"id": uuid.uuid4().hex[:8], "section": section, "text": text[:300], "habit": habit,
                "added": date.today().isoformat()}
        self.lines.append(line)
        self._save()
        return line

    def remove(self, line_id: str) -> None:
        self.lines = [l for l in self.lines if l["id"] != line_id]
        self._save()

    def find(self, words: str) -> Optional[dict]:
        """The line a few words mean ("early mornings"), by shared words."""
        from core.failure_log import similar

        scored = [(similar(words, l["text"]), l) for l in self.lines]
        scored = [s for s in scored if s[0] > 0]
        return max(scored, key=lambda s: s[0])[1] if scored else None

    def rate(self, line_id: str, score: int, day: Optional[date] = None) -> dict:
        if not 1 <= int(score) <= 5:
            raise ValueError("Rate it from 1 to 5.")
        day = day or date.today()
        week = (day - timedelta(days=day.weekday())).isoformat()
        self.ratings = [r for r in self.ratings if not (r["line"] == line_id and r["week"] == week)]
        entry = {"line": line_id, "week": week, "score": int(score), "at": datetime.now().isoformat(timespec="seconds")}
        self.ratings.append(entry)
        self._save()
        return entry


# ------------------------------------------------------------------ how they did

_ADD = re.compile(r"^(?:please )?(?:add (?:this )?to|put (?:this )?in|in|for)? ?my operating journal[:,]?\s+(.+)$",
                  re.IGNORECASE)
_RATE = re.compile(r"^rate (.+?) (?:a )?([1-5])(?: out of 5)?(?: this week)?[.!]*$", re.IGNORECASE)


def reply(context, text: str) -> Optional[str]:
    """Talking to it: "add to my operating journal: work out 4 times a week", "rate early mornings 4". The
    person's own words are the approval. None when it isn't that."""
    journal = getattr(context, "operating_journal", None)
    actions = getattr(context, "actions", None)
    if journal is None or actions is None:
        return None
    said = " ".join(str(text or "").split())
    added, rated = _ADD.match(said), _RATE.match(said)
    if added:
        kind, params = "operating.add", {"text": added.group(1)}
    elif rated and journal.lines:
        line = journal.find(rated.group(1))
        if line is None:
            return None
        kind, params = "operating.rate", {"line_id": line["id"], "score": int(rated.group(2))}
    else:
        return None
    from core.actions import ActionError

    try:
        done = actions.approve(context, actions.propose(context, kind, params, proposed_by="person").proposal_id)
    except ActionError as problem:
        return str(problem)
    return done.result if done.status == "executed" else (done.result or "That didn't work; nothing was changed.")


def weekly_offer(context, today: Optional[date] = None) -> list:
    """Sundays: the self-rated lines not rated this week, as one gentle question through the gate."""
    from core.communication_gate import Candidate

    today = today or date.today()
    journal = getattr(context, "operating_journal", None)
    if today.weekday() != 6 or journal is None:
        return []
    week = (today - timedelta(days=today.weekday())).isoformat()
    rated = {r["line"] for r in journal.ratings if r["week"] == week}
    waiting = [l for l in journal.lines if l["habit"]["kind"] == "self" and l["id"] not in rated]
    if not waiting:
        return []
    first = " ".join(waiting[0]["text"].split()[:3]).lower()
    return [Candidate(topic="operating_journal", title="Your Operating Journal",
                      message=f"How did this week go against how you want to operate? {len(waiting)} of your lines are "
                              f"yours to rate: say \"rate {first} 4\" (1 to 5) for each.",
                      fingerprint=f"operating_journal:{week}")]


def _weeks(today: date, n: int = WEEKS) -> list[tuple[date, date]]:
    start = today - timedelta(days=today.weekday())
    return [(start - timedelta(weeks=i), start - timedelta(weeks=i) + timedelta(days=6)) for i in range(n)][::-1]


def _months(today: date, n: int = WEEKS) -> list[tuple[date, date]]:
    out, first = [], today.replace(day=1)
    for _ in range(n):
        last = (first + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        out.append((first, last))
        first = (first - timedelta(days=1)).replace(day=1)
    return out[::-1]


def measure(context, line: dict, today: Optional[date] = None) -> Optional[dict]:
    """Pure-ish. One line against its record: {spans, values, target, on_pace, this, word}. None when self-rated
    and never rated."""
    today = today or date.today()
    h = line["habit"]
    if h["kind"] == "self":
        journal = getattr(context, "operating_journal", None)
        mine = [r for r in (journal.ratings if journal else []) if r["line"] == line["id"]]
        if not mine:
            return None
        weeks = {r["week"]: r["score"] for r in mine}
        spans = _weeks(today)
        values = [weeks.get(a.isoformat()) for a, _b in spans]
        rated = [v for v in values if v is not None]
        return {"values": values, "target": 4, "on_pace": sum(1 for v in rated if v >= 4), "of": len(rated),
                "this": values[-1], "word": "your own rating, out of 5", "per": "week"}
    spans = _weeks(today) if h["per"] == "week" else _months(today)
    if h["kind"] == "count":
        from core.life_events import events_for, reversed_ids

        found = events_for(context, since=spans[0][0].isoformat(), until=today.isoformat(), types=[h["type"]])
        gone = reversed_ids(events_for(context, since=spans[0][0].isoformat(), types=["undone"]))
        days = [e.day for e in found if e.event_id not in gone]
        values = [sum(1 for d in days if a.isoformat() <= d <= b.isoformat()) for a, b in spans]
        word = h.get("word", h["type"])
    else:  # spending in a category
        budget = getattr(context, "budget", None)
        if budget is None:
            return None
        spent = [(str(e.date or "")[:10], float(e.amount or 0)) for e in budget.all_expenses()
                 if str(getattr(e, "category", "")).lower() == h["category"].lower()]
        values = [round(sum(v for d, v in spent if a.isoformat() <= d <= b.isoformat()), 2) for a, b in spans]
        word = f"spent on {h['category']}"
    done = values[:-1]  # the current week or month isn't over
    ok = [(v <= h["target"]) if h.get("at_most") else (v >= h["target"]) for v in done]
    return {"values": values, "target": h["target"], "on_pace": sum(ok), "of": len(done), "this": values[-1],
            "word": word, "per": h["per"], "at_most": h.get("at_most", False)}


def picture(context, today: Optional[date] = None, money_word=None) -> list[str]:
    """Every line against what the records show, in plain numbers: never a judgment."""
    journal = getattr(context, "operating_journal", None)
    if journal is None or not journal.lines:
        return []
    fmt = money_word or (lambda v: f"{v:,.2f}")
    out = []
    for line in journal.lines:
        m = measure(context, line, today)
        if m is None:
            out.append(f"\"{line['text']}\": not rated yet (say \"rate {' '.join(line['text'].split()[:3]).lower()} 4\").")
            continue
        per = "week" if m["per"] == "week" else "month"
        this = m["this"] if m["this"] is not None else "not rated"
        if line["habit"]["kind"] == "spending":
            shown = ", ".join(fmt(v) for v in m["values"])
            out.append(f"\"{line['text']}\": {shown} by {per} (the last is this {per} so far); within it "
                       f"{m['on_pace']} of {m['of']} full {per}s.")
        elif line["habit"]["kind"] == "self":
            out.append(f"\"{line['text']}\": rated {', '.join('-' if v is None else str(v) for v in m['values'])} by "
                       f"week (out of 5); this week {this}.")
        else:
            out.append(f"\"{line['text']}\": {', '.join(str(v) for v in m['values'])} {m['word']} by {per} (the "
                       f"last is this {per} so far); {m['on_pace']} of {m['of']} full {per}s at {m['target']:g} or more.")
    return out


def pace(context, today: Optional[date] = None) -> Optional[tuple[float, int, dict]]:
    """(share of measured full periods on pace, how many, by area) for the journal.pace loop."""
    journal = getattr(context, "operating_journal", None)
    if journal is None or not journal.lines:
        return None
    hits = total = 0
    by: dict[str, list[int]] = {}
    for line in journal.lines:
        m = measure(context, line, today)
        if m is None or not m["of"]:
            continue
        hits += m["on_pace"]
        total += m["of"]
        area = by.setdefault(line["habit"]["area"], [0, 0])
        area[0] += m["on_pace"]
        area[1] += m["of"]
    if not total:
        return None
    return round(hits / total, 2), total, by
