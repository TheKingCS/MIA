"""
core.assistant_taught_skill_actions
=====================================

Taught skills by voice (DEC-0123, core/taught_skills.py):
- "Watch me: the Friday reset" ... "that's it"
- "What skills have I taught you?"
- "Run the Friday reset" ... "yes" / "done" / an answer
- "Stop the skill"
- "Forget the Friday reset skill"

The plainest of these ("watch me: ...", "that's it", "run <its name>",
the answer to what a run just asked) are handled in code before the model
(`taught_skills.take_turn`); these tools are the same doors for when the
model is the one that hears it. Each runs the same code as the Taught
Skills screen, and none of them can be a step in a skill.
"""

from __future__ import annotations

from core import taught_skills
from core.assistant_actions import AssistantAction, AssistantActionRegistry
from core.assistant_goods_actions import _run
from core.taught_skills import CLEAN_RUNS, DOMAIN, LEARNED, SkillError

_NONE = "Taught skills aren't available on this MIA."


def _named(context, words: str):
    """The skill a few words name, or None."""
    book = getattr(context, "taught_skills", None)
    return book.find(words) if book is not None else None


def _watch(context, arguments: dict) -> str:
    """Tool watch_me_teach: proposes `taught_skill.watch` with the name they gave."""
    return _run(context, "taught_skill.watch", {"name": arguments.get("name") or ""})


def _keep(context, arguments: dict) -> str:
    """Tool keep_taught_skill: proposes `taught_skill.keep` (what she was shown becomes a skill)."""
    return _run(context, "taught_skill.keep", {})


def _cancel(context, arguments: dict) -> str:
    """Tool stop_watching_me: proposes `taught_skill.cancel` (what she was shown is dropped)."""
    return _run(context, "taught_skill.cancel", {})


def _teach(context, arguments: dict) -> str:
    """Tool teach_skill_in_steps: proposes `taught_skill.add` from a name and the steps written as lines."""
    return _run(context, "taught_skill.add", {"name": arguments.get("name") or "", "steps": arguments.get("steps") or "",
                                              "about": arguments.get("about") or ""})


def _change(context, arguments: dict) -> str:
    """Tool change_taught_skill: proposes `taught_skill.steps` for the skill named, with its new steps."""
    skill = _named(context, arguments.get("skill") or "")
    if skill is None:
        return "Which skill? " + _list(context, {})
    return _run(context, "taught_skill.steps", {"skill_id": skill.skill_id, "steps": arguments.get("steps") or ""})


def _forget(context, arguments: dict) -> str:
    """Tool forget_taught_skill: proposes `taught_skill.delete` for the skill named."""
    skill = _named(context, arguments.get("skill") or "")
    if skill is None:
        return "Which skill? " + _list(context, {})
    return _run(context, "taught_skill.delete", {"skill_id": skill.skill_id})


def _list(context, arguments: dict) -> str:
    """Tool list_taught_skills: each skill with whether it's learned or how far through practising, what she's
    being shown, and the run that's waiting."""
    book = getattr(context, "taught_skills", None)
    if book is None:
        return _NONE
    said = []
    if book.skills:
        said.append("You've taught me: " + "; ".join(
            f"{s.name} ({'learned' if s.state == LEARNED else f'practising, {s.clean_runs} of {CLEAN_RUNS} clean runs'})"
            for s in sorted(book.skills, key=lambda s: s.name.lower())) + ".")
    else:
        said.append("You haven't taught me a skill yet. Say \"watch me: \" and a name, do it with me, then say "
                    "\"that's it\".")
    if book.recording is not None:
        said.append(f"I'm watching for \"{book.recording['name']}\" ({len(book.recording['steps'])} steps so far).")
    if book.active is not None and book.active.waiting is not None:
        said.append(f"Waiting on you: {book.active.waiting['text']}")
    return " ".join(said)


def _start(context, arguments: dict) -> str:
    """Tool run_taught_skill: starts the skill named and runs it until it needs the person or ends."""
    if getattr(context, "taught_skills", None) is None:
        return _NONE
    skill = _named(context, arguments.get("skill") or "")
    if skill is None:
        return "I don't have a skill by that name. " + _list(context, {})
    try:
        return taught_skills.say(taught_skills.start(context, skill.skill_id))
    except SkillError as problem:
        return str(problem)


def _answer(context, arguments: dict) -> str:
    """Tool answer_taught_skill: gives the waiting run what the person said (an answer, "done", yes or no)."""
    try:
        return taught_skills.say(taught_skills.answer(context, arguments.get("answer") or ""))
    except SkillError as problem:
        return str(problem)


def _stop(context, arguments: dict) -> str:
    """Tool stop_taught_skill: stops the run in progress."""
    return "Stopped." if taught_skills.stop(context) else "No skill is running."


def _whats_running(context, arguments: dict) -> str:
    """Tool whats_running: what MIA is running in steps now (a browser task, a taught skill, a workflow), where each
    is or what it waits for, and what ended lately, from the person's run book (core/runs.py, UI-1)."""
    from core.runs import summary

    return summary(context)


def _plan_week(context, arguments: dict) -> str:
    """Tool plan_my_week: lines up this week's steps from what's due (`steps.plan_week`), then reads the plan."""
    from core.actions import run_as_tool
    from core.step_plans import said

    made = run_as_tool(context, "steps.plan_week", {})
    return made if "waiting for you" not in made else said(context)


