"""
core.user_sync
================

User Sync: where MIA gets to know a person (slices 3 and 4 of
docs/GLASSES_FIRST_BOOT_PLAN.md). The questions are written here, by
topic, not chosen by the model: it's the highest-stakes conversation she
has.

First the phone: only it can ask Android for a permission, so the phone
reports what's allowed (`report`) and the glasses show that, nothing
guessed. It never holds anything up: "skip" moves on.

For each topic:

1. She asks its questions, one at a time.
2. **The model extracts, the code decides.** The model gets the topic's
   answers and returns JSON in a fixed shape. The code keeps only what
   fits the shape and what the person really said (`_said`), so a guess
   never gets through.
3. Each fact becomes a chip: an existing action kind and its params.
   If the model gives nothing usable, or isn't there, the answer itself
   becomes a memory chip. She never fills a gap.
4. The person approves per topic (Zac, 2026-10-29). "Looks right" runs
   the chips through core/actions.py as hers, each one recorded and
   undoable; "not the tacos" drops one first. Nothing is written before
   that yes.
5. She offers to keep going or finish later (answer 3 in the plan), which
   is also the place to skip the next topic.

- `state(context)`: what a screen shows. Served as `/api/user-sync`.
- `start`, `reply(context, text)`, `choose(context, choice, index)`:
  the same steps by voice, by typing or by the glasses' two moves. Each
  returns `state` plus `say`, the line to speak.
- `hear(context, text)`: words from the glasses (core/glasses_voice.py),
  or None when they aren't for User Sync.

Each person's own, on their profile (core/person_settings.py), so it can
be left and picked up on any device. Answers stay only until the topic
is approved.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta
from typing import Optional

from core import person_settings
from core.child_accounts import is_child
from core.logger import get_logger

log = get_logger(__name__)

KEY = "user_sync.progress"

WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
MONTHS = ("january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
          "november", "december")
HOURS = ("twelve", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven")
MAX_DISHES = 6
MAX_NAME = 60
MAX_CHIPS = 8

# Only what the phone app really uses: it reads neither the calendar nor Health.
PHONE_ASKS = (("microphone", "Microphone"), ("notifications", "Notifications"), ("location", "Location"),
              ("photos", "Photos"), ("music", "Music"), ("glasses", "Glasses"))

LATER = re.compile(r"(let'?s )?(finish|do this|do it|continue|pick (this|it) up) later|later|stop( for now)?|pause|not now", re.I)
SKIP = re.compile(r"skip( that( one)?| this( one)?| it)?|pass|next( question)?", re.I)
SKIP_TOPIC = re.compile(r"skip (this topic|the topic|all of (this|it))", re.I)
YES = re.compile(r"(yes|yeah|yep|yup|sure|ok|okay|correct|right|perfect|good|great)?[ ,]*"
                 r"((that )?looks? (right|good)|that'?s (right|good|it)|sounds good|save (it|them|that)|all good)?( thanks| thank you)?", re.I)
DROP = re.compile(r"(not|no|drop|remove|skip|take off|forget|without)\s+(.+)", re.I)
RESUME = re.compile(r"(let'?s )?(keep going|continue|carry on|pick (this|it) up)( getting to know me)?|"
                    r"(keep |continue )?get(ting)? to know me|user sync", re.I)
NOTHING = re.compile(r"(no|nope|nah|none|nothing|not really|i don'?t( know)?|not sure|no thanks)", re.I)
NOT_DISHES = {"leftovers", "takeout", "take out", "takeaway", "whatever", "fast food", "eating out", "delivery"}
STOPWORDS = {"a", "an", "and", "the", "with", "of", "or", "on", "in", "my", "some", "sometimes", "usually", "for", "to", "de"}


# ------------------------------------------------------------------ the topics


def _remember(label: str, text: str) -> dict:
    return _chip("Memory", label, "memory.add", text=text)


def _mission(name: str, summary: str = "") -> dict:
    return _chip("Missions", name, "mission.add", name=name, summary=summary)


def _fact(value, heard: str) -> str:
    """One short thing they really said, or ""."""
    value = " ".join(str(value or "").split()).strip(" .,")
    return value if len(value) <= MAX_NAME and _said(value, heard) else ""


def _facts(value, heard: str) -> list[str]:
    return [v for v in (_fact(s, heard) for s in _strings(value)) if v]


def _day_said(day: str, heard: str) -> bool:
    return bool(re.search(rf"\b{day[:3]}[a-z]*day|\b{day[:3]}\b", heard.lower()))


def _days(value, heard: str) -> list[str]:
    """Weekdays they named, or that "Monday through Friday" covers."""
    days = [d for d in WEEKDAYS if d in [s.lower().rstrip("s") for s in _strings(value)]]
    spans = re.search(r"\b(weekdays|every day|everyday|daily|through|thru)\b|day to \w+day", heard.lower())
    return days if spans else [d for d in days if _day_said(d, heard)]


def _time(value, heard: str) -> str:
    """A time they said, digits or words, or ""."""
    value = str(value or "").strip().lower()
    match = re.fullmatch(r"(\d{1,2})(?::\d{2})?\s*([ap]\.?m\.?)?", value)
    if not match or int(match.group(1)) > 23:
        return ""
    hour = int(match.group(1)) % 12
    said = heard.lower()
    known = re.search(rf"\b({hour or 12}|{int(match.group(1))}|{HOURS[hour]})\b", said)
    return value if known or (hour == 0 and re.search(r"\b(noon|midnight)\b", said)) else ""


def _next_day(day: str) -> str:
    today = date.today()
    return (today + timedelta((WEEKDAYS.index(day) - today.weekday()) % 7)).isoformat()


def _next_month_day(day: int) -> str:
    today = date.today()
    year, month = today.year, today.month
    if day < today.day:
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return date(year, month, day).isoformat()


def _month_day(value) -> int:
    match = re.search(r"\d{1,2}", str(value or ""))
    day = int(match.group()) if match else 0
    return day if 1 <= day <= 28 else 0  # 29-31 aren't in every month: the person can set those


def _money_said(value, heard: str) -> float:
    try:
        amount = float(str(value or "").replace(",", "").strip(" $"))
    except ValueError:
        return 0.0
    return amount if amount > 0 and f"{amount:g}" in heard.replace(",", "") else 0.0


def _birthday(value, heard: str) -> tuple[str, str]:
    """(full date, as said): a date needs the year, and she won't make one up."""
    said = _fact(value, heard)
    found = re.fullmatch(rf"({'|'.join(MONTHS)}) (\d{{1,2}})(?:st|nd|rd|th)?,? (\d{{4}})", said.lower())
    if found:
        try:
            return date(int(found.group(3)), MONTHS.index(found.group(1)) + 1, int(found.group(2))).isoformat(), said
        except ValueError:
            pass
    return "", said


