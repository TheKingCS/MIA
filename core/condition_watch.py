"""
core.condition_watch
======================

"Tell me when..." (brainstorm round 16, 2026-11-25): a condition in his own world he asks her to watch, checked in
code every day and said through the communication gate when it comes true. World Intelligence watches the news
(core/world_intel); this watches his own records and his forecast:

- **freeze** / **cold**: tonight's low at or under a temperature ("tell me if it freezes tonight": 32 °F or 0 °C by
  his country, core/weather.unit_for; "tell me when it gets below 20 degrees");
- **rain**: tomorrow's chance of rain at half or more;
- **item**: a pantry item down to a number ("tell me when we're down to 2 dozen eggs", "when the flour gets below
  5", "when we're low on coffee": 1 or under, "out of": 0);
- **feed**: a flock's feed down to a number of days (core/feed_runway; 5 when none is said);
- **supply**: water, food or generator fuel down to a number of days (core/homestead_health; 7 when none is said).

**How it's read** (`parse`): his words, in code, never the model; what can't be read is said back with an example
("I can watch the weather, a pantry item, the feed or your water, food and fuel"), and a pantry item he doesn't have
is said as such. A reminder, something stopping ("when it stops raining"), a bill or a price is never a watch, and
the weather only when it's the weather doing it ("if it freezes", never "the freezer"; the Fable review,
2026-11-25). **Once or every time**: a watch says itself once and is done (`told`), unless he said "whenever",
"every time" or "each time": then once a day while it's true. A watch for "tonight" or "tomorrow" ends after that
day (`until`).

**The store** (`WatchList`, each person's own, condition_watches.json, sealed at rest and written through
atomic_write_text so "undo that" restores it): adding and stopping a watch are the actions `condition_watch.add` / `condition_watch.remove`
(his own words, so act_within_grant: he asked, and undo takes it back). Marking one told is her bookkeeping on her
own watch, the way the gate logs what it said. A pantry watch that fires offers the item for the grocery list
(`restock`, brainstorm round 17): the words to say, or added with its Undo when he approved that kind ahead. The daily check `condition_watch` (`offer`) offers each one that's
true, TIMELY (held for an opening, never dropped, and never paused for dismissals: core/communication_gate's
NEVER_PAUSED), the weather's ending the next morning.
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from core.actions import ACTION_TYPES, ActionError, ActionType
from core.atomic_write import atomic_write_text
from core.data_root import DATA_DIR
from core.logger import get_logger

log = get_logger(__name__)

FILE_NAME = "condition_watches.json"
KINDS = ("freeze", "rain", "item", "feed", "supply")
FEED_DAYS = 5
SUPPLY_DAYS = 7
RAIN_CHANCE = 50
CAN_WATCH = ("I can watch tonight's low (\"tell me if it freezes tonight\"), tomorrow's rain, a pantry item (\"tell "
             "me when we're down to 2 dozen eggs\"), the flock's feed (\"when the feed gets under 5 days\"), or your "
             "water, food and fuel (\"when we're down to 3 days of water\").")


@dataclass
class Watch:
    """One condition he asked her to watch: its kind (KINDS), what it's about (an item's name, "water"...), the number
    it's measured against, his words, whether it says itself every time, the last day it counts (`until`, "" for
    none), when it was made and when it was last told ("" for never)."""
    watch_id: str
    kind: str
    about: str = ""
    value: float = 0.0
    words: str = ""
    standing: bool = False
    until: str = ""
    created_at: str = ""
    told: str = ""

    def to_dict(self) -> dict:
        """As saved."""
        return asdict(self)

    @staticmethod
    def from_dict(raw: dict) -> "Watch":
        """From what was saved; unknown keys left out."""
        known = {k: raw[k] for k in Watch.__dataclass_fields__ if k in raw}
        return Watch(**known)


class WatchList:
    """A person's condition watches (condition_watches.json in their own folder). Each is known by what he said
    (`EPISTEMIC`, DEC-0173 G3: its source is his own words, kept with it)."""
    EPISTEMIC = {"record": Watch, "source": "words", "at": "created_at", "how": "said"}

    def __init__(self, context=None, data_dir: Optional[Path] = None) -> None:
        """Loads them from the person's folder (or data/)."""
        self.context = context
        self.data_dir = Path(data_dir) if data_dir is not None else DATA_DIR
        self._file = self.data_dir / FILE_NAME
        self.watches: list[Watch] = []
        self._load()

    def _load(self) -> None:
        """Reads the file, sealed on disk (core/at_rest: open_text reads it sealed or plain); missing or unreadable
        is no watches."""
        from core.at_rest import open_text

        try:
            raw = json.loads(open_text(self._file)) if self._file.exists() else {}
            raw = raw if isinstance(raw, dict) else {}
            self.watches = [Watch.from_dict(d) for d in raw.get("watches", []) if isinstance(d, dict)]
        except (OSError, ValueError, TypeError) as problem:
            log.warning("Couldn't read the condition watches: %s", problem)
            self.watches = []

    def _save(self) -> None:
        """Writes it atomically (so "undo that" can restore it)."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._file, json.dumps({"watches": [w.to_dict() for w in self.watches]}, indent=1,
                                                 ensure_ascii=False))

    def add(self, watch: Watch) -> Watch:
        """Keeps a new watch."""
        self.watches.append(watch)
        self._save()
        return watch

    def remove(self, watch_id: str) -> Watch:
        """Stops one. KeyError for one that isn't there."""
        found = self.get(watch_id)
        if found is None:
            raise KeyError(watch_id)
        self.watches = [w for w in self.watches if w.watch_id != watch_id]
        self._save()
        return found

    def get(self, watch_id: str) -> Optional[Watch]:
        """One by its id."""
        return next((w for w in self.watches if w.watch_id == watch_id), None)

    def live(self, today: date) -> list[Watch]:
        """The ones still watching: not told yet (or standing), and not past their last day."""
        return [w for w in self.watches if (w.standing or not w.told) and (not w.until or w.until >= today.isoformat())]

    def mark_told(self, watch_id: str, on: date) -> None:
        """Her bookkeeping: the day a watch was said (a once-watch is then done)."""
        found = self.get(watch_id)
        if found is not None:
            found.told = on.isoformat()
            self._save()


