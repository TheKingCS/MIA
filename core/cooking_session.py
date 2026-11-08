"""
core.cooking_session
======================

Cook mode's engine (DEC-0113, the design canvas's Kitchen · Cook Mode;
docs/design/applications/kitchen.md §13): one recipe being cooked, per
person, shared by every surface the way the live workout is
(core/training_session.py): the phone, the tablet on the counter, the PC
and, later, voice and the glasses all move the same session.

- **The steps** come from the recipe's instructions, split the way the
  recipe page splits them (core.web_screens.recipe_steps).
- **Where you are**: the step in focus; next and back move it.
- **Timers** are named ("Chili simmer") and keep running across steps, so
  the rice can go while you chop. A step that says how long ("simmer for
  18 minutes", "bake 1 hour 10 min") offers that timer (`step_timer`);
  the person starts it. Nothing is guessed by a model.
- **What this step uses**: the recipe's ingredients named in the step's
  words, with their amounts (`step_uses`), pure string matching.
- **Finishing** is the existing "I made this" (`meal.cook`, which logs
  the meal and uses up the pantry): the session only closes after it.

Everything here except `CookingStore` is pure logic. The store writes
through atomic_write_text, so "undo that" can put a session back
(core/undo_log.py), and it's a personal store (core/personal_data.py).
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from core.at_rest import open_text
from core.atomic_write import atomic_write_text
from core.logger import get_logger

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_FILE = "cooking_session.json"

COOKING, FINISHED = "cooking", "finished"
MAX_TIMER_MINUTES = 24 * 60


@dataclass
class Timer:
    """One named timer: what it's for, how long it was set for, and when it ends (ISO)."""
    name: str
    seconds: int
    ends: str


@dataclass
class Session:
    """The recipe being cooked: which recipe, its steps, the step in focus, the timers running, when it started."""
    recipe_id: str
    title: str
    steps: list = field(default_factory=list)  # [str]
    index: int = 0
    timers: list = field(default_factory=list)  # [Timer as dict]
    started: str = ""
    status: str = COOKING


def _iso(t: datetime) -> str:
    """A time as ISO text, to the second."""
    return t.replace(microsecond=0).isoformat()


def _at(text: str) -> Optional[datetime]:
    """ISO text back to a time; None when blank or unreadable."""
    try:
        return datetime.fromisoformat(text) if text else None
    except ValueError:
        return None


# ---------------------------------------------------------------- reading a step (pure)

_DURATION = re.compile(
    r"(?:(\d+(?:\.\d+)?)\s*(?:hours?|hrs?|h)\b)?\s*(?:and\s*)?(?:(\d+(?:\.\d+)?)\s*(?:minutes?|mins?|m)\b)?",
    re.IGNORECASE)
_RANGE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:-|–|to)\s*\d+(?:\.\d+)?\s*(hours?|hrs?|minutes?|mins?)\b", re.IGNORECASE)
_VERB = re.compile(r"\b(simmer|bake|roast|boil|cook|rest|chill|marinate|rise|proof|steep|fry|grill|soak|cool)\w*",
                   re.IGNORECASE)


def step_timer(step: str) -> Optional[dict]:
    """Pure logic. The timer a step asks for, from its own words: "Simmer for 18 minutes" -> {"name": "Simmer",
    "seconds": 1080}; "bake 1 hour 10 min" -> 4200 seconds; a range ("20 to 25 minutes") takes the low end, so
    the person checks early. None when the step gives no time.
    """
    text = step or ""
    best = 0
    rng = _RANGE.search(text)
    if rng:  # "20 to 25 minutes": the low end, so they check early
        best = int(float(rng.group(1)) * (3600 if rng.group(2).lower().startswith("h") else 60))
    for m in ([] if best else _DURATION.finditer(text)):
        hours, minutes = m.group(1), m.group(2)
        if not hours and not minutes:
            continue
        seconds = int(float(hours or 0) * 3600 + float(minutes or 0) * 60)
        if seconds > 0:
            best = seconds
            break
    if not best:
        return None
    verb = _VERB.search(text)
    return {"name": verb.group(1).capitalize() if verb else "Timer", "seconds": best}


def _key(name: str) -> str:
    """Pure logic. An ingredient's name for matching against a step: lower case, the last word's plural "s" off."""
    words = re.findall(r"[a-z]+", (name or "").lower())
    if not words:
        return ""
    last = words[-1][:-1] if words[-1].endswith("s") and len(words[-1]) > 3 else words[-1]
    return " ".join(words[:-1] + [last])


def step_uses(step: str, ingredients: list) -> list[dict]:
    """Pure logic. The recipe's ingredients this step names, in the recipe's order, with their amounts:
    [{"name": "kidney beans", "amount": "2 cans"}]. Matched on the ingredient's whole name or its last word
    ("beans", "stock"), plural or not; an ingredient the step doesn't mention isn't listed.
    """
    text = " " + re.sub(r"[^a-z]+", " ", (step or "").lower()) + " "
    out = []
    for ing in ingredients or []:
        key = _key(ing.get("name", ""))
        if not key:
            continue
        # the whole name, or its last word ("beans" for "kidney beans", "stock" for "chicken stock")
        keys = {key} | ({key.split()[-1]} if " " in key and len(key.split()[-1]) > 3 else set())
        if any(f" {k} " in text or f" {k}s " in text or f" {k}es " in text for k in keys):
            qty, unit = ing.get("quantity"), (ing.get("unit") or "").strip()
            amount = (f"{qty:g}" if isinstance(qty, (int, float)) and qty else "") + (f" {unit}" if unit else "")
            out.append({"name": ing.get("name", ""), "amount": amount.strip()})
    return out


# ---------------------------------------------------------------- moving the session (pure)

