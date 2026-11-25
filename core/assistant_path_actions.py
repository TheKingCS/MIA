"""
core.assistant_path_actions
=============================

Learning paths by voice (DEC-0112; core/paths.py): any desire, the same loop.
"I want to learn guitar" starts the guitar program; "I want to learn to weld",
with no program for it, has MIA draft one (grounded in her specialists' notes)
and describe it, and "start it" starts it. Then lessons, practice, checks and
progress work the same for every path.

- `start_learning`: a built-in program, a draft of theirs, or a new draft.
- `learning_lesson`: the next lesson for where they are, or one named (guitar
  also answers a chord's shape).
- `log_practice`: a practice session on a path (the only one started, or the
  one named).
- `learning_check`: a counted or said check; a check a verifier hears (guitar's
  chords, tuning) points to the page that records it.
- `learning_progress`: how every path (or the one named) is going.

Writes go straight to the person's own store (each undoable); nothing here is
sent anywhere. `next_lesson_reply` answers "what's my next guitar lesson?" in
code, read only, before the model (core/assistant_turn.py).
"""

from __future__ import annotations

import re
from typing import Optional

from core import paths


def _book(context) -> Optional[paths.PathBook]:
    """The person's learning paths, or None on a MIA without them."""
    return getattr(context, "paths", None)


def _which(context, book: paths.PathBook, words: str) -> Optional[paths.Program]:
    """The path the words mean among those started (or the only one started); None when the words name a course
    that isn't started (`_ask_which` then says so), unless only by words a started course uses for itself."""
    started = [paths.program_of(context, p) for p in book.started()]
    started = [p for p in started if p is not None]
    if len(started) == 1 and not words:
        return started[0]
    found = paths.find_program(context, words) if words else None
    if found is not None:
        if book.path(found.id) is not None:
            return found
        # a course he named by its name that isn't started is never swapped for the one that is (live check,
        # 2026-11-25: "teach me small business basics" taught Money basics' first lesson); but words a started course
        # uses for itself stay its ("woodworking basics" with Carpentry started: the fifth review)
        text = f" {words.lower()} "
        if found.name.lower() not in text:
            own = [p for p in started if any(re.search(rf"\b{re.escape(w)}\b", text) for w in p.words)]
            if len(own) == 1:
                return own[0]
        return None
    return started[0] if len(started) == 1 else None


_NEXT_LESSON = re.compile(r"\b(?:what'?s|whats|what is|what are)\b.{0,30}\bnext\b.{0,30}\b(?:lessons?|steps?|course)\b|"
                          r"\bnext (?:\w+ ){1,3}lesson\b", re.I)


def _course_named(context, said: str):
    """The course his words name: by its words (core/paths.find_program), else its id or name as a whole word ("my
    next money lesson": an id counts in find_program only as the whole subject)."""
    found = paths.find_program(context, said)
    if found is not None:
        return found
    paths._builtins()
    return next((p for p in paths.PROGRAMS.values()
                 if re.search(rf"\b{re.escape(p.id)}\b", said, re.I) or p.name.lower() in said.lower()), None)


def next_lesson_reply(context, words: str) -> Optional[str]:
    """"What's my next guitar lesson?", read only, in code (live sweep, 2026-11-25: with Guitar not started, the
    model answered "I'm not aware of your upcoming lessons"): for a course his words name, its next step from his own
    path (core/paths.next_step), or that it isn't started and how to start it. None when no course is named (the
    progress plans and the lesson tool take "what's next?"), or for a board course (core/esp32_lab.next_lab_reply's)."""
    said = str(words or "")
    if not _NEXT_LESSON.search(said):
        return None
    book = getattr(context, "paths", None)
    program = _course_named(context, said)
    if book is None or program is None or program.id in ("esp32", "arduino"):
        return None
    if book.path(program.id) is None:
        return (f"You haven't started {program.name} yet. Say \"I want to learn {program.id}\" and I'll set it up "
                "with you.")
    return paths.next_step(book, program)


def _ask_which(context, book: paths.PathBook, words: str = "") -> str:
    """The question when more than one path is started; or, when the words name a course he hasn't started, that he
    hasn't and how to."""
    named = paths.find_program(context, words) if words.strip() else None
    if named is not None and book.path(named.id) is None:
        return (f"You haven't started {named.name} yet. Say \"I want to learn {named.name.lower()}\" and I'll set it up "
                "with you.")
    names = [paths.program_of(context, p).name for p in book.started() if paths.program_of(context, p)]
    return "Which one? " + ", ".join(names) + "." if names else "You haven't started anything yet: say what you'd like to learn."


