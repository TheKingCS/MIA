"""
core.reminders_view
=====================

His reminders and the small everyday turns around them, in code (the live sweep, 2026-11-26):

- `listing`: "what reminders do I have?" (it had named only the wake-up alarm): the calendar's reminders still to
  come, the repeating ones with how often, and his alarms;
- `cancel`: "cancel the oil reminder" (it had said "it's not a reminder for the truck's oil change"): the one whose
  title holds every word he said, by its id, through the action contract (event.delete / alarm.delete: recorded and
  undoable); two that fit are asked about with their days; none, and the model has it;
  "turn off all reminders" lists them and asks which, never deleting them all on one sentence;
- `greeting`: "good morning" (it had said "I didn't get an answer together for that one"): back in kind, with the
  morning briefing's day when it's morning (core/morning_briefing.briefing);
- `yesterday`: "what did I do yesterday?" (it had said nothing's kept): yesterday's wins in a few words
  (core/life_events.WINS, as the evening wrap counts them), never something taken back since;
- `last_done` ("when did I last change the oil?", from his maintenance record) and `in_a_while` ("remind me in 2
  hours to ...", the clock worked out in code), from the full sweep of 2026-11-26;
- the automation asks she mustn't claim (the automation sweep, 2026-11-26): `stop_reminding` stops only one that's
  there, `TRACK_SPENDING` and `MORNING_ROUTINE` say what she does, `when_paid` his next payday (she can't see pay
  arrive), and `bill_reminder` rent or a bill as a bill.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

AHEAD_DAYS = 60
SHOWN = 8


def _events(context, today: date) -> list:
    """The calendar's reminders still to come: repeating ones, and one-offs from today on (within AHEAD_DAYS)."""
    calendar = getattr(context, "calendar", None)
    if calendar is None:
        return []
    end = (today + timedelta(days=AHEAD_DAYS)).isoformat()
    return [e for e in calendar.all_events() if e.recurrence or today.isoformat() <= (e.date or "") <= end]


def _alarms(context) -> list:
    """His alarms that are on."""
    alarms = getattr(context, "alarms", None)
    try:
        return [a for a in alarms.all_alarms() if a.enabled] if alarms is not None else []
    except Exception:  # noqa: BLE001
        return []


def _when(event, today: date) -> str:
    """Pure logic. "every week", "every two weeks", "tomorrow at 09:00", "on Dec 3"."""
    if event.recurrence:
        return {"daily": "every day", "weekly": "every week", "biweekly": "every two weeks", "monthly": "every month",
                "yearly": "every year"}.get(event.recurrence, f"every {event.recurrence}")
    day = date.fromisoformat(event.date[:10])
    said = "today" if day == today else "tomorrow" if day == today + timedelta(days=1) else f"on {day:%b} {day.day}"
    return said + (f" at {event.time}" if event.time else "")


def listing(context, today: Optional[date] = None) -> str:
    """For "what reminders do I have?"."""
    today = today or date.today()
    events = sorted(_events(context, today), key=lambda e: (not e.recurrence, e.date or ""))
    alarms = _alarms(context)
    if not events and not alarms:
        return "You don't have any reminders. Say one, like \"remind me every Friday to check the oil\"."
    parts = [f"{e.title} ({_when(e, today)})" for e in events[:SHOWN]]
    parts += [f"the {a.label} alarm at {a.time}" for a in alarms[:SHOWN]]
    more = len(events) + len(alarms) - len(parts)
    return "Your reminders: " + "; ".join(parts) + (f"; and {more} more" if more > 0 else "") + "."


def _words(text: str) -> set:
    """Pure logic. A title's or a request's words, small ones left out."""
    return {w for w in re.findall(r"[a-z]+", (text or "").lower()) if len(w) > 2} - {
        "the", "my", "reminder", "reminders", "alarm", "cancel", "delete", "remove", "stop", "turn", "off", "that",
        "about", "for", "to", "please", "mia"}