def _extract_routines(context, answers: list[dict]) -> Optional[list[dict]]:
    got = _ask_model(context, ROUTINES_PROMPT, answers)
    if got is None:
        return None
    heard = " ".join(a["a"] for a in answers)
    chips = []
    wake, bed = _time(got.get("wake"), heard), _time(got.get("bed"), heard)
    if wake:
        chips.append(_remember(f"Up around {wake}", f"Usually gets up around {wake}"))
    if bed:
        chips.append(_remember(f"Bed around {bed}", f"Usually goes to bed around {bed}"))
    for item in got.get("weekly") if isinstance(got.get("weekly"), list) else []:
        item = item if isinstance(item, dict) else {}
        what = _fact(item.get("what"), heard)
        day = str(item.get("day") or "").strip().lower().rstrip("s")
        if not what or day not in WEEKDAYS or not _day_said(day, heard):
            continue
        what = what[:1].upper() + what[1:]
        if is_child(context):  # the calendar is the household's
            chips.append(_remember(f"{what}, {day.capitalize()}s", f"{what} every {day.capitalize()}"))
            continue
        chips.append(_chip("Calendar", f"{what}, {day.capitalize()}s", "event.add", title=what, date=_next_day(day),
                           time=_time(item.get("time"), heard), recurrence="weekly"))
    for thing in _facts(got.get("morning"), heard):
        chips.append(_remember(f"Mornings: {thing}", f"A good morning has {thing}"))
    return chips or None


