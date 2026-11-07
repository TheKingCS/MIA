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
sent anywhere.
"""

from __future__ import annotations

from typing import Optional

from core import paths


def _book(context) -> Optional[paths.PathBook]:
    """The person's learning paths, or None on a MIA without them."""
    return getattr(context, "paths", None)


def _which(context, book: paths.PathBook, words: str) -> Optional[paths.Program]:
    """The path the words mean among those started (or the only one started)."""
    started = [paths.program_of(context, p) for p in book.started()]
    started = [p for p in started if p is not None]
    if len(started) == 1 and not words:
        return started[0]
    found = paths.find_program(context, words) if words else None
    if found is not None and book.path(found.id) is not None:
        return found
    return started[0] if len(started) == 1 else None


def _ask_which(context, book: paths.PathBook) -> str:
    """The question when more than one path is started."""
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
    """Tool learning_lesson: the next lesson for where they are, one named, or (guitar) a chord's shape."""
    book = _book(context)
    if book is None:
        return "Learning paths aren't on this MIA."
    topic = str(arguments.get("topic") or "").strip()
    program = _which(context, book, str(arguments.get("path") or topic))
    if program is None:
        return _ask_which(context, book)
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
    """Tool log_practice: keeps a practice session on a path and says how the week's homework stands."""
    book = _book(context)
    if book is None:
        return "Learning paths aren't on this MIA."
    program = _which(context, book, str(arguments.get("path") or ""))
    if program is None:
        return _ask_which(context, book)
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
    a verifier checks points to the page."""
    book = _book(context)
    if book is None:
        return "Learning paths aren't on this MIA."
    program = _which(context, book, str(arguments.get("path") or arguments.get("check") or ""))
    if program is None:
        return _ask_which(context, book)
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


def register_path_actions(registry) -> None:
    """Registers the learning-path tools: start_learning, learning_lesson, log_practice, learning_check and
    learning_progress."""
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
                         "start learning", "start it", "get better at", "want to improve at"),
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
        trigger_phrases=("next lesson", "my lesson", "guitar lesson", "show me the", "chord shape", "teach me the"),
        subjects=("lesson", "chord"),
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
