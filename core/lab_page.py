"""
core.lab_page
===============

The course page (docs/future/INTERACTIVE_LABS_PLAN.md, step 3; web/course.html): one frame for every course on MIA's
learning paths, the first Build With ESP32 (core/esp32_path.py).

`page(context, course, lesson)`: the course (its name and what it's for), whether he's started it, its stages each
with its state (done, current, later), lessons and checks (passed or not), the lab chosen (the one asked for, else
the next on his path) with its goal, steps, why, what to watch for, and for a hands-on lab its parts, wiring, sketch,
platformio.ini and whether it needs his Wi-Fi typed in, and its circuit for the simulator (core/esp32_sim.circuit_of)
with what to do there to pass; the board (its port, or what's missing) for a course worked
on one; and what's next. Read only: starting the course is the action `path.start`, flashing `esplab.flash`, reading
the board POST /api/labs/{course}/read.
"""

from __future__ import annotations

from typing import Optional


def _labs(course: str) -> dict:
    """The hands-on labs a course has (lesson id -> lab), {} for a course taught without one."""
    if course == "esp32":
        from core.esp32_path import LABS

        return LABS
    return {}


def page(context, course: str = "esp32", lesson: str = "") -> dict:
    """The course page's data (see the module's opening).
    For an ESP32 lab, the circuit for the simulator and what to do there to pass (core/esp32_sim)."""
    from core import paths

    program = paths.program_of(context, course)
    if program is None:
        return {"available": False, "why": "There's no course by that name on MIA's learning paths."}
    book = getattr(context, "paths", None)
    started = bool(book is not None and book.path(program.id) is not None)
    current = paths.stage_of(book, program).number if started else 1
    stages = []
    for s in program.stages:
        stages.append({"number": s.number, "name": s.name, "builds": s.builds,
                       "state": "done" if s.number < current else "current" if s.number == current else "later",
                       "lessons": [{"id": l.id, "title": l.title} for l in s.lessons],
                       "checks": [{"id": c.id, "what": c.what, "passed": started and book.passed(program.id, c.id)}
                                  for c in s.checks]})
    labs = _labs(program.id)
    chosen = lesson if any(l.id == lesson for s in program.stages for l in s.lessons) else ""
    if not chosen and program.id == "esp32":
        from core.esp32_lab import lesson_for

        chosen = lesson_for(context, "")
    if not chosen:
        chosen = paths.stage_of(book, program).lessons[0].id if started else program.stages[0].lessons[0].id
    stage, the = next((s, l) for s in program.stages for l in s.lessons if l.id == chosen)
    lab = labs.get(the.id)
    shown = {"id": the.id, "title": the.title, "stage": stage.number, "steps": list(the.steps), "why": the.why,
             "watch": list(the.watch)}
    if program.id == "esp32":
        from core import esp32_sim

        shown["circuit"] = esp32_sim.circuit_of(the.id)
        shown["try"] = esp32_sim.TRY.get(the.id, "")
    if lab is not None:
        from core.esp32_lab import checks_of, ini

        shown.update({"parts": list(lab["parts"]), "wiring": [list(w) for w in lab["wiring"]], "code": lab["code"],
                      "ini": ini(lab), "secrets": bool(lab.get("secrets")), "libs": list(lab.get("libs", ())),
                      "checks": [{"id": c.id, "what": c.what, "passed": started and book.passed(program.id, c.id)}
                                 for c in checks_of(the.id)]})
    board: Optional[dict] = None
    if labs:
        from core.esp32_lab import board as bench

        found = bench()
        board = {"port": found["port"], "description": found["description"], "ready": not found["missing"],
                 "missing": found["missing"]}
    return {"available": True, "started": started,
            "course": {"id": program.id, "name": program.name, "icon": program.icon, "about": program.about,
                       "minutes_a_day": program.plan[0], "days_a_week": program.plan[1]},
            "stages": stages, "lab": shown, "board": board,
            "next": paths.next_step(book, program) if book is not None else ""}