ROUTINES_PROMPT = """Read what a person said about their routines. Pull out only what they actually said.
Reply with JSON only, in exactly this shape:
{"wake": "", "bed": "", "weekly": [{"what": "", "day": "", "time": ""}], "morning": []}
- wake, bed: the usual time they get up and go to bed, like "7:00" or "10:30 pm".
- weekly: things that happen every week on a set day. day is the weekday's name; time like "18:30", or "".
- morning: short things that make a good morning for them.
Use [] or "" for anything they didn't say. Never guess, never add examples.

What they said:
"""


def _extract_work(context, answers: list[dict]) -> Optional[list[dict]]:
    got = _ask_model(context, WORK_PROMPT, answers)
    if got is None:
        return None
    heard = " ".join(a["a"] for a in answers)
    chips = []
    job = _fact(got.get("job"), heard)
    if job:
        chips.append(_remember(job, f"Work or school: {job}"))
    schedule = _fact(got.get("schedule"), heard)
    if schedule:
        chips.append(_remember(schedule, f"Work or school hours: {schedule}"))
    have = _mission_names(context)
    for thing in _facts(got.get("upcoming"), heard):
        name = thing[:1].upper() + thing[1:]
        if name not in have:
            chips.append(_mission(name, "From getting to know you."))
    return chips or None


WORK_PROMPT = """Read what a person said about their work or school. Pull out only what they actually said.
Reply with JSON only, in exactly this shape:
{"job": "", "schedule": "", "upcoming": []}
- job: what they do or study, in a few of their own words.
- schedule: their days and hours in their own words, like "Monday to Friday, 8 to 5".
- upcoming: big things coming up that they want kept track of, each a short name.
Use [] or "" for anything they didn't say. Never guess, never add examples.

What they said:
"""


def _extract_workouts(context, answers: list[dict]) -> Optional[list[dict]]:
    got = _ask_model(context, WORKOUTS_PROMPT, answers)
    if got is None:
        return None
    heard = " ".join(a["a"] for a in answers)
    chips = []
    fitness = getattr(context, "fitness", None)
    plan = (fitness.plan.get("training") or {}) if fitness is not None else {}
    split = [s[:1].upper() + s[1:] for s in _facts(got.get("split"), heard)][:7]
    days = _days(got.get("days"), heard)
    training = {}
    if len(split) > 1 and not plan.get("rotation"):  # never over a plan they already have
        training["rotation"] = [{"name": s, "exercises": []} for s in split]
    if days:
        training["days"] = ", ".join(d[:3].capitalize() for d in days)
    if training and fitness is not None:
        label = ", ".join(x for x in (", ".join(split) if "rotation" in training else "", training.get("days")) if x)
        chips.append(_chip("Workouts", label, "fitness.plan", changes={"training": training}))
    for thing in _facts(got.get("activities"), heard):
        chips.append(_remember(thing[:1].upper() + thing[1:], f"Trains by: {thing}"))
    goal = _fact(got.get("goal"), heard)
    if goal:
        name = goal[:1].upper() + goal[1:]
        if name not in _mission_names(context):
            chips.append(_mission(name, "What you're training toward."))
    return chips or None


WORKOUTS_PROMPT = """Read what a person said about how they train. Pull out only what they actually said.
Reply with JSON only, in exactly this shape:
{"split": [], "days": [], "activities": [], "goal": ""}
- split: the named training days in order, like ["Push", "Pull", "Legs"]. Only if they named them.
- days: the full names of the weekdays they train.
- activities: other things they do to stay active, in their own words, like "run" or "yoga".
- goal: what they're working toward, in a few of their own words.
Use [] or "" for anything they didn't say. Never guess, never add examples.

What they said:
"""


def _extract_hobbies(context, answers: list[dict]) -> Optional[list[dict]]:
    got = _ask_model(context, HOBBIES_PROMPT, answers)
    if got is None:
        return None
    heard = " ".join(a["a"] for a in answers)
    chips = [_remember(h[:1].upper() + h[1:], f"Enjoys {h}") for h in _facts(got.get("hobbies"), heard)]
    have = _mission_names(context)
    for thing in _facts(got.get("learning"), heard):
        name = f"Get better at {thing}"
        if name not in have:
            chips.append(_mission(name, "Something you said you're learning."))
    return chips or None