def _action_start(context, arguments: dict) -> str:
    """Tool start_learning: starts the program the interest means (built in, or a draft of theirs); with none, drafts
    one and describes it, to be started by saying start it."""
    book = _book(context)
    if book is None:
        return "Learning paths aren't on this MIA."
    interest = str(arguments.get("interest") or "").strip()
    goal = str(arguments.get("goal") or "").strip()
    program = paths.find_program(context, interest)
    if program is None and not interest and book.drafts:
        program = paths.from_dict(list(book.drafts.values())[-1])  # "start it": the latest draft
    if program is None:
        if not interest:
            return "What would you like to learn?"
        try:
            program = paths.draft(context, interest, goal)
        except ValueError as problem:
            return str(problem)
        return (paths.describe_program(program) + " Say \"start it\" to begin, with how much time you have, or tell "
                "me what to change.")
    book.start(program, goal, arguments.get("minutes_a_day"), arguments.get("days_a_week"))
    paths.ensure_homework(context)
    plan = book.path(program.id)["plan"]
    return (f"You're set for {program.name}" + (" (a plan I drafted)" if program.drafted else "") + f": "
            f"{plan['minutes_a_day']} minutes a day, {plan['days_a_week']} days a week. This week's homework is in "
            "Missions. " + paths.next_step(book, program) + " Want the first lesson now?")


def _action_lesson(context, arguments: dict) -> str:
    """Tool learning_lesson: the next lesson for where they are, one named, or (guitar) a chord's shape.
    A course named that isn't started is said as not started, never swapped for the one that is."""
    book = _book(context)
    if book is None:
        return "Learning paths aren't on this MIA."
    topic = str(arguments.get("topic") or "").strip()
    program = _which(context, book, str(arguments.get("path") or topic))
    if program is None:
        return _ask_which(context, book, str(arguments.get("path") or topic))
    if program.id == "guitar" and topic:
        from core.guitar import CHORDS, shape_text

        short = topic.lower().replace(" chord", "").replace(" shape", "").replace(" minor", "m").replace(
            " major", "").replace("the ", "").strip()
        chord = next((c for name, c in CHORDS.items() if short == name.lower()), None)
        if chord is not None:
            return shape_text(chord) + "."
    lessons = [l for s in program.stages for l in s.lessons]
    named = next((l for l in lessons if topic and topic.lower() in l.title.lower()), None)
    if named is None:
        stage = paths.stage_of(book, program)
        left = paths.open_checks(book, program)
        named = next((l for l in stage.lessons if left and left[0].about and left[0].about in l.about),
                     stage.lessons[0])
    return paths.teach(program, named)


def _action_practice(context, arguments: dict) -> str:
    """Tool log_practice: keeps a practice session on a path and says how the week's homework stands.
    A course named that isn't started is said as not started."""
    book = _book(context)
    if book is None:
        return "Learning paths aren't on this MIA."
    program = _which(context, book, str(arguments.get("path") or ""))
    if program is None:
        return _ask_which(context, book, str(arguments.get("path") or ""))
    try:
        book.log_practice(program, arguments.get("minutes") or 0, str(arguments.get("worked_on") or ""),
                          arguments.get("value"))
    except (TypeError, ValueError) as problem:
        return str(problem)
    done = [m for m in paths.ensure_homework(context) if m is not None and m.status == "completed"
            and m.occurrence_key.startswith(f"{paths.PREFIX}{program.id}:")]
    s = paths.stats(book, program)
    return (f"Logged. {program.name} this week: {s['week_days']} of {s['plan']['days_a_week']} days, "
            f"{s['week_minutes']:g} minutes." + (" That finishes this week's homework." if done else ""))


def _find_check(program: paths.Program, book: paths.PathBook, words: str) -> Optional[paths.Check]:
    """The check the words mean: by id, by the most words in common with an open (else any) check, else the first
    open one."""
    text = (words or "").lower().replace("e minor", "em").replace("a minor", "am")
    every = [c for s in program.stages for c in s.checks]
    if text in {c.id for c in every}:
        return next(c for c in every if c.id == text)
    want = {w for w in text.replace(",", " ").split() if len(w) > 1 and w not in ("to", "the", "and", "a", "in")}
    if want:
        def overlap(c):
            what = c.what.lower().replace("e minor", "em").replace("a minor", "am")
            return len(want & set(what.replace(",", " ").replace(":", " ").split()))
        left = paths.open_checks(book, program)
        best = max(left or every, key=overlap)
        if overlap(best):
            return best
    left = paths.open_checks(book, program)
    return left[0] if left else None


