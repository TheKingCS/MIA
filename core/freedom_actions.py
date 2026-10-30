"""
core.freedom_actions
======================

Freedom's actions (DEC-0038, core/freedom.py) on the action contract:
proposed in plain words, approved, run.

- `freedom.plan`: the person's own numbers: what a month of living
  takes, the cushion in months, saved so far (until the bank says),
  saved a month, take-home pay an hour and hours a shift. A blank or 0
  goes back to what MIA works out.
- `freedom.fund_account`: whether a bank account is part of the fund
  (H-0067; until one is picked, all checking and savings count).
- `freedom.build_move`: a build up or down in the person's own order.
- `freedom.build` / `freedom.build_edit`: a homestead build to pay for
  (a Project with a budget, core/homestead_costs.py): the greenhouse,
  the coop, solar, the root cellar. Spending tagged to it counts toward
  it.
"""

from __future__ import annotations

from core.actions import ACTION_TYPES, ActionError, ActionType, _need
PLAN_FIELDS = (  # setting, the parameter, how it's said
    ("freedom.monthly_needs", "monthly_needs", "a month of living"),
    ("freedom.cushion_months", "cushion_months", "the cushion"),
    ("freedom.saved", "saved", "saved so far"),
    ("freedom.monthly_saving", "monthly_saving", "saved a month"),
)
MONEY_PARAMS = {"monthly_needs", "saved", "monthly_saving"}  # pay is the Dungeon's (DEC-0052)


def _money(x: float) -> str:
    from core.region import money

    return money(x)


def _grown_up(context) -> None:
    from core.child_accounts import is_child

    if is_child(context):
        raise ActionError("That's for a grown-up.")


def _number(raw, label: str) -> float:
    if raw in (None, ""):
        return 0.0
    try:
        value = float(raw)
    except (TypeError, ValueError):
        raise ActionError(f"{label.capitalize()} has to be a number.") from None
    if value < 0:
        raise ActionError(f"{label.capitalize()} can't be negative.")
    return value


def _changes(context, params) -> list[tuple]:
    from core.freedom import settings

    _grown_up(context)
    now = settings(context)
    out = []
    for key, param, said in PLAN_FIELDS:
        if param not in params:
            continue
        value = _number(params.get(param), said)
        if param == "cushion_months":
            if value != int(value) or value > 60:
                raise ActionError("The cushion is a whole number of months, up to 60.")
            value = int(value)
        if value != (now.get(key) or 0):
            out.append((key, param, said, value))
    if not out:
        raise ActionError("Nothing to change.")
    return out


def _said(param: str, value) -> str:
    if param == "cushion_months":
        return f"{value} months"
    if param == "shift_hours":
        return f"{value:g} hours" if value else "not set"
    if not value:
        return "worked out by MIA" if param in ("monthly_needs", "monthly_saving") else "not set"
    return _money(value)


def _plan_describe(context, params) -> str:
    return "Your freedom plan: " + "; ".join(f"{said} {_said(param, value)}" for _k, param, said, value in _changes(context, params))


def _plan(context, params) -> str:
    from core import person_settings

    for key, _param, _said_, value in _changes(context, params):
        person_settings.put(context, key, value)
    return "Plan updated."


def _build_values(params, partial: bool) -> dict:
    out = {}
    if "name" in params or not partial:
        name = str(params.get("name") or "").strip()
        if not name:
            raise ActionError("What's the build called? (greenhouse, chicken coop, solar…)")
        out["name"] = name
    if "budget" in params or not partial:
        budget = _number(params.get("budget"), "the budget")
        if budget <= 0:
            raise ActionError("About what will it cost?")
        out["budget"] = round(budget, 2)
    if "description" in params:
        out["description"] = str(params.get("description") or "").strip()
    if "status" in params:
        from core.project_manager import PROJECT_STATUSES

        if params["status"] not in PROJECT_STATUSES:
            raise ActionError("Planning, Active, On Hold or Complete?")
        out["status"] = params["status"]
    return out


def _build_describe(context, params) -> str:
    _grown_up(context)
    _need(context, "projects")
    v = _build_values(params, partial=False)
    return f"Add the build “{v['name']}” to your freedom plan, about {_money(v['budget'])}"