HOBBIES_PROMPT = """Read what a person said about what they do for fun. Pull out only what they actually said.
Reply with JSON only, in exactly this shape:
{"hobbies": [], "learning": []}
- hobbies: things they do for fun, each a short name.
- learning: things they're learning or want to get better at, each a short name.
Use [] for anything they didn't say. Never guess, never add examples.

What they said:
"""


def _extract_people(context, answers: list[dict]) -> Optional[list[dict]]:
    got = _ask_model(context, PEOPLE_PROMPT, answers)
    if got is None:
        return None
    heard = " ".join(a["a"] for a in answers)
    store = getattr(context, "relationships", None)
    have = {p.name.lower() for p in store.all_people()} if store is not None else set()
    chips = []
    known = False
    for person in got.get("people") if isinstance(got.get("people"), list) else []:
        person = person if isinstance(person, dict) else {}
        name = _fact(person.get("name"), heard)
        if not name:
            continue
        name = name[:1].upper() + name[1:]
        if name.lower() in have:
            known = True
            continue
        have.add(name.lower())
        who = _fact(person.get("who"), heard)
        birthday, said = _birthday(person.get("birthday"), heard)
        params = {"name": name, "relationship": who}
        if birthday:
            params["birthday"] = birthday
        elif said:
            params["notes"] = f"Birthday: {said}"
        chips.append(_chip("People", ", ".join(x for x in (name, who, said) if x), "person.add", **params))
    return chips or ([] if known else None)


PEOPLE_PROMPT = """Read what a person said about the people in their life. Pull out only what they actually said.
Reply with JSON only, in exactly this shape:
{"people": [{"name": "", "who": "", "birthday": ""}]}
- name: their name, or what the person calls them, like "Mom".
- who: how they're related, like "sister" or "best friend".
- birthday: as it was said, like "March 4" or "March 4, 1990".
Use [] or "" for anything they didn't say. Never guess, never add examples.

What they said:
"""


def _extract_money(context, answers: list[dict]) -> Optional[list[dict]]:
    got = _ask_model(context, MONEY_PROMPT, answers)
    if got is None:
        return None
    heard = " ".join(a["a"] for a in answers)
    chips = []
    have = _mission_names(context)
    for thing in _facts(got.get("saving_for"), heard):
        name = f"Save for {thing}"
        if name not in have:
            chips.append(_mission(name, "Something you said you're saving for."))
    for bill in got.get("bills") if isinstance(got.get("bills"), list) else []:
        bill = bill if isinstance(bill, dict) else {}
        name = _fact(bill.get("name"), heard)
        if not name:
            continue
        name = name[:1].upper() + name[1:]
        amount, day = _money_said(bill.get("amount"), heard), _month_day(bill.get("day"))
        if amount and day and re.search(rf"\b{day}(st|nd|rd|th)?\b", heard):
            chips.append(_chip("Budget", name, "bill.add", name=name, amount=amount, due_date=_next_month_day(day)))
        else:  # a bill needs both: without them it's only worth remembering
            chips.append(_remember(name, f"Wants to stay on top of {name}"))
    for thing in _facts(got.get("watch"), heard):
        chips.append(_remember(thing[:1].upper() + thing[1:], f"Wants to spend less on {thing}"))
    return chips or None


MONEY_PROMPT = """Read what a person said about their money. Pull out only what they actually said.
Reply with JSON only, in exactly this shape:
{"saving_for": [], "bills": [{"name": "", "amount": "", "day": ""}], "watch": []}
- saving_for: what they're saving for, each a short name.
- bills: bills they want to stay on top of. amount is the number; day is the day of the month, a number.
- watch: what they'd like to spend less on, each a short name.
Use [] or "" for anything they didn't say. Never guess, never add examples.

What they said:
"""