def cancel(context, words: str, today: Optional[date] = None) -> Optional[str]:
    """For "cancel the oil reminder": the one reminder or alarm whose title holds every word he said, cancelled by
    its id through the action contract (undoable); the choice when several fit; for "all", the list and a question.
    None when no words are left to match or none fits (the model's then); with no actions engine here, where to
    remove it."""
    today = today or date.today()
    if re.search(r"\b(?:all|every|everything)\b", words or "", re.I):
        found = listing(context, today)
        return found + " Which should I cancel? Say \"cancel the ... reminder\" for each, so none goes by accident."
    want = _words(words)
    if not want:
        return None
    # every word he said is in its title (never one shared word: "the oil change reminder" isn't "Change the filter")
    events = [e for e in _events(context, today) if want <= _words(e.title)]
    alarms = [a for a in _alarms(context) if want <= _words(a.label)]
    hits = [("event.delete", {"event_id": e.event_id}, e.title, _when(e, today)) for e in events] + \
        [("alarm.delete", {"alarm_id": a.alarm_id}, f"the {a.label} alarm", a.time) for a in alarms]
    if not hits:
        return None  # nothing it can name for sure: the model's (a maintenance task, a watch, a far-off reminder)
    if len(hits) > 1:
        return "Which one? " + "; ".join(f"{name} ({when})" for _k, _p, name, when in hits) + "."
    kind, params, name, when = hits[0]
    actions = getattr(context, "actions", None)
    if actions is None:
        return f"I found {name}, but I can't cancel it from here: remove it on the Calendar page."
    from core.actions import ActionError

    try:  # his own request, through the action contract: recorded, and "undo that" brings it back
        done = actions.approve(context, actions.propose(context, kind, params).proposal_id)
    except ActionError as problem:
        return str(problem)
    repeats = " It was a repeating one; the whole series is gone." if "every" in when else ""
    return f"Cancelled {name}.{repeats} Say \"undo that\" to bring it back." if done.status == "executed" else \
        (done.result or "I couldn't cancel it.")


def greeting(context, words: str, now: Optional[datetime] = None) -> str:
    """Back in kind; in the morning with the briefing's day (weather and what's first) when there is one."""
    now = now or datetime.now()
    said = (words or "").lower()
    if "morning" in said and now.hour < 12:
        try:
            from core.morning_briefing import briefing

            day = briefing(context, now)
            if day:
                return day
        except Exception:  # noqa: BLE001
            log.exception("Greeting: the briefing couldn't be read")
        return "Good morning. Nothing on today's list yet. What's first?"
    part = "morning" if now.hour < 12 else "afternoon" if now.hour < 17 else "evening"
    if re.search(r"\bgood (?:morning|afternoon|evening)\b", said):
        return f"Good {part}. What can I do for you?"
    return "Hey. What can I do for you?"


def yesterday(context, today: Optional[date] = None) -> str:
    """For "what did I do yesterday?": yesterday's wins counted by kind (core/life_events.WINS), never one taken
    back since."""
    from core import life_events

    day = (today or date.today()) - timedelta(days=1)
    try:
        events = [e for e in life_events.events_for(context, since=day.isoformat(), until=day.isoformat())
                  if e.type not in life_events.AUDIT_ONLY]
    except Exception:  # noqa: BLE001
        log.exception("Yesterday couldn't be read")
        events = []
    try:  # what's been taken back since, today included, doesn't count
        later = life_events.events_for(context, since=day.isoformat())
    except Exception:  # noqa: BLE001
        later = events
    taken_back = life_events.reversed_ids(later)
    kept = [e for e in events if e.event_id not in taken_back and e.type in life_events.WINS]
    if not kept:
        return f"Nothing's logged for yesterday ({day:%A}). Tell me what you do as you go, and I'll keep the day."
    from core.evening_wrap import _count

    totals = life_events.counts(kept)
    said = ", ".join(_count(n, life_events.TYPES.get(t, t)) for t, n in sorted(totals.items(), key=lambda kv: -kv[1])[:6])
    return f"Yesterday ({day:%A}): {said}."


TRACK_SPENDING = ("Not from your bank yet: bank linking stays off until MIA's further along, so nothing comes in on its "
                  "own. What I do keep: what you tell me (\"I spent $30 on groceries\"), receipts in your Inbox (an "
                  "emailed one I file, one you drop in I read and put to you to file), and your bills as they come due. Ask \"how much did I spend "
                  "last month?\" any time, or say \"every month tell me how much I spent\" and I'll send it on the 1st.")
MORNING_ROUTINE = ("Two ways. Say \"every morning tell me the weather and my day\" and I'll send that each morning. And "
                   "for something you do each morning, say \"add a routine: morning chores, once a day\" and I'll keep "
                   "it and count the mornings you do it.")