def start(recipe_id: str, title: str, steps: list, now: datetime) -> Session:
    """Pure logic. A new session at step one (ValueError when the recipe has no steps to follow)."""
    steps = [s for s in (steps or []) if str(s).strip()]
    if not steps:
        raise ValueError(f"{title} has no steps written down yet. Add them to the recipe first.")
    return Session(recipe_id=recipe_id, title=title, steps=steps, started=_iso(now))


def next_step(s: Session) -> None:
    """Pure logic. The next step (ValueError on the last one: then it's "I made this")."""
    if s.index >= len(s.steps) - 1:
        raise ValueError("That's the last step. Say \"I made this\" when it's on the table.")
    s.index += 1


def back(s: Session) -> None:
    """Pure logic. The step before (ValueError on the first)."""
    if s.index <= 0:
        raise ValueError("That's the first step.")
    s.index -= 1


def go_to(s: Session, number: int) -> None:
    """Pure logic. Step `number` (1-based); ValueError when there's no such step."""
    if not 1 <= number <= len(s.steps):
        raise ValueError(f"There are {len(s.steps)} steps.")
    s.index = number - 1


def add_timer(s: Session, name: str, seconds: int, now: datetime) -> Timer:
    """Pure logic. Starts a named timer (a same-named one is replaced); ValueError for no time or over a day."""
    seconds = int(seconds or 0)
    if seconds <= 0 or seconds > MAX_TIMER_MINUTES * 60:
        raise ValueError("A timer needs a time between a minute and a day.")
    name = (name or "Timer").strip()[:40] or "Timer"
    t = Timer(name=name, seconds=seconds, ends=_iso(now + timedelta(seconds=seconds)))
    s.timers = [x for x in s.timers if x.get("name", "").lower() != name.lower()] + [asdict(t)]
    return t


def cancel_timer(s: Session, name: str) -> None:
    """Pure logic. Stops the named timer (ValueError when there's none by that name)."""
    keep = [x for x in s.timers if x.get("name", "").lower() != (name or "").strip().lower()]
    if len(keep) == len(s.timers):
        raise ValueError(f"There's no timer called {name}.")
    s.timers = keep


def timers_left(s: Session, now: datetime) -> list[dict]:
    """Pure logic. Every timer with its seconds left (0 when it has gone off), soonest first."""
    out = []
    for x in s.timers:
        ends = _at(x.get("ends", ""))
        left = max(0, int((ends - now).total_seconds())) if ends else 0
        out.append({"name": x.get("name", "Timer"), "seconds": int(x.get("seconds") or 0), "left": left, "done": left == 0})
    return sorted(out, key=lambda t: t["left"])


def view(s: Session, now: datetime, ingredients: Optional[list] = None) -> dict:
    """What every surface shows: the recipe, the step in focus (its number, text, what it uses and the timer it
    offers), the steps around it, and the timers with their time left."""
    step = s.steps[s.index] if s.steps else ""
    return {"recipe_id": s.recipe_id, "title": s.title, "status": s.status, "number": s.index + 1,
            "steps_total": len(s.steps), "step": step, "previous": s.steps[s.index - 1] if s.index > 0 else None,
            "next": s.steps[s.index + 1] if s.index + 1 < len(s.steps) else None, "last": s.index == len(s.steps) - 1,
            "uses": step_uses(step, ingredients or []), "offer_timer": step_timer(step),
            "timers": timers_left(s, now), "started": s.started}


def say(s: Session, now: datetime) -> str:
    """One sentence for the voice: where they are."""
    v = view(s, now)
    line = f"Step {v['number']} of {v['steps_total']}: {v['step']}"
    done = [t["name"] for t in v["timers"] if t["done"]]
    return line + (f" The {done[0].lower()} timer is done." if done else "")


# ---------------------------------------------------------------- the store

class CookingStore:
    """The person's one recipe being cooked (a personal store, core/personal_data.py)."""

    def __init__(self, context, data_dir: Optional[Path] = None) -> None:
        """Points at the person's session file (data/ by default) and loads it."""
        self.context = context
        self.data_dir = Path(data_dir) if data_dir is not None else _DATA_DIR
        self._file = self.data_dir / _FILE
        self._load()

    def _load(self) -> None:
        """Reads the session in progress, keeping only fields it knows; an unreadable file is logged and means none. Sealed at rest (DEC-0126): a sealed file is opened; one that won't open is copied aside and starts empty."""
        self.session: Optional[Session] = None
        try:
            raw = json.loads(open_text(self._file)) if self._file.exists() else None
        except (OSError, ValueError):
            log.exception("%s unreadable; nothing cooking.", _FILE)
            raw = None
        if raw:
            self.session = Session(**{k: v for k, v in raw.items() if k in Session.__dataclass_fields__})

    def reload(self) -> None:
        """Reads the file again (after undo restored it, or another surface changed it)."""
        self._load()

    def save(self) -> None:
        """Writes the session atomically (every surface reads the same one)."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._file, json.dumps(asdict(self.session) if self.session else None, indent=1),
                          encoding="utf-8")

    def live(self) -> Optional[Session]:
        """The recipe being cooked now (not a finished one)."""
        return self.session if self.session is not None and self.session.status != FINISHED else None

    def begin(self, recipe_id: str, title: str, steps: list, now: Optional[datetime] = None) -> Session:
        """Starts cooking a recipe (ValueError when something else is already cooking, or it has no steps)."""
        if self.live() is not None:
            raise ValueError(f"{self.session.title} is already cooking. Finish or stop it first.")
        self.session = start(recipe_id, title, steps, now or datetime.now())
        self.save()
        return self.session

    def close(self) -> None:
        """Ends the session (after "I made this", or when they stop without making it)."""
        if self.session is not None:
            self.session.status = FINISHED
            self.save()