def _action_check(context, arguments: dict) -> str:
    """Tool learning_check: a counted or said check passed or not; a recorded one read from the person's records; one
    a verifier checks points to the page.
    A course named that isn't started is said as not started.
    Asked again with the same words its course was looked for by."""
    book = _book(context)
    if book is None:
        return "Learning paths aren't on this MIA."
    program = _which(context, book, str(arguments.get("path") or arguments.get("check") or ""))
    if program is None:  # the same words as `_which` had (the fifth review: "Which one? Carpentry." for a check)
        return _ask_which(context, book, str(arguments.get("path") or arguments.get("check") or ""))
    check = _find_check(program, book, str(arguments.get("check") or ""))
    if check is None:
        return "Which check? " + paths.next_step(book, program)
    if check.how not in paths.PLAIN_HOWS and check.how != paths.RECORDED:
        return (f"\"{check.what}\" is one I check myself: open the {program.name} page (web/guitar.html?path="
                f"{program.id}) on the phone or the web and show me.")
    try:
        if check.how == paths.RECORDED:
            result = paths.check_records(context, program, check)
        else:
            result = paths.record_plain(context, program, check, arguments.get("value"))
    except ValueError as problem:
        return str(problem)
    paths.ensure_homework(context)
    return result["said"] + (" " + paths.next_step(book, program) if result["passed"] else "")


def _action_progress(context, arguments: dict) -> str:
    """Tool learning_progress: how each path (or the one named) is going, and what's next."""
    book = _book(context)
    if book is None:
        return "Learning paths aren't on this MIA."
    paths.ensure_homework(context)
    words = str(arguments.get("path") or "")
    chosen = _which(context, book, words) if words else None
    programs = [chosen] if chosen else [paths.program_of(context, p) for p in book.started()]
    programs = [p for p in programs if p is not None]
    if not programs:
        return "You haven't started learning anything with me yet: say what you'd like to learn."
    return " ".join(paths.describe_stats(book, p) for p in programs)


LEARNING_WORDS = (
    "woodworking", "woodwork", "the shop", "in the shop", "joinery", "dovetail", "dovetails", "mortise", "tenon",
    "carpentry", "bushcraft", "survival skills", "ferro rod", "fire starting", "friction fire", "knots", "shelter",
    "fitness", "get fit", "guitar", "homework", "practiced", "practised",  # not bare "lessons": "what lessons have
    # I learned from experience?" is reflection, not a program
    "practice", "my program", "the program", "what stage", "next stage",
)


GARDENING_PHRASES = ("teach me gardening", "into gardening", "learn gardening", "in gardening", "my gardening",
                     "gardening program", "gardening lesson", "gardening homework")


def _program_names(context) -> list:
    """The learning programs' names ("Woodworking at the bench", "Survival and bushcraft"...), for the registry."""
    from core import paths

    paths._builtins()
    return [p.name for p in paths.PROGRAMS.values()]


def _action_practice_today(context, arguments: dict) -> str:
    """Tool practice_today: what to practise today on a path (the one named, else every one started), read only:
    today's minutes from the plan and whether today is already in, this week so far, and the next step with its
    lesson (core/paths.next_step, stats). Nothing is written, so MIA can answer it herself (the model gave generic
    guitar advice instead: live check through the whole turn, 2026-11-25)."""
    from datetime import date

    book = _book(context)
    if book is None:
        return "Learning paths aren't on this MIA."
    words = " ".join(str(arguments.get(k) or "") for k in ("path", "question"))
    chosen = _which(context, book, words) if words.strip() else None
    programs = [chosen] if chosen else [paths.program_of(context, p) for p in book.started()]
    programs = [p for p in programs if p is not None]
    if not programs:
        found = paths.find_program(context, words) if words.strip() else None
        return (paths.next_step(book, found) if found is not None else
                "You haven't started learning anything with me yet: say what you'd like to learn, like \"start "
                "guitar\".")
    today = date.today().isoformat()
    parts = []
    for program in programs:
        s = paths.stats(book, program)
        plan = s["plan"] or {}
        done_today = any(x["date"] == today for x in (book.path(program.id) or {}).get("sessions", []))
        minutes = plan.get("minutes_a_day")
        head = (f"{program.name} today: " + (f"{minutes:g} minutes" if minutes else "a session")
                + (" (you've already practised today)" if done_today else "")
                + (f"; this week {s['week_days']} of {plan.get('days_a_week')} days, {s['week_minutes']:g} minutes"
                   if plan.get("days_a_week") else "") + ".")
        parts.append(head + " " + paths.next_step(book, program))
    return " ".join(parts)