def _extract_meals(context, answers: list[dict]) -> Optional[list[dict]]:
    """Chips for Meals. None: nothing usable came back. []: all of it is already here."""
    got = _ask_model(context, MEALS_PROMPT, answers)
    if got is None:
        return None
    heard = " ".join(a["a"] for a in answers)
    chips = []
    have = _recipe_names(context)
    seen = set()
    known = False
    for dish in _strings(got.get("dishes")):
        name = dish[:1].upper() + dish[1:]
        known = known or name.lower() in have
        if len(name) > MAX_NAME or not _said(name, heard) or name.lower() in seen | have | NOT_DISHES:
            continue
        seen.add(name.lower())
        chips.append(_chip("Recipe book", name, "recipe.add", name=name, source="User Sync"))
        if len(chips) == MAX_DISHES:
            break
    day = str(got.get("prep_day") or "").strip().lower().rstrip("s")
    if day in WEEKDAYS and day in heard.lower():
        name = f"{day.capitalize()} meal prep"
        if name not in _mission_names(context):
            chips.append(_chip("Missions", name, "mission.add", name=name, summary="Cook ahead for the week."))
    for food in _strings(got.get("avoid")):
        if len(food) <= MAX_NAME and _said(food, heard):
            chips.append(_chip("Memory", f"Avoids {food}", "memory.add", text=f"Avoids {food} in food", category="Cooking"))
    return chips or ([] if known else None)


MEALS_PROMPT = """Read what a person said about their meals. Pull out only what they actually said.
Reply with JSON only, in exactly this shape:
{"dishes": ["..."], "prep_day": "...", "avoid": ["..."]}
- dishes: meals they make or eat, each a short name in their own words.
- prep_day: the one weekday they cook ahead or meal prep, or "" if they didn't name one.
- avoid: foods they avoid, dislike or can't eat.
Use [] or "" for anything they didn't say. Never guess, never add examples.

What they said:
"""

# id -> what she calls it, the questions, how it becomes chips.
TOPICS = {
    "routines": {
        "title": "Routines",
        "questions": [
            "What time do you usually get up, and go to bed?",
            "Is there anything you do every week on a set day?",
            "What makes a good morning for you?",
        ],
        "extract": _extract_routines,
    },
    "work": {
        "title": "Work",
        "questions": [
            "What do you do for work or school?",
            "Which days and hours are you usually there?",
            "Is anything big coming up that you'd like me to keep track of?",
        ],
        "extract": _extract_work,
    },
    "meals": {
        "title": "Meals",
        "questions": [
            "What do you usually eat on weeknights?",
            "Is there a day you cook ahead or meal prep?",
            "Anything you avoid, or can't eat?",
        ],
        "extract": _extract_meals,
    },
    "workouts": {
        "title": "Workouts",
        "questions": [
            "How do you train right now, if at all?",
            "Which days do you usually train?",
            "What are you working toward?",
        ],
        "extract": _extract_workouts,
    },
    "hobbies": {
        "title": "Hobbies",
        "questions": [
            "What do you do for fun?",
            "Is there something you're learning, or want to get better at?",
        ],
        "extract": _extract_hobbies,
    },
    "people": {
        "title": "People",
        "questions": [
            "Who are the people who matter most to you?",
            "Any birthdays you'd like me to remember?",
        ],
        "extract": _extract_people,
    },
    "money": {
        "title": "Money",
        "adult": True,  # a child doesn't see Budget (core/child_accounts.py)
        "questions": [
            "Are you saving for anything right now?",
            "Which bills do you always want to stay on top of? Tell me the amount and the day they're due.",
            "Is there anything you'd like to spend less on?",
        ],
        "extract": _extract_money,
    },
}


# ------------------------------------------------------------------ the model, checked


def _ask_model(context, prompt: str, answers: list[dict]) -> Optional[dict]:
    llm = getattr(context, "llm", None)
    if llm is None:
        return None
    said = "\n".join(f"Q: {a['q']}\nA: {a['a']}" for a in answers)
    try:
        reply = llm.generate(prompt + said)
    except Exception:
        log.exception("User Sync couldn't ask the model.")
        return None
    return _json_in(reply or "")


def _json_in(reply: str) -> Optional[dict]:
    """The first JSON object in a model's reply, whatever follows it; None if there isn't one."""
    reply = re.sub(r"<think>.*?</think>", "", reply, flags=re.S)
    start = reply.find("{")
    if start < 0:
        return None
    try:
        got = json.JSONDecoder().raw_decode(reply[start:])[0]
    except ValueError:
        return None
    return got if isinstance(got, dict) else None