def _bill_named(context, words: str):
    """A bill of his whose name holds every word he said, or None."""
    want = _words(words)
    budget = getattr(context, "budget", None)
    try:
        bills = budget.all_bills() if budget is not None and want else []
    except Exception:  # noqa: BLE001
        bills = []
    hits = [b for b in bills if want <= _words(b.name) | {"bill", "pay"}]
    return hits[0] if len(hits) == 1 else None


def stop_reminding(context, words: str, today: Optional[date] = None) -> str:
    """For "stop reminding me to take out the trash": the reminder his words name cancelled (`cancel`); a bill of his
    named, that its reminders come with the bill; or that there's none about it, never a claim that one stopped
    (the automation sweep, 2026-11-26: "I'll stop reminding you" with nothing set)."""
    found = cancel(context, words, today)
    if found:
        return found
    bill = _bill_named(context, words)
    if bill is not None:  # a bill's reminders come with the bill
        return (f"That's your {bill.name} bill: its reminders come with it. Mark it paid when you pay, or say "
                f"\"delete the {bill.name} bill\" if you don't have it any more.")
    want = re.sub(r"^(?:the|my|a)\s+", "", (words or "").strip(" .?!"), flags=re.I) if _words(words) else ""
    listed = listing(context, today)
    return (f"I don't have a reminder about {want or 'that'}, so there's nothing to stop. " + listed) if want else listed


def bill_reminder(what: str, day: str = "") -> str:
    """For "remind me on the 1st of every month to pay rent": a bill reminds him itself, so he's told how to add it,
    due on the day he said (the automation sweep, 2026-11-26: it had become an alarm at midnight)."""
    thing = re.sub(r"^\s*pay (?:the |my )?", "", what or "", flags=re.I).strip(" .") or "it"
    due = {"first": "1st"}.get((day or "").lower(), day or "1st")
    return (f"Add {thing} as a bill and I'll remind you before it's due each month, and count it when you pay: say "
            f"\"add a bill: {thing}, $amount, due the {due}, monthly\" with its amount.")


def when_paid(context, what: str) -> str:
    """For "when I get paid, remind me to put 10% in savings": she can't see pay arrive (no bank link), so his next
    payday from his own pay (Salary income, never rent or egg sales), and the words to put it on his calendar that
    day."""
    budget = getattr(context, "budget", None)
    sources = []
    try:
        sources = [s for s in budget.all_income_sources() if not getattr(s, "entity_id", "")
                   and str(getattr(s, "category", "Salary") or "Salary") == "Salary"] if budget else []  # his pay only
    except Exception:  # noqa: BLE001
        sources = []
    from core import money_ahead

    ahead = [m for m in money_ahead.flows([], sources, [], date.today(), 9) if m["amount"] > 0 and m["note"] != "late"]
    names = {s.name: s for s in sources}
    dated = [(m["day"], names[m["what"]]) for m in ahead if m["what"] in names]  # the next one from today, never past
    task = what.strip(" .") or "that"
    if not dated:
        return (f"I can't see your pay arrive (no bank is linked), and you don't have a payday in Money yet. Add your "
                f"pay as income with how often it comes, and I'll tell you its next day.")
    day, source = dated[0]
    how = getattr(source, "recurrence", "") or "once"
    return (f"I can't see your pay arrive (no bank is linked), but your {source.name} pay is next due {day:%A, %B} "
            f"{day.day} ({how}). Say \"add {task} to my calendar on {day:%B} {day.day}\" and I'll put it there.")


_BARE_VERBS = frozenset({"run", "work", "go", "eat", "call", "see", "do", "make", "check", "clean", "fix", "use"})


def _stem(word: str) -> str:
    """Pure logic. A word's stem, the same for each tense ("changed", "changing", "change" are all "chang")."""
    for end in ("ing", "ed", "es", "s", "e"):
        if word.endswith(end) and len(word) - len(end) >= 3:
            return word[:-len(end)]
    return word


def _stems(text: str) -> set:
    """Pure logic. A phrase's word stems, small and asking ones out ("changed the oil" and "Oil change" agree)."""
    words = set(re.findall(r"[a-z]+", (text or "").lower())) - {
        "the", "my", "a", "an", "in", "on", "of", "for", "did", "i", "we", "last", "time", "our", "do", "get", "got",
        "have", "had", "it", "was", "were"}
    return {_stem(w) for w in words}


