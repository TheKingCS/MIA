"""
core.user_sync
================

User Sync: where MIA gets to know a person (slice 3 of
docs/GLASSES_FIRST_BOOT_PLAN.md). The questions are written here, by
topic, not chosen by the model: it's the highest-stakes conversation she
has. Slice 3 is one topic end to end, Meals; slice 4 adds the rest to
TOPICS.

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
from datetime import datetime
from typing import Optional

from core import person_settings
from core.logger import get_logger

log = get_logger(__name__)

KEY = "user_sync.progress"

WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
MAX_DISHES = 6
MAX_NAME = 60

LATER = re.compile(r"(let'?s )?(finish|do this|do it|continue|pick (this|it) up) later|later|stop( for now)?|pause|not now", re.I)
SKIP = re.compile(r"skip( that( one)?| this( one)?| it)?|pass|next( question)?", re.I)
SKIP_TOPIC = re.compile(r"skip (this topic|the topic|meals|all of (this|it))", re.I)
YES = re.compile(r"(yes|yeah|yep|yup|sure|ok|okay|correct|right|perfect|good|great)?[ ,]*"
                 r"((that )?looks? (right|good)|that'?s (right|good|it)|sounds good|save (it|them|that)|all good)?( thanks| thank you)?", re.I)
DROP = re.compile(r"(not|no|drop|remove|skip|take off|forget|without)\s+(.+)", re.I)
RESUME = re.compile(r"(let'?s )?(keep going|continue|carry on|pick (this|it) up)( getting to know me)?|"
                    r"(keep |continue )?get(ting)? to know me|user sync", re.I)
NOTHING = re.compile(r"(no|nope|nah|none|nothing|not really|i don'?t( know)?|not sure|no thanks)", re.I)
NOT_DISHES = {"leftovers", "takeout", "take out", "takeaway", "whatever", "fast food", "eating out", "delivery"}
STOPWORDS = {"a", "an", "and", "the", "with", "of", "or", "on", "in", "my", "some", "sometimes", "usually", "for", "to", "de"}


# ------------------------------------------------------------------ the topics


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
    "meals": {
        "title": "Meals",
        "questions": [
            "What do you usually eat on weeknights?",
            "Is there a day you cook ahead or meal prep?",
            "Anything you avoid, or can't eat?",
        ],
        "extract": _extract_meals,
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
    """The one JSON object in a model's reply; None if there isn't one."""
    reply = re.sub(r"<think>.*?</think>", "", reply, flags=re.S)
    start, end = reply.find("{"), reply.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        got = json.loads(reply[start:end + 1])
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
    words = _words(fact)
    return bool(words) and len(words & _words(heard)) * 3 >= len(words) * 2


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


def _topic_now(progress: dict) -> Optional[str]:
    return next((t for t in TOPICS if (progress.get("topics") or {}).get(t, {}).get("status") not in ("done", "skipped")), None)


def _own(progress: dict, topic: str) -> dict:
    return progress.setdefault("topics", {}).setdefault(topic, {"status": "asking", "asked": 0, "answers": [], "chips": []})


def state(context) -> dict:
    """What a screen shows. `offer` is true for someone who hasn't begun."""
    progress = _progress(context)
    topic = _topic_now(progress)
    finished = topic is None
    begun = bool(progress.get("started_at"))
    out = {"done": finished, "begun": begun, "paused": bool(progress.get("paused")), "active": begun and not finished and not progress.get("paused"),
           "offer": not begun and not finished, "topic": topic, "title": "", "number": 0, "topics": len(TOPICS),
           "step": "done" if finished else "ask", "question": "", "heard": "", "chips": [], "percent": 100}
    if finished:
        return out
    now = (progress.get("topics") or {}).get(topic) or {"status": "asking", "asked": 0, "answers": [], "chips": []}
    questions = TOPICS[topic]["questions"]
    number = list(TOPICS).index(topic)
    answers = now.get("answers") or []
    out.update(title=TOPICS[topic]["title"], number=number + 1, heard=answers[-1]["a"] if answers else "",
               percent=round(100 * (number + min(now.get("asked", 0), len(questions)) / len(questions) / 2) / len(TOPICS)))
    if now.get("status") == "review":
        out.update(step="review", question="Here's what I've got. Does that look right?",
                   chips=[{"app": c["app"], "text": c["text"]} for c in now.get("chips") or []])
    else:
        out["question"] = questions[min(now.get("asked", 0), len(questions) - 1)]
    return out


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
        chips = [_chip("Memory", words, "memory.add", text=f"{TOPICS[topic]['title']}: {words}")]
    now.update(status="review", chips=chips)
    _save(context, progress)
    return _next_line(context)


def _finish_topic(context, progress: dict, topic: str, status: str, lead: str = "") -> str:
    now = _own(progress, topic)
    now.update(status=status, answers=[], chips=[])  # their words aren't kept past this
    if _topic_now(progress) is None:
        progress["finished_at"] = datetime.now().isoformat(timespec="seconds")
    _save(context, progress)
    return _next_line(context, lead)


# ------------------------------------------------------------------ the steps


def start(context) -> dict:
    """Begin, or pick up where it was left."""
    progress = _progress(context)
    progress.setdefault("started_at", datetime.now().isoformat(timespec="seconds"))
    progress["paused"] = False
    _save(context, progress)
    now = state(context)
    if now["done"]:
        return _result(context, "")
    return _result(context, f"Let's talk about {now['title'].lower()}. {now['question']}")


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
    topic = _topic_now(progress)
    words = " ".join(str(text or "").split()).strip(" .!?")
    if topic is None:
        return _result(context, "")
    if not words:
        return _result(context, "I didn't catch that.")
    if LATER.fullmatch(words):
        return _pause(context, progress)
    now = _own(progress, topic)
    if now["status"] == "review":
        if YES.fullmatch(words):
            return _approve(context, progress, topic)
        drop = DROP.fullmatch(words)
        if drop:
            return _drop(context, progress, topic, _chip_named(now["chips"], drop.group(2)))
        return _result(context, "Say looks right to save these, or tell me which one to drop.")
    if SKIP_TOPIC.fullmatch(words):
        return _result(context, _finish_topic(context, progress, topic, "skipped", "Skipped."))
    question = TOPICS[topic]["questions"][now["asked"]]
    now["asked"] += 1
    if not SKIP.fullmatch(words):
        now["answers"].append({"q": question, "a": words})
    return _result(context, _after_answer(context, progress, topic))


def choose(context, choice: str, index: int = -1) -> dict:
    """The same steps from a button: approve, drop, skip, later."""
    progress = _progress(context)
    topic = _topic_now(progress)
    if topic is None:
        return _result(context, "")
    if choice == "later":
        return _pause(context, progress)
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