def register_path_actions(registry) -> None:
    """Registers the learning-path tools: start_learning, learning_lesson, log_practice, learning_check and
    learning_progress, and the words that reach them (`LEARNING_WORDS`, the programs' names), so his own way of
    asking about woodworking, gardening, fitness or bushcraft finds them (tests/test_everyday_phrasing_routing.py).
    practice_today (read only, so MIA can answer it herself) is reached by "what should I practice on guitar
    today?".
    learning_lesson is reached by "what's my next ESP32 lesson?" too."""
    from core.assistant_actions import AssistantAction

    s = {"type": "string"}
    path = {**s, "description": "Which path (guitar, welding...), only if they named one."}
    registry.register(AssistantAction(
        name="start_learning", domain="learning",
        description=("Start learning something (guitar, welding, a language...): their goal in their own words and how "
                     "much time they have. MIA uses her program for it, or drafts one and asks before starting; "
                     "'start it' starts the draft."),
        parameters={"type": "object", "properties": {
            "interest": {**s, "description": "What they want to learn, e.g. 'guitar'. Empty for 'start it'."},
            "goal": {**s, "description": "Why, in their words, only if they said."},
            "minutes_a_day": {"type": "integer", "description": "Minutes a day, only if they said."},
            "days_a_week": {"type": "integer", "description": "Days a week, only if they said."}}, "required": []},
        handler=_action_start,
        trigger_phrases=("want to learn", "learn to play", "teach me to", "teach me how to", "learn guitar",
                         "start learning", "start it", "get better at", "want to improve at") + GARDENING_PHRASES,
        subjects=("learn", "learning"),
    ))
    registry.register(AssistantAction(
        name="learning_lesson", domain="learning",
        description="Teach the next lesson on one of their learning paths, or one they named (for guitar, a chord's "
                    "shape).",
        parameters={"type": "object", "properties": {
            "topic": {**s, "description": "A lesson or (guitar) a chord, only if they named one."}, "path": path},
            "required": []},
        handler=_action_lesson,
        trigger_phrases=("next lesson", "my lesson", "guitar lesson", "show me the", "chord shape", "teach me the",
                         "next esp32 lesson", "esp32 lesson", "next lab"),
        subjects=("lesson", "chord"),
    ))
    registry.register(AssistantAction(
        name="practice_today", domain="learning",
        description="What to practise today on a learning path (guitar, woodworking...): today's minutes, this week "
                    "so far, and the next step with its lesson, from his own plan. Teaching a lesson is "
                    "learning_lesson; logging practice is log_practice.",
        parameters={"type": "object", "properties": {"path": path, "question": {**s, "description": "his words"}},
                    "required": []},
        handler=_action_practice_today, prompt_arg="question",
        # "what should I practice on guitar today?" went to the day's agenda, then the model's own advice (live check)
        trigger_phrases=("what should i practice", "what should i practise", "what do i practice", "practice today",
                         "practise today", "practice on guitar", "practice on the guitar", "what to practice",
                         "work on today on", "practice tonight"),
        subjects=("practice", "practise", "guitar"),
    ))
    registry.register(AssistantAction(
        name="log_practice", domain="learning",
        description="Log a practice session on one of their learning paths: minutes, what they worked on, a number "
                    "like a tempo.",
        parameters={"type": "object", "properties": {
            "minutes": {"type": "number", "description": "How long."},
            "worked_on": {**s, "description": "What they practised."},
            "value": {"type": "number", "description": "A number they used, like a tempo, only if they said."},
            "path": path}, "required": ["minutes"]},
        handler=_action_practice,
        trigger_phrases=("practiced", "practised", "minutes of practice", "played guitar for", "practice session"),
        subjects=("practice",),
    ))
    registry.register(AssistantAction(
        name="learning_check", domain="learning",
        description="Record a skill check on a learning path they measured or did: a count against a mark (chord "
                    "changes a minute, a tempo, a time) or something done.",
        parameters={"type": "object", "properties": {
            "check": {**s, "description": "Which check, in their words, e.g. 'G to C changes'."},
            "value": {"type": "number", "description": "The number they got."}, "path": path}, "required": []},
        handler=_action_check,
        trigger_phrases=("changes in a minute", "chord changes", "one minute changes", "one-minute changes",
                         "skill check", "passed the check", "played the whole song"),
        subjects=("check", "changes"),
    ))
    registry.register(AssistantAction(
        name="learning_progress", domain="learning",
        description="How their learning paths are going: the week against the plan, streak, hours, checks passed, "
                    "bests, and what's next.",
        parameters={"type": "object", "properties": {"path": path}, "required": []},
        handler=_action_progress,
        trigger_phrases=("guitar progress", "how's my guitar", "how is my guitar", "learning progress",
                         "how am i doing on", "my progress on", "how's my learning"),
        subjects=("progress",),
    ))
    # His programs by the words he'd use for them, so "what's my next woodworking lesson?" or "I cut a dovetail joint
    # today" reaches these tools without the embedding model (the phone): each program's name, its everyday words,
    # and the words of learning itself. "Gardening" alone is small talk ("I love gardening"), so it reaches them only
    # inside a learning phrase (`GARDENING_PHRASES`).
    registry.register_domain_keywords("learning", LEARNING_WORDS)
    registry.register_entity_names("learning", _program_names, match_all_words=True)  # never "a bench at the park"