def _strings(value) -> list[str]:
    if not isinstance(value, list):
        return []
    return [" ".join(v.split()).strip(" .,") for v in value if isinstance(v, str) and v.strip(" .,")]


def _words(text: str) -> set[str]:
    found = re.findall(r"[a-z']+", text.lower().replace("’", "'"))
    return {w.rstrip("s") for w in found if w not in STOPWORDS}


def _said(fact: str, heard: str) -> bool:
    """Most of a fact's words came from the person: "Chicken & rice bowls"
    from "chicken and rice" stands, a dish they never named doesn't."""
    numbers = set(re.findall(r"\d+", fact))
    if numbers - set(re.findall(r"\d+", heard)):
        return False
    words = _words(fact)
    return len(words & _words(heard)) * 3 >= len(words) * 2 if words else bool(numbers)


def _chip(app: str, label: str, kind: str, **params) -> dict:
    return {"app": app, "text": label, "kind": kind, "params": params}


def _recipe_names(context) -> set[str]:
    kitchen = getattr(context, "kitchen", None)
    return {r.name.lower() for r in kitchen.all_recipes()} if kitchen is not None else set()


def _mission_names(context) -> set[str]:
    missions = getattr(context, "missions", None)
    return {m.name for m in missions.all_missions()} if missions is not None else set()


# ------------------------------------------------------------------ progress


def _progress(context) -> dict:
    saved = person_settings.get(context, KEY) or {}
    return saved if isinstance(saved, dict) else {}


def _save(context, progress: dict) -> None:
    person_settings.put(context, KEY, progress)


def _topics(context) -> list[str]:
    return [t for t, topic in TOPICS.items() if not (topic.get("adult") and is_child(context))]


def _topic_now(context, progress: dict) -> Optional[str]:
    return next((t for t in _topics(context) if (progress.get("topics") or {}).get(t, {}).get("status") not in ("done", "skipped")), None)


def _own(progress: dict, topic: str) -> dict:
    return progress.setdefault("topics", {}).setdefault(topic, {"status": "asking", "asked": 0, "answers": [], "chips": []})


def state(context) -> dict:
    """What a screen shows. `offer` is true for someone who hasn't begun."""
    progress = _progress(context)
    topic = _topic_now(context, progress)
    finished = topic is None
    begun = bool(progress.get("started_at"))
    order = _topics(context)
    out = {"done": finished, "begun": begun, "paused": bool(progress.get("paused")), "active": begun and not finished and not progress.get("paused"),
           "offer": not begun and not finished, "topic": topic, "title": "", "number": 0, "topics": len(order),
           "step": "done" if finished else "ask", "question": "", "heard": "", "chips": [], "rows": [], "percent": 100}
    if finished:
        return out
    now = (progress.get("topics") or {}).get(topic) or {"status": "asking", "asked": 0, "answers": [], "chips": []}
    questions = TOPICS[topic]["questions"]
    number = order.index(topic)
    answers = now.get("answers") or []
    out.update(title=TOPICS[topic]["title"], number=number + 1, heard=answers[-1]["a"] if answers else "",
               percent=round(100 * (number + min(now.get("asked", 0), len(questions)) / len(questions) / 2) / len(order)))
    if not progress.get("phone_done"):
        out.update(step="phone", title="Your phone", question="First, your phone. Tap Allow on it for each of these.", rows=_rows(progress))
    elif progress.get("between"):
        out.update(step="next", question=f"Next is {TOPICS[topic]['title'].lower()}. Keep going, or finish later?")
    elif now.get("status") == "review":
        out.update(step="review", question="Here's what I've got. Does that look right?",
                   chips=[{"app": c["app"], "text": c["text"]} for c in now.get("chips") or []])
    else:
        out["question"] = questions[min(now.get("asked", 0), len(questions) - 1)]
    return out


def _rows(progress: dict) -> list[dict]:
    """What the phone has really reported, nothing guessed."""
    told = progress.get("permissions") or {}
    return [{"id": key, "label": label, "status": "allowed" if told.get(key) else ("not yet" if key in told else "waiting")}
            for key, label in PHONE_ASKS]