def _build(context, params) -> str:
    v = _build_values(params, partial=False)
    projects = _need(context, "projects")
    project = projects.add_project(v["name"], status="Planning", description=v.get("description", ""))
    projects.update_project(project.project_id, budget=v["budget"])
    return f"{v['name']} is in the plan. Tag what you spend on it (Money) and it counts down."


def _project(context, params):
    project = _need(context, "projects").get_project(str(params.get("project_id") or ""))
    if project is None:
        raise ActionError("That build isn't there anymore.")
    return project


def _build_edit_describe(context, params) -> str:
    _grown_up(context)
    project = _project(context, params)
    v = _build_values(params, partial=True)
    if not v:
        raise ActionError("Nothing to change.")
    bits = [f"{k} {_money(x) if k == 'budget' else x}" for k, x in v.items() if k != "description"]
    return f"Change {project.name}: " + (", ".join(bits) or "its notes")


def _build_edit(context, params) -> str:
    project = _project(context, params)
    context.projects.update_project(project.project_id, **_build_values(params, partial=True))
    return "Build updated."


def _account(context, params):
    from core.freedom import bank_accounts, settings

    _grown_up(context)
    wanted = str(params.get("account_id") or "")
    accounts = bank_accounts(context)
    found = next((a for a in accounts if a["id"] == wanted), None)
    if found is None:
        raise ActionError("That account isn't in your latest bank sync.")
    on = str(params.get("in_fund", "yes")).lower() not in ("no", "false", "0", "off")
    picked = [str(a) for a in (settings(context).get("freedom.fund_accounts") or [])] or [a["id"] for a in accounts]
    picked = [a for a in picked if a != wanted] + ([wanted] if on else [])
    if not picked:
        raise ActionError("Keep at least one account in the fund.")
    return found, on, picked


def _account_describe(context, params) -> str:
    found, on, _picked = _account(context, params)
    name = found["name"] + (f" ····{found['mask']}" if found["mask"] else "")
    return f"{'Count' if on else 'Leave out'} {name} {'in' if on else 'of'} your freedom fund"


def _account_run(context, params) -> str:
    from core import person_settings

    _found, _on, picked = _account(context, params)
    person_settings.put(context, "freedom.fund_accounts", picked)
    return "Fund accounts updated."


def _moving(context, params):
    from core.freedom import gather, settings
    from datetime import date

    _grown_up(context)
    builds = gather(context, date.today())[0].builds
    ids = [b["id"] for b in builds]
    wanted = str(params.get("project_id") or "")
    if wanted not in ids:
        raise ActionError("That build isn't in the plan.")
    up = str(params.get("direction") or "up").lower() == "up"
    i = ids.index(wanted)
    j = i - 1 if up else i + 1
    if not 0 <= j < len(ids):
        raise ActionError("It's already " + ("first." if up else "last."))
    ids[i], ids[j] = ids[j], ids[i]
    return builds[i]["name"], up, ids


def _move_describe(context, params) -> str:
    name, up, _ids = _moving(context, params)
    return f"Move {name} {'up' if up else 'down'} in your builds"


def _move(context, params) -> str:
    from core import person_settings

    _name, _up, ids = _moving(context, params)
    person_settings.put(context, "freedom.build_order", ids)
    return "Order saved."


def _register() -> None:
    for kind in (
        ActionType("freedom.plan", "Save", {param: said for _k, param, said in PLAN_FIELDS}, _plan_describe, _plan),
        ActionType("freedom.fund_account", "Fund", {"account_id": "the bank account", "in_fund": "yes or no"},
                   _account_describe, _account_run),
        ActionType("freedom.build_move", "Move", {"project_id": "the build", "direction": "up or down"},
                   _move_describe, _move),
        ActionType("freedom.build", "Add Build", {"name": "the build", "budget": "about what it costs",
                                                  "description": "notes"}, _build_describe, _build),
        ActionType("freedom.build_edit", "Save", {"project_id": "the build", "name": "the build",
                                                  "budget": "about what it costs", "status": "Planning, Active, On Hold, Complete",
                                                  "description": "notes"}, _build_edit_describe, _build_edit),
    ):
        ACTION_TYPES[kind.kind] = kind


_register()
