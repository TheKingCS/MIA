"""
core.teach_something
======================

"Teach me something" (brainstorm round 18, 2026-11-26): a lesson from her own courses (core/paths), never a model's
trivia. On a course he's started, a lesson from the stage he's on (one a day, turning through the stage's lessons by
the date); with none started, a first lesson from one of her courses, turning through them by the date, with how to
start it. Read only.
"""

from __future__ import annotations

from datetime import date
from typing import Optional


def say(context, today: Optional[date] = None) -> str:
    """A lesson in her words (core/paths.teach), and what to say next: on a started course, its stage's lesson for
    the day (a drafted plan said as one), courses and lessons turning on their own; else a built-in course's first
    lesson, every built-in course loaded first (the Fable review, 2026-11-26)."""
    from core import paths

    today = today or date.today()
    turn = today.toordinal()
    book = getattr(context, "paths", None)
    started = [paths.program_of(context, p) for p in (book.started() if book is not None else [])]
    started = [p for p in started if p is not None]
    if started:
        program = started[turn % len(started)]
        stage = paths.stage_of(book, program)
        lesson = stage.lessons[(turn // len(started)) % len(stage.lessons)]
        drafted = " (a plan I drafted with you, not a built-in course)" if getattr(program, "drafted", False) else ""
        return (f"From {program.name}{drafted}, stage {stage.number} ({stage.name}): {paths.teach(program, lesson)} "
                f"Say \"what's my next {program.name.lower()} lesson\" for where you are in it.")
    paths._builtins()
    programs = [p for p in paths.PROGRAMS.values() if not getattr(p, "drafted", False) and p.stages]
    if not programs:
        return "I don't have a course to teach from yet."
    program = sorted(programs, key=lambda p: p.id)[turn % len(programs)]
    lesson = program.stages[0].lessons[0]
    return (f"From {program.name}: {paths.teach(program, lesson)} Say \"I want to learn {program.name.lower()}\" and "
            f"I'll take you through the rest.")