def _the_plan(context, arguments: dict) -> str:
    """Tool whats_the_plan: the open plan's steps, numbered, with what's waiting (core/step_plans.said)."""
    from core.step_plans import said

    return said(context)


def _plan_step(kind: str):
    """A handler that runs `kind` (steps.do or steps.drop) on the step number given, in the newest open plan."""
    def handler(context, arguments: dict) -> str:
        """Runs the plan action on the numbered step, as the screen's press would."""
        from core.actions import run_as_tool

        return run_as_tool(context, kind, {"step_id": str(arguments.get("step") or "").strip()})
    return handler


def register_taught_skill_actions(registry: AssistantActionRegistry) -> None:
    """Registers the taught-skill tools: watch_me_teach, keep_taught_skill, stop_watching_me, teach_skill_in_steps,
    change_taught_skill, forget_taught_skill, list_taught_skills, run_taught_skill, answer_taught_skill and
    stop_taught_skill; whats_running, every run of steps in one list (UI-1); and the plans across apps (UI-7):
    plan_my_week, whats_the_plan, do_plan_step and drop_plan_step."""
    none = {"type": "object", "properties": {}, "required": []}
    which = {"type": "string", "description": "The skill's name, as they said it."}
    lines = {"type": "string", "description": "The steps, one a line: tell: words / ask: question -> name / "
                                              "you: what they do / tool: tool_name key=value / action: kind key=value."}
    for name, description, parameters, handler, phrases in (
        ("watch_me_teach", "Start watching what the person does next, to keep it as a taught skill.",
         {"type": "object", "properties": {"name": {"type": "string", "description": "What to call the skill."}},
          "required": ["name"]}, _watch, ("watch me", "let me teach you", "teach you how", "learn this")),
        ("keep_taught_skill", "Keep what was just shown as a taught skill.", none, _keep,
         ("done teaching", "that's the skill", "keep that skill")),
        ("stop_watching_me", "Stop watching and drop what was being shown.", none, _cancel,
         ("stop watching", "forget what i showed")),
        ("teach_skill_in_steps", "Teach a skill by writing its steps.",
         {"type": "object", "properties": {"name": {"type": "string", "description": "What to call the skill."},
                                           "steps": lines,
                                           "about": {"type": "string", "description": "What it's for, if said."}},
          "required": ["name", "steps"]}, _teach, ("teach you a skill", "new taught skill", "a skill in steps")),
        ("change_taught_skill", "Replace a taught skill's steps (it goes back to practising).",
         {"type": "object", "properties": {"skill": which, "steps": lines}, "required": ["skill", "steps"]},
         _change, ("change the skill", "change the steps", "edit the skill")),
        ("forget_taught_skill", "Forget a taught skill.",
         {"type": "object", "properties": {"skill": which}, "required": ["skill"]}, _forget,
         ("forget the skill", "delete the skill", "forget that skill")),
        ("list_taught_skills", "The skills the person has taught, learned or practising, and any run waiting on them.",
         none, _list, ("skills have i taught", "taught skills", "taught you", "what have you learned from me",
                       "skills you've learned")),
        ("run_taught_skill", "Run a skill the person taught, stopping for them where it asks.",
         {"type": "object", "properties": {"skill": which}, "required": ["skill"]}, _start,
         ("run the skill", "run my skill", "practise the skill", "practice the skill", "do the skill")),
        ("answer_taught_skill", "Give the running skill the person's answer, their \"done\", or their yes or no.",
         {"type": "object", "properties": {"answer": {"type": "string", "description": "What they said."}},
          "required": ["answer"]}, _answer, ("answer the skill", "tell the skill")),
        ("stop_taught_skill", "Stop the skill that's running.", none, _stop,
         ("stop the skill", "stop that skill", "cancel the skill")),
    ):
        registry.register(AssistantAction(name=name, domain=DOMAIN, description=description, parameters=parameters,
                                          handler=handler, trigger_phrases=phrases, subjects=("skill", "skills")))
    step = {"type": "object", "properties": {"step": {"type": "string", "description": "The step's number."}},
            "required": ["step"]}
    for name, description, parameters, handler, phrases in (
        ("plan_my_week", "Line up this week's steps from what's due, for the person to do one at a time. Nothing in "
                         "the plan runs until they say.", none, _plan_week,
         ("plan my week", "get me ready for the week", "ready for the week", "line up my week")),
        ("whats_the_plan", "Read the open plan's steps, numbered, with what's waiting.", none, _the_plan,
         ("what's the plan", "whats the plan", "read the plan", "what's left in the plan", "steps in the plan")),
        ("do_plan_step", "Do one numbered step of the open plan, because the person said to.", step,
         _plan_step("steps.do"), ("do step", "go ahead with step", "run step")),
        ("drop_plan_step", "Leave one numbered step out of the open plan.", step, _plan_step("steps.drop"),
         ("drop step", "skip step", "leave out step")),
    ):
        registry.register(AssistantAction(name=name, domain=DOMAIN, description=description, parameters=parameters,
                                          handler=handler, trigger_phrases=phrases, subjects=("plan", "step", "week")))
    registry.register(AssistantAction(
        name="whats_running", domain=DOMAIN,
        description="What MIA is running in steps right now (browser tasks, taught skills, workflows), where each is or "
                    "what it waits for, and what stopped lately.",
        parameters=none, handler=_whats_running,
        trigger_phrases=("what's running", "whats running", "what are you running", "what are you doing right now",
                         "anything running", "what are you in the middle of"),
        subjects=("running", "doing", "middle")))