def _result(context, say: str) -> dict:
    return {**state(context), "say": say}


def _next_line(context, lead: str = "") -> str:
    now = state(context)
    if now["done"]:
        return " ".join(x for x in (lead, "That's everything for now. You can tell me more any time.") if x)
    return " ".join(x for x in (lead, now["question"]) if x)


def _after_answer(context, progress: dict, topic: str) -> str:
    """The next question, or the topic's chips once its questions are done."""
    now = _own(progress, topic)
    questions = TOPICS[topic]["questions"]
    if now["asked"] < len(questions):
        _save(context, progress)
        return _next_line(context)
    answers = [a for a in now["answers"] if not NOTHING.fullmatch(a["a"].strip(" .!"))]
    if not answers:
        return _finish_topic(context, progress, topic, "done")
    chips = TOPICS[topic]["extract"](context, answers)
    if chips == []:
        return _finish_topic(context, progress, topic, "done")
    if chips is None:  # nothing fit: keep their words, invent nothing
        words = " ".join(a["a"] for a in answers)[:300]
        chips = [_remember(words, f"{TOPICS[topic]['title']}: {words}")]
    now.update(status="review", chips=chips[:MAX_CHIPS])
    _save(context, progress)
    return _next_line(context)


def _finish_topic(context, progress: dict, topic: str, status: str, lead: str = "") -> str:
    now = _own(progress, topic)
    now.update(status=status, answers=[], chips=[])  # their words aren't kept past this
    if _topic_now(context, progress) is None:
        progress["finished_at"] = datetime.now().isoformat(timespec="seconds")
    else:
        progress["between"] = True
    _save(context, progress)
    return _next_line(context, lead)


# ------------------------------------------------------------------ the steps


def start(context) -> dict:
    """Begin, or pick up where it was left."""
    progress = _progress(context)
    progress.setdefault("started_at", datetime.now().isoformat(timespec="seconds"))
    progress["paused"] = False
    progress.pop("between", None)
    _save(context, progress)
    now = state(context)
    if now["done"]:
        return _result(context, "")
    return _result(context, _opening(now))


def _opening(now: dict) -> str:
    return now["question"] if now["step"] == "phone" else f"Let's talk about {now['title'].lower()}. {now['question']}"


def _phone_done(context, progress: dict) -> dict:
    progress["phone_done"] = True
    _save(context, progress)
    return _result(context, _opening(state(context)))


def _keep_going(context, progress: dict) -> dict:
    progress.pop("between", None)
    _save(context, progress)
    return _result(context, _opening(state(context)))


def report(context, granted: dict) -> dict:
    """What the phone says is allowed. Everything allowed moves on by itself."""
    progress = _progress(context)
    told = progress.setdefault("permissions", {})
    music = getattr(context, "music", None)
    if music is not None and (granted or {}).get("music") and not told.get("music"):
        music.scan_library()  # the songs already on this phone
    told.update({key: bool(granted[key]) for key, _label in PHONE_ASKS if key in (granted or {})})
    if _topic_now(context, progress) is not None and not progress.get("phone_done") and all(told.get(k) for k, _l in PHONE_ASKS):
        return _phone_done(context, progress)
    _save(context, progress)
    return _result(context, "")


def _pause(context, progress: dict) -> dict:
    progress["paused"] = True
    _save(context, progress)
    return _result(context, "Of course. We'll pick this up whenever you like.")


def _approve(context, progress: dict, topic: str) -> dict:
    """The person's yes: each chip through the action contract, as theirs."""
    actions = getattr(context, "actions", None)
    if actions is None:
        return _result(context, "I can't save that here. Nothing was changed.")
    now = _own(progress, topic)
    saved, failed = 0, []
    for chip in now["chips"]:
        try:
            proposal = actions.approve(context, actions.propose(context, chip["kind"], chip["params"], proposed_by="mia").proposal_id)
        except Exception:
            log.exception("User Sync couldn't save %s.", chip["kind"])
            failed.append(chip)
            continue
        if proposal.status == "executed":
            saved += 1
        else:
            failed.append(chip)
    if failed:  # what didn't save stays on screen, never lost
        now["chips"] = failed
        _save(context, progress)
        return _result(context, f"Saved {saved}. {len(failed)} didn't save. Say looks right to try again, or drop it.")
    return _result(context, _finish_topic(context, progress, topic, "done", f"Saved {saved}."))