def last_done(context, words: str, today: Optional[date] = None) -> Optional[str]:
    """For "when did I last change the oil?" (the full sweep, 2026-11-26: "about 3 months ago", made up): his
    maintenance tasks whose title (with its asset's name) holds every word he said, any tense ("changed the oil" is
    "Oil change"), and when each was last done, from the record; None when none fits or he said one bare verb ("when
    did I last run?"), so the model has it."""
    today = today or date.today()
    maintenance = getattr(context, "maintenance", None)
    want = _stems(words)
    if maintenance is None or not want:
        return None
    if len(want) == 1 and next(iter(want)) in {_stem(v) for v in _BARE_VERBS}:
        return None  # "when did I last run?" is never "Run generator"
    hits = []
    for task in maintenance.all_tasks():
        asset = maintenance.get_asset(task.asset_id) if hasattr(maintenance, "get_asset") else None
        has = _stems(task.title) | _stems(getattr(asset, "name", "") if asset else "")
        if want <= has:
            hits.append((task, asset))
    if not hits:
        return None
    parts = []
    for task, asset in hits[:3]:
        name = task.title + (f" ({asset.name})" if asset is not None else "")
        if not task.last_completed:
            parts.append(f"{name}: never logged as done. Tell me when you do it (\"I did the {task.title.lower()}\").")
            continue
        when = date.fromisoformat(str(task.last_completed)[:10])
        ago = (today - when).days
        since = "" if ago < 0 else ", today" if ago == 0 else ", yesterday" if ago == 1 else f", {ago} days ago"
        parts.append(f"{name}: last done {when:%B} {when.day}, {when.year}{since}.")
    return " ".join(parts)


_SPOKEN = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "ten": 10, "fifteen": 15,
           "twenty": 20, "thirty": 30, "forty": 40, "forty-five": 45, "ninety": 90}


def minutes_in(spec: str) -> Optional[float]:
    """Pure logic. The minutes in "2 hours", "an hour and a half", "a half hour", "2 hours and 30 minutes", "ninety
    minutes", "half an hour" (core/clock.WORD_NUMBERS for the words); None when it can't be read."""
    from core.clock import WORD_NUMBERS

    said = " ".join((spec or "").lower().split())
    said = re.sub(r"\b(?:half an hour|a half hour|half hour)\b", "30 minutes", said)
    total, found = 0.0, False
    for amount, unit, half in re.findall(r"(\d+(?:\.\d+)?|[a-z-]+) (hours?|hrs?|minutes?|mins?)( and a half)?", said):
        n = float(amount) if amount[0].isdigit() else WORD_NUMBERS.get(amount)
        if n is None:
            return None
        n += 0.5 if half else 0
        total += n * (60 if unit.startswith("h") else 1)
        found = True
    return total if found else None


def in_a_while(context, amount: str, unit: str, what: str, now: Optional[datetime] = None) -> Optional[str]:
    """For "remind me in 2 hours to check the oven" (the full sweep, 2026-11-26: the model worked the clock out
    itself): an alarm at now plus that (`minutes_in`: "an hour and a half", "2 hours and 30 minutes"), through
    add_alarm (undoable, one-shot); None past 23 hours (a calendar day's, the model's) or without the alarm tool."""
    from datetime import timedelta

    now = now or datetime.now()
    minutes = minutes_in(f"{amount} {unit}")
    if minutes is None:
        return None
    if not 0 < minutes <= 23 * 60:
        return None
    at = now + timedelta(minutes=minutes)
    actions = getattr(context, "assistant_actions", None)
    if actions is None:
        return None
    label = what.strip(" .!?")[:60]
    said = actions.execute(context, "add_alarm", {"label": label[:1].upper() + label[1:], "time": f"{at:%H:%M}"})
    return said + (" That's tomorrow." if at.date() != now.date() else "")  # the alarm's own reply says its time


