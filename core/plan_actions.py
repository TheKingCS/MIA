"""
core.plan_actions
===================

The plan page's changes (the screens review's missing "plan's page", its
material list, cut list and shopping list; DEC-0118, DEC-0125), as action
kinds so the Library page and voice agree and "undo that" takes each back
(the plans and projects stores write through atomic_write_text):

- `plan.keep`: keep a plan at the size on the page (a built-in plan worked
  out for your size; by voice, material_list with keep).
- `plan.project`: start a Workshop project from it, its materials and steps
  in the description (by voice, start_plan_project).
- `plan.delete`: let a kept plan go (built-in plans and files stay; by voice,
  forget_plan).

The sizes travel as the plan's own calculator arguments (length_ft,
width_ft...) beside `plan_id`; quantities are always worked out in
core/build_calcs.py, never here.
"""

from __future__ import annotations

from core.actions import ACTION_TYPES, ActionError, ActionType, _need


def _plan(context, params) -> dict:
    """The plan the params name; ActionError when it isn't on the shelf."""
    plan = _need(context, "plans").get(str(params.get("plan_id") or ""))
    if plan is None:
        raise ActionError("That plan isn't on the shelf.")
    return plan


def _worked(context, params) -> tuple[dict, dict, dict]:
    """(the plan, its materials at the size in the params, the sizes used); ActionError for a size that won't do."""
    from core.plan_library import read_sizes

    plan = _plan(context, params)
    try:
        sizes = read_sizes(plan, params) if plan.get("calc") else {}
        worked = _need(context, "plans").worked_out(plan, **sizes) if sizes else None
    except (ValueError, TypeError) as error:
        raise ActionError(str(error) or "Those sizes don't work for this plan.") from None
    return plan, (worked.as_dict() if worked is not None else plan.get("materials") or {}), sizes


def _title(plan: dict, materials: dict) -> str:
    """What a plan at a size is called: its worked-out title ("8 x 10 ft gable shed"), capitalised, else the plan's."""
    title = materials.get("title") or plan["title"]
    return title[:1].upper() + title[1:]


def _describe_keep(context, params) -> str:
    """The approval sentence for plan.keep; a file plan can't be kept (it's already on the shelf)."""
    plan, materials, _ = _worked(context, params)
    if plan["id"].startswith("file:"):
        raise ActionError("A file plan is already on the shelf.")
    return f"Keep {_title(plan, materials)} on the plans shelf"


def _keep(context, params) -> str:
    """Does plan.keep: a kept plan with the materials at this size, its tools, steps, calculator and size."""
    plan, materials, sizes = _worked(context, params)
    kept = context.plans.keep(_title(plan, materials), plan.get("kind", "other"),
                              plan.get("summary") or "Worked out by MIA for your size.", materials,
                              tools=plan.get("tools"), steps=plan.get("steps"),
                              source={"name": f"Worked out by MIA from {plan['title']}"}, tags=plan.get("tags"),
                              calc=plan.get("calc", ""), args={**plan.get("args", {}), **sizes})
    return f"Kept \"{kept['title']}\" on the plans shelf."


def _describe_project(context, params) -> str:
    """The approval sentence for plan.project."""
    plan, materials, _ = _worked(context, params)
    _need(context, "projects")
    return f"Start a project: {_title(plan, materials)}, with its materials and steps"


def _project(context, params) -> str:
    """Does plan.project: a Workshop project named for the plan at this size, its materials and steps written into
    the description (as start_plan_project does by voice)."""
    from core.assistant_plan_actions import _materials_text

    plan, materials, _ = _worked(context, params)
    description = f"From the plan \"{plan['title']}\" (plan:{plan['id']}).\n" + _materials_text(materials)
    if plan.get("steps"):
        description += "\nSteps:\n" + "\n".join(f"{i}. {s}" for i, s in enumerate(plan["steps"], 1))
    project = context.projects.add_project(name=_title(plan, materials), description=description)
    return f"Started the project \"{project.name}\"."


def _describe_delete(context, params) -> str:
    """The approval sentence for plan.delete; only a kept plan can go."""
    plan = _plan(context, params)
    if plan["id"] not in context.plans.plans:
        raise ActionError("Only plans you kept can be let go; built-in plans and files stay.")
    return f"Let the kept plan \"{plan['title']}\" go"


def _delete(context, params) -> str:
    """Does plan.delete."""
    plan = _plan(context, params)
    context.plans.delete(plan["id"])
    return f"Let \"{plan['title']}\" go."


PLAN_ACTIONS = {a.kind: a for a in (
    ActionType("plan.keep", "Keep this size", {"plan_id": "the plan", "length_ft": "and its other sizes (optional)"},
               _describe_keep, _keep),
    ActionType("plan.project", "Start a project", {"plan_id": "the plan", "length_ft": "and its other sizes (optional)"},
               _describe_project, _project),
    ActionType("plan.delete", "Let it go", {"plan_id": "a kept plan"}, _describe_delete, _delete),
)}
ACTION_TYPES.update(PLAN_ACTIONS)
