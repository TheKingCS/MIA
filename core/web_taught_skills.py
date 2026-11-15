"""
core.web_taught_skills
========================

The Taught Skills screen's data (DEC-0123, DEC-0017: assembled here, the
web only shows it): each skill with its steps in plain words and as the
lines they're edited in, its practice state, what she's being shown right
now, and the run that's waiting on the person.
"""

from __future__ import annotations

from core.taught_skills import CLEAN_RUNS, LEARNED, format_steps, say_step

STEP_HELP = ("One step a line. tell: words she says. ask: a question -> a name (use it later as {name}). "
             "you: something you do. tool: one of her tools, then key=value. action: an action kind, then key=value.")


def skills_page(context) -> dict:
    """The screen: {available, skills, watching, run, needed, help}. A skill row has its id, name, what it's for,
    state, clean runs, runs, how the last one ended, its steps as sentences (each marked when it will ask) and as
    editable lines."""
    from core.taught_skills import Skill, _needs_yes

    book = getattr(context, "taught_skills", None)
    if book is None:
        return {"available": False, "skills": [], "watching": None, "run": None, "needed": CLEAN_RUNS,
                "help": STEP_HELP}
    learned = Skill("", "", state=LEARNED)
    rows = []
    for s in sorted(book.skills, key=lambda s: s.name.lower()):
        rows.append({
            "skill_id": s.skill_id, "name": s.name, "about": s.about, "state": s.state, "clean_runs": s.clean_runs,
            "runs": s.runs, "last_run": s.last_run, "last_result": s.last_result, "source": s.source,
            "steps": [{"text": say_step(context, step), "kind": step.get("kind"),
                       "asks": _needs_yes(context, s, step), "always_asks": _needs_yes(context, learned, step)}
                      for step in s.steps],
            "steps_text": format_steps(s.steps)})
    watching = None
    if book.recording is not None:
        watching = {"name": book.recording["name"],
                    "steps": [say_step(context, step) for step in book.recording["steps"]]}
    run = None
    if book.active is not None:
        skill = book.get(book.active.skill_id)
        run = {"skill_id": book.active.skill_id, "name": skill.name if skill else "", "step": book.active.at + 1,
               "of": len(skill.steps) if skill else 0, "waiting": book.active.waiting}
    return {"available": True, "skills": rows, "watching": watching, "run": run, "needed": CLEAN_RUNS,
            "help": STEP_HELP}