# what "when did I last ..." asks of his history, beyond the maintenance tasks: (his words, the history's kinds)
HISTORY_ASKS = (
    (r"work(?:ed)? out|workout|lift(?:ed)?|train(?:ed)?|exercis(?:e|ed)|(?:go|went) to the gym",
     ("workout_logged", "training_done"), "worked out"),
    (r"(?:collect(?:ed)?|g[eo]t|gather(?:ed)?) (?:the |any )?eggs", ("eggs_collected",), "collected eggs"),
    (r"(?:catch|caught) (?:a |any )?fish|(?:go|went) fishing", ("fish_caught",), "caught a fish"),
    (r"pa(?:y|id) (?:a |any )?bills?$", ("bill_paid",), "paid a bill"),
    (r"harvest(?:ed)?", ("harvest",), "harvested"),
    (r"plant(?:ed)? (?:anything|something|seeds)", ("batch_planted",), "planted"),
    (r"cook(?:ed)?|ma(?:k|d)e dinner", ("meal_logged",), "cooked"),
    (r"finish(?:ed)? a (?:build|project)", ("build_finished", "project_completed"), "finished a build or project"),
)


def last_in_history(context, words: str, today: Optional[date] = None) -> Optional[str]:
    """For "when did I last work out?" / "... collect eggs" / "... catch a fish" / "... pay a bill" (the model had
    guessed): the latest of that kind in his history (core/life_events, never one taken back), on the day it happened
    (a backdated log's own date) and what it was; "pay the electric bill", "pay rent" or "pay the truck" from that bill's or loan's own
    record; that none is
    logged when there's none; None when his words aren't one of HISTORY_ASKS."""
    from core import life_events

    today = today or date.today()
    said = " ".join((words or "").lower().split())
    bill = re.fullmatch(r"pa(?:y|id) (?:the |my |on (?:the |my )?)?(?P<name>[\w' -]+?)(?: bill| payment)?", said)
    if bill:  # "when did I last pay the electric bill?": the bill's own record
        budget = getattr(context, "budget", None)
        want = _stems(bill.group("name"))
        hits = [b for b in (budget.all_bills() if budget is not None else []) if want and want <= _stems(b.name)]
        if len(hits) == 1:
            paid = hits[0].last_paid_date
            if not paid:
                return f"{hits[0].name} isn't marked paid yet."
            when = date.fromisoformat(str(paid)[:10])
            return f"You last paid {hits[0].name} on {when:%A, %B} {when.day}."
        debts = [d for d in (budget.all_debts() if budget is not None and hasattr(budget, "all_debts") else [])
                 if want and want <= _stems(d.name) | _stems(getattr(d, "debt_type", ""))]
        if len(debts) == 1:  # "when did I last pay the truck?": the loan's own record
            paid = debts[0].last_payment_date
            if not paid:
                return f"No payment on {debts[0].name} is logged yet."
            when = date.fromisoformat(str(paid)[:10])
            return f"You last paid on {debts[0].name} on {when:%A, %B} {when.day}."
        if want and re.search(r"\b(?:bill|payment)$", said):
            return None  # a bill or payment he named that isn't one of his: the model's
        # otherwise ("pay a bill", "pay any bills", a name that's none of his): the history's kinds below
    for pattern, types, did in HISTORY_ASKS:
        if not re.fullmatch(rf"(?:{pattern})(?: today| yesterday)?", said):
            continue
        try:
            events = life_events.events_for(context, types=types + ("undone",))
        except Exception:  # noqa: BLE001
            log.exception("Couldn't read the history for %s", did)
            return None
        taken_back = life_events.reversed_ids(events)
        def day(e) -> str:
            """The day it happened (a backdated log's own date), never only when it was written down."""
            return str((e.payload or {}).get("date") or e.at)[:10]

        kept = sorted((e for e in events if e.type in types and e.event_id not in taken_back), key=day)
        if not kept:
            return f"I don't have a time you {did} logged yet. Tell me when you do, and I'll keep it."
        last = kept[-1]
        when = date.fromisoformat(day(last))
        ago = (today - when).days
        since = "" if ago < 0 else " (today)" if ago == 0 else " (yesterday)" if ago == 1 else f" ({ago} days ago)"
        said_it = (last.summary or "").rstrip(".")
        if ":" in said_it:  # "Worked out: Push day, 40 min" is "Push day, 40 min"
            said_it = said_it.split(":", 1)[1].strip()
        elif said_it.lower().split(" ", 1)[0] == did.split()[0]:  # "Caught a bass" is "a bass"
            said_it = said_it.split(" ", 1)[1] if " " in said_it else ""
        empty = not said_it or said_it.lower() in ("a session", "a meal", "logged a meal")
        what = "" if empty else f": {said_it}"
        return f"You last {did} on {when:%A, %B} {when.day}{since}{what}."
    return None