def book(context) -> WatchList:
    """The person's watch list: the context's, else one on the data folder."""
    found = getattr(context, "condition_watches", None) if context is not None else None
    return found if found is not None else WatchList(context)


# ------------------------------------------------------------------ reading his words

_STANDING = re.compile(r"\b(?:whenever|every time|each time|any ?time|every (?:morning|day|night|evening)|each "
                       r"(?:morning|day|night|evening))\b", re.I)
_NUMBER = r"(\d+(?:\.\d+)?)"
_WORD_NUMBERS = {"a dozen": 12, "two dozen": 24, "three dozen": 36, "one": 1, "two": 2, "three": 3, "four": 4,
                 "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}


def _numbers(text: str) -> str:
    """Pure logic. "2 dozen" as 24 and the small number words as digits, so one pattern reads them."""
    text = re.sub(r"\b(\d+(?:\.\d+)?) dozen\b", lambda m: f"{float(m.group(1)) * 12:g}", text)
    for words, n in _WORD_NUMBERS.items():
        text = re.sub(rf"\b{words}\b", str(n), text)
    return text


def _until(text: str, today: date) -> str:
    """Pure logic. The last day a watch counts: "tonight" today, "tomorrow" tomorrow, else none."""
    if re.search(r"\btonight\b", text):
        return today.isoformat()
    if re.search(r"\btomorrow\b", text):
        return (today + timedelta(days=1)).isoformat()
    return ""


_NOT_A_WATCH = re.compile(r"\bremind me\b|\bstops? (?:rain|freez|snow)\w*|\b(?:bill|bills|dollars?|bucks|price|cost)\b|"
                          r"\$\d", re.I)
_FREEZE = re.compile(r"\b(?:it|we)(?:'s| is| are| will| gonna| going to)*\s*(?:going to |gonna |will )?"
                     r"(?:freez(?:e|es|ing)|frost(?:s|ing)?|get (?:a )?(?:hard )?(?:frost|freeze))\b|"
                     r"\b(?:a |any |hard )?(?:frost|freeze)\b (?:tonight|tomorrow)|\bbelow freezing\b", re.I)
_RAIN = re.compile(r"\bit(?:'s| is| will)?\s*(?:going to |gonna |will )?rain(?:s|ing)?\b|\brain (?:tonight|tomorrow)\b",
                   re.I)
_PRONOUNS = {"it", "that", "this", "they", "them", "he", "she", "you", "temperature", "temp", "the temperature"}
_SUBJECT = r"(?:^|\b(?:our|my|the|we're|we are|i'm|i am|on|of|out of|low on|running low on|run out of)\s)"


def _clean_name(name: str) -> str:
    """Pure logic. An item's name without "the", "my" or a closing "please"."""
    name = re.sub(r"^(?:the|my|our|some)\s+", "", name.strip())
    return re.sub(r"[ ,]*(?:please|thanks|thank you|mia|left)\s*$", "", name).strip()


def parse(words: str, today: Optional[date] = None, celsius: bool = False) -> Optional[dict]:
    """Pure logic. {kind, about, value, standing, until} from his words, or None when it isn't something she can
    watch. A reminder ("remind me if it rains to bring in the laundry"), something stopping ("when it stops
    raining"), a bill or a price isn't a watch; the weather only when it's the weather doing it ("if it freezes",
    "frost tonight", never "the freezer" or "the rain gauge", nor a weekday's, which the forecast doesn't read); a
    supply or the feed only as its own subject ("our water", "low on gas", never "the dog food"); never a store's
    sale, a budget, money or a vehicle ("the truck is low on gas"). An item's name is his words for it (matched to the pantry when it's
    checked)."""
    today = today or date.today()
    text = _numbers(" ".join(str(words or "").lower().replace("’", "'").split()))
    text = re.sub(r"\bbelow zero\b", "below 0 degrees", text)
    if _NOT_A_WATCH.search(text) or re.search(r"\b(?:store|sale|budget|money|truck|car|van|tank)\b", text):
        return None  # "when the feed store has a sale", "the truck is low on gas": not his homestead's (cross-route)
    base = {"standing": bool(_STANDING.search(text)), "until": _until(text, today), "about": ""}
    cold = re.search(rf"\b(?:below|under|down to|colder than|drops? (?:below|under|to)|gets? (?:below|under|down to)) "
                     rf"(-?{_NUMBER[1:-1]}) ?(?:degrees|°)", text)
    if cold:
        return {**base, "kind": "freeze", "value": float(cold.group(1))}
    if re.search(r"\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", text) and \
            (_FREEZE.search(text) or _RAIN.search(text)):
        return None  # "rain on Saturday": the forecast only reads tonight and tomorrow, never a day he named
    if _FREEZE.search(text):
        return {**base, "kind": "freeze", "value": 0.0 if celsius else 32.0}
    if _RAIN.search(text):
        return {**base, "kind": "rain", "value": float(RAIN_CHANCE)}
    days = re.search(rf"\b{_NUMBER} days?\b", text)
    if re.search(rf"{_SUBJECT}(?:chicken |layer |the flock'?s? |the chickens'? )?feed\b", text) and \
            not re.search(r"\b(?:dog|cat|horse|goat|pig|cattle|rabbit)s?'? feed\b", text):
        out = bool(re.search(r"\bout of (?:\w+ )?feed\b", text))
        return {**base, "kind": "feed", "about": "feed",
                "value": 0.0 if out else (float(days.group(1)) if days else float(FEED_DAYS))}
    supply = re.search(rf"{_SUBJECT}(water|food|fuel|gas|gasoline|generator fuel)\b", text)
    if supply and not re.search(r"\b(?:dog|cat|pet|horse|goat|bird|fish|chicken)s?'? (?:water|food)\b", text) and \
            (days or re.search(r"\b(?:low|run(?:ning|s)? (?:low|out)|out of)\b", text)):
        about = {"gas": "fuel", "gasoline": "fuel", "generator fuel": "fuel"}.get(supply.group(1), supply.group(1))
        out = bool(re.search(r"\bout of\b", text)) and not days
        return {**base, "kind": "supply", "about": about,
                "value": 0.0 if out else (float(days.group(1)) if days else float(SUPPLY_DAYS))}
    asked = re.sub(r"^(?:please |hey mia,? )?(?:(?:tell|let|warn|alert|ping) me(?: know)?) (?:when(?:ever)?|if|once|"
                   r"every time|each time) (?:it'?s |we'?re |i'?m |we are |i am |we have |we've got |there'?s |there "
                   r"are )?", "", text)
    asked = re.sub(r"[ ,]*(?:please|thanks|thank you|mia)\s*[?.!]*\s*$", "", asked)
    item = re.search(rf"\b(?:down to|below|under|less than|drops? (?:below|under|to)|gets? (?:below|under|down to)) "
                     rf"{_NUMBER}(?: \w+)?(?: of)? ([a-z][a-z' -]*?)\s*[?.!]*$", asked)
    if item and _clean_name(item.group(2)) not in _PRONOUNS | {""}:
        return {**base, "kind": "item", "about": _clean_name(item.group(2)), "value": float(item.group(1))}
    item = re.match(rf"([a-z][a-z' -]*?) (?:gets?|drops?|goes|is|are) (?:below|under|down to) {_NUMBER}\b", asked)
    if item and _clean_name(item.group(1)) not in _PRONOUNS | {""}:
        return {**base, "kind": "item", "about": _clean_name(item.group(1)), "value": float(item.group(2))}
    low = re.search(r"\b(?:low on|running low on|run(?:ning)? out of|out of)\s+([a-z][a-z' -]*?)\s*[?.!]*$", asked)
    if low and _clean_name(low.group(1)) not in _PRONOUNS | {""}:
        out = bool(re.search(r"\bout of\b", asked)) and not re.search(r"\blow\b", asked)
        return {**base, "kind": "item", "about": _clean_name(low.group(1)), "value": 0.0 if out else 1.0}
    return None


def describe(watch: Watch, unit: str = "°F") -> str:
    """Pure logic. A watch in words: "if tonight's low gets down to 32°F (tonight only)"; a watch for tomorrow night
    or tomorrow's rain says its day."""
    v = f"{watch.value:g}"
    made = (watch.created_at or "")[:10]
    later = bool(watch.until) and watch.until != made
    night = "tomorrow night's low" if later else "tonight's low"
    rainy = "today" if watch.until and not later else "tomorrow"
    said = {"freeze": f"if {night} gets down to {v}{unit}",
            "rain": f"if the chance of rain {rainy} is half or more",
            "item": f"when the pantry's {watch.about} gets down to {v}",
            "feed": "when the flock's feed runs out" if watch.value == 0 else f"when the flock's feed is down to {v} days",
            "supply": f"when you're out of {watch.about}" if watch.value == 0 else f"when your {watch.about} is down to {v} days"
            }.get(watch.kind, watch.words)
    if watch.until and watch.kind == "freeze":
        said += " (that night only)" if later else " (tonight only)"
    return said + (", every time" if watch.standing else "")


# ------------------------------------------------------------------ checking

def _pantry_item(context, about: str):
    """The pantry item his words name (a whole-word match either way, the shortest name first), or None."""
    kitchen = getattr(context, "kitchen", None)
    if kitchen is None or not about:
        return None
    want = set(re.findall(r"[a-z]+", about.lower()))
    want = {w[:-1] if w.endswith("s") and len(w) > 3 else w for w in want}
    best = None
    for p in kitchen.all_pantry_items():
        have = {w[:-1] if w.endswith("s") and len(w) > 3 else w for w in re.findall(r"[a-z]+", p.name.lower())}
        if want and (want <= have or have <= want) and (best is None or len(p.name) < len(best.name)):
            best = p
    return best


def check(context, watch: Watch, today: date, forecast: Optional[dict] = None) -> Optional[str]:
    """Pure-ish: the words to say when the watch's condition is true now, else None (and None when it can't be read)."""
    if watch.kind in ("freeze", "rain"):
        if forecast is None:
            from core import weather

            forecast = weather.card(context)
        if not forecast or not forecast.get("text"):
            return None
        tomorrow = forecast.get("tomorrow") or {}
        if watch.kind == "freeze":
            if watch.until and today.isoformat() < watch.until:
                return None  # "tomorrow night": tonight's low isn't the one he asked about
            low = tomorrow.get("low", forecast.get("low"))
            if low is not None and low <= watch.value:
                return (f"You asked me to tell you: tonight's low is {low:g}{forecast.get('unit', '')}, at or under "
                        f"{watch.value:g}. Cover the tender plants, check the birds' water and the pipes.")
            return None
        if watch.until and today.isoformat() == watch.until:  # the day he named is today: today's chance
            day = next((d for d in forecast.get("days") or [] if str(d.get("date", ""))[:10] == watch.until), {})
            chance, when = day.get("rain"), "today"
        else:
            chance, when = tomorrow.get("rain"), "tomorrow"
        if chance is not None and chance >= watch.value:
            return f"You asked me to tell you: {when} has a {chance}% chance of rain."
        return None
    if watch.kind == "item":
        item = _pantry_item(context, watch.about)
        have = float(item.quantity or 0) if item is not None else 0.0
        if item is not None and str(item.unit or "").lower().startswith("dozen"):
            have *= 12  # his "2 dozen eggs" was read as 24 eggs
        if item is not None and have <= watch.value:
            unit = f" {item.unit}" if item.unit else ""
            return f"You asked me to tell you: {item.name} is down to {float(item.quantity or 0):g}{unit}."
        return None
    if watch.kind == "feed":
        from core import feed_runway

        flocks = getattr(getattr(context, "flock", None), "flocks", []) or []
        for flock in flocks:
            found = feed_runway.runway(context.flock.entries, flock, today)
            if found and not found.get("unknown") and found["days_left"] is not None and found["days_left"] <= watch.value:
                return f"You asked me to tell you: {feed_runway.words(flock.name, found)}"
        return None
    if watch.kind == "supply":
        from core import homestead_health

        found, _missing = homestead_health.days(context, today)
        left = found.get(watch.about.capitalize())
        if left is not None and left <= watch.value:
            return f"You asked me to tell you: your {watch.about} is down to {left:g} days."
        return None
    return None


def restock(context, watch: Watch) -> str:
    """When a pantry watch fires (brainstorm round 17: a watch that acts on itself): the item for the grocery list.
    Added at once, with its Undo, only when he approved grocery.add from now on (DEC-0215: core/actions.propose
    by "mia" runs it through the grants check); otherwise the words to say to add it, never a card no screen shows
    (the Fable review, 2026-11-25: a background card expired unseen). Nothing when it's already on the list (a name
    matching either way). The sentence to add to the message, or ""."""
    if watch.kind != "item":
        return ""
    item = _pantry_item(context, watch.about)
    kitchen, actions = getattr(context, "kitchen", None), getattr(context, "actions", None)
    if item is None or kitchen is None or actions is None:
        return ""
    name = item.name.lower()
    try:
        listed = [g.name.lower() for g in kitchen.all_grocery_items() if not g.checked]
        if any(name in g or g in name for g in listed):
            return f" {item.name} is already on your grocery list."
        from core.actions import _granted_ahead

        if not _granted_ahead(context, "grocery.add"):
            return f" Say \"add {name} to my grocery list\" and I will."
        card = actions.propose(context, "grocery.add", {"name": item.name}, proposed_by="mia")
    except Exception:  # noqa: BLE001 - the message still goes without the offer
        log.exception("Condition watch: couldn't offer %s for the grocery list", watch.about)
        return ""
    if getattr(card, "status", "") == "executed":
        return f" I added {item.name} to your grocery list (undo it if you don't want it)."
    return f" Say \"add {name} to my grocery list\" and I will."


def offer(context, now: datetime) -> list:
    """The daily check: each live watch whose condition is true, through the gate as TIMELY (he asked for it, so it
    waits for an opening rather than being dropped; the topic is never paused for dismissals, NEVER_PAUSED), once for
    a once-watch (then marked told) and once a day for a standing one. The weather's expires the next morning, the
    rest after two days (the Fable review, 2026-11-25). A pantry watch's message ends with its grocery-list
    offer (`restock`)."""
    from core.communication_gate import TIMELY, Candidate

    today = now.date()
    watches = book(context)
    out = []
    for watch in watches.live(today):
        if watch.standing and watch.told == today.isoformat():
            continue
        try:
            said = check(context, watch, today)
        except Exception:  # noqa: BLE001 - one watch that can't be read never stops the rest
            log.exception("Condition watch %s couldn't be checked", watch.watch_id)
            continue
        if not said:
            continue
        said += restock(context, watch)
        weather = watch.kind in ("freeze", "rain")
        ends = datetime.combine(today, datetime.min.time()) + (timedelta(days=1, hours=9) if weather else timedelta(days=2))
        out.append(Candidate(topic="condition_watch", title="Something you asked me to watch", message=said,
                             urgency=TIMELY, source="system", fingerprint=f"watch-{watch.watch_id}-{today.isoformat()}",
                             expires=ends.isoformat(timespec="seconds")))
        watches.mark_told(watch.watch_id, today)
    return out


# ------------------------------------------------------------------ actions and tools

def _made(context, params) -> Watch:
    """The watch the action would keep, from his words; ActionError when it can't be read."""
    from core.weather import unit_for

    words = str(params.get("words") or "").strip()
    today = date.today()
    found = parse(words, today, celsius=unit_for(context) == "celsius")
    if found is None:
        raise ActionError("I couldn't tell what to watch for. " + CAN_WATCH)
    if found["kind"] == "item" and _pantry_item(context, found["about"]) is None:
        raise ActionError(f"I don't see {found['about']} in your pantry, so I couldn't tell when it runs low. Add it in "
                          f"Kitchen with how much you have, then ask me again.")
    return Watch(watch_id=str(params.get("watch_id") or uuid.uuid4().hex[:8]), kind=found["kind"],
                 about=found["about"], value=found["value"], words=words[:200], standing=found["standing"],
                 until=found["until"], created_at=datetime.now().isoformat(timespec="seconds"))


def _unit(context) -> str:
    """°F or °C by his country."""
    from core.weather import unit_for

    return "°C" if unit_for(context) == "celsius" else "°F"


def _add_describe(context, params) -> str:
    """What condition_watch.add says."""
    return f"Watch and tell you {describe(_made(context, params), _unit(context))}"


def _add_execute(context, params) -> str:
    """Does condition_watch.add: keeps the watch."""
    watch = book(context).add(_made(context, params))
    return f"I'll tell you {describe(watch, _unit(context))}. Say \"stop watching that\" to stop."


def _remove_describe(context, params) -> str:
    """What condition_watch.remove says."""
    watch = book(context).get(str(params.get("watch_id") or ""))
    if watch is None:
        raise ActionError("That isn't one of the things I'm watching for you.")
    return f"Stop watching {describe(watch, _unit(context))}"


def _remove_execute(context, params) -> str:
    """Does condition_watch.remove."""
    watch = book(context).remove(str(params.get("watch_id") or ""))
    return f"Stopped: I won't tell you {describe(watch, _unit(context))}."


ACTIONS = {a.kind: a for a in (
    ActionType("condition_watch.add", "Watch For This", {"words": "what to watch for, in his words"},
               _add_describe, _add_execute),
    ActionType("condition_watch.remove", "Stop Watching", {"watch_id": "one of his watches"},
               _remove_describe, _remove_execute),
)}
ACTION_TYPES.update(ACTIONS)


def _run(context, kind: str, params: dict) -> str:
    """Runs one of these actions for a voice tool as its screen would (core/actions.run_as_tool: describe's checks,
    then execute, or the refusal in its own words)."""
    from core.actions import run_as_tool

    return run_as_tool(context, kind, params)


def _watch_tool(context, arguments: dict) -> str:
    """Tool watch_condition: keeps a watch from his own words (its prompt_arg)."""
    return _run(context, "condition_watch.add", {"words": str(arguments.get("question") or arguments.get("words") or "")})


def lines(context, today: Optional[date] = None) -> list[str]:
    """Each live watch in words, for "what are you watching for me?"."""
    unit = _unit(context)
    return [describe(w, unit) for w in book(context).live(today or date.today())]


def _list_tool(context, arguments: dict) -> str:
    """Tool list_condition_watches: what she's watching for him."""
    said = lines(context)
    if not said:
        return "I'm not watching anything for you yet. " + CAN_WATCH
    return "I'll tell you " + "; ".join(said) + "."


def _stop_tool(context, arguments: dict) -> str:
    """Tool stop_condition_watch: stops the watch his words name, or the only one, or the newest when he says
    "that"."""
    live = book(context).live(date.today())
    if not live:
        return "I'm not watching anything for you."
    words = set(re.findall(r"[a-z]+", str(arguments.get("question") or arguments.get("watch") or "").lower()))
    cold = any(w.startswith(("freez", "frost", "cold")) for w in words)
    rainy = any(w.startswith("rain") for w in words)
    named = [w for w in live if w.about and set(re.findall(r"[a-z]+", w.about)) & words
             or (w.kind == "freeze" and cold) or (w.kind == "rain" and rainy)]
    if len(named) > 1:
        return "Which one? " + "; ".join(describe(w, _unit(context)) for w in named) + "."
    chosen = named[0] if named else (live[-1] if len(live) == 1 or "that" in words else None)
    if chosen is None:
        return "Which one? I'm watching " + "; ".join(describe(w, _unit(context)) for w in live) + "."
    return _run(context, "condition_watch.remove", {"watch_id": chosen.watch_id})


def register_condition_watch_actions(registry) -> None:
    """Registers watch_condition, list_condition_watches and stop_condition_watch."""
    from core.assistant_actions import AssistantAction

    question = {"type": "object", "properties": {"question": {"type": "string", "description": "his words"}},
                "required": []}
    registry.register(AssistantAction(
        name="watch_condition", domain="world_intel",
        description="Watch a condition in his own world and tell him when it comes true: tonight's low, tomorrow's "
                    "rain, a pantry item running low, the flock's feed, or his water, food and fuel days.",
        parameters=question, handler=_watch_tool, prompt_arg="question",
        trigger_phrases=("tell me when", "tell me if it", "let me know when", "let me know if it", "warn me if",
                         "warn me when", "alert me when", "alert me if"),
        subjects=("watch",),
    ))
    registry.register(AssistantAction(
        name="list_condition_watches", domain="world_intel",
        description="What she's watching for him in his own world (tonight's low, rain, pantry, feed, supplies).",
        parameters={"type": "object", "properties": {}, "required": []}, handler=_list_tool,
        trigger_phrases=("what are you watching for me", "what am i having you watch", "what conditions are you watching"),
        subjects=("watch",),
    ))
    registry.register(AssistantAction(
        name="stop_condition_watch", domain="world_intel",
        description="Stop one of the conditions she's watching for him.",
        parameters=question, handler=_stop_tool, prompt_arg="question",
        trigger_phrases=("stop watching that", "stop telling me when", "don't tell me when", "never mind the watch"),
        subjects=("watch",),
    ))