def _drop(context, progress: dict, topic: str, index: int) -> dict:
    chips = _own(progress, topic)["chips"]
    if not 0 <= index < len(chips):
        return _result(context, "Which one should I drop?")
    gone = chips.pop(index)
    _save(context, progress)
    if not chips:
        return _result(context, _finish_topic(context, progress, topic, "done", "Dropped."))
    return _result(context, f"Dropped {gone['text']}. Does the rest look right?")


def _chip_named(chips: list[dict], words: str) -> int:
    wanted = _words(re.sub(r"^(the|that|this|one)\b", "", words.strip()))
    if not wanted:
        return -1
    found = [i for i, c in enumerate(chips) if wanted & _words(c["text"])]
    return found[0] if len(found) == 1 else -1


def reply(context, text: str) -> dict:
    """What the person said or typed, wherever they are in it."""
    progress = _progress(context)
    topic = _topic_now(context, progress)
    words = " ".join(str(text or "").split()).strip(" .!?")
    if topic is None:
        return _result(context, "")
    if not words:
        return _result(context, "I didn't catch that.")
    if LATER.fullmatch(words):
        return _pause(context, progress)
    if not progress.get("phone_done"):
        if SKIP.fullmatch(words) or YES.fullmatch(words) or NOTHING.fullmatch(words):
            return _phone_done(context, progress)
        return _result(context, "Tap Allow on your phone, or say skip.")
    if progress.get("between"):
        if YES.fullmatch(words) or RESUME.fullmatch(words):
            return _keep_going(context, progress)
        if SKIP.fullmatch(words):
            return _result(context, _finish_topic(context, progress, topic, "skipped", "Skipped."))
        return _result(context, "Say keep going, skip, or let's finish later.")
    now = _own(progress, topic)
    if now["status"] == "review":
        if YES.fullmatch(words):
            return _approve(context, progress, topic)
        drop = DROP.fullmatch(words)
        if drop:
            return _drop(context, progress, topic, _chip_named(now["chips"], drop.group(2)))
        return _result(context, "Say looks right to save these, or tell me which one to drop.")
    if SKIP_TOPIC.fullmatch(words) or words.lower() == f"skip {TOPICS[topic]['title'].lower()}":
        return _result(context, _finish_topic(context, progress, topic, "skipped", "Skipped."))
    question = TOPICS[topic]["questions"][now["asked"]]
    now["asked"] += 1
    if not SKIP.fullmatch(words):
        now["answers"].append({"q": question, "a": words})
    return _result(context, _after_answer(context, progress, topic))


def choose(context, choice: str, index: int = -1) -> dict:
    """The same steps from a button: approve, drop, skip, continue, later."""
    progress = _progress(context)
    topic = _topic_now(context, progress)
    if topic is None:
        return _result(context, "")
    if choice == "later":
        return _pause(context, progress)
    if not progress.get("phone_done"):
        return _phone_done(context, progress) if choice == "skip" else _result(context, "")
    if progress.get("between"):
        if choice == "continue":
            return _keep_going(context, progress)
        return _result(context, _finish_topic(context, progress, topic, "skipped", "Skipped.")) if choice == "skip" else _result(context, "")
    now = _own(progress, topic)
    if choice == "approve" and now["status"] == "review":
        return _approve(context, progress, topic)
    if choice == "drop" and now["status"] == "review":
        return _drop(context, progress, topic, index)
    if choice == "skip" and now["status"] != "review":
        return reply(context, "skip")
    return _result(context, "")


def hear(context, text: str) -> Optional[dict]:
    """Words from the glasses, if they're for User Sync."""
    now = state(context)
    if now["active"]:
        return reply(context, text)
    words = " ".join(str(text or "").split()).strip(" .!?")
    if not now["done"] and RESUME.fullmatch(words):
        return start(context)
    return None
