"""
core.web_equipment
====================

Garage, Property, Greenhouse and Maintenance on the web (2026-10-06,
DEC-0017), and one page per asset in the shape of Zac's concept (the
mower page): everything the PC app shows, assembled here so `web/`
holds no logic. Served as `/api/equipment?scope=…` and
`/api/assets/{asset_id}`; changes are the action kinds in
core/equipment_actions.py and `maintenance.done`.

- **Scopes** follow the PC modules: Garage = vehicles and power
  equipment, Property = appliances, the property and tools, Greenhouse =
  garden and plants, Maintenance = everything (with the full task list
  and the upcoming calendar).
- **Task status** speaks the PC app's vocabulary ("overdue 13d", "due in
  3d", "120/150 engine hours", "ok — 72°F"), computed from the same
  due-date functions in core/maintenance_manager.py.
- **An asset's page:** details, quick stats (meters), current tasks,
  related missions, documents, cost of ownership, and its history from
  the life events log. Parts aren't tracked per asset yet (PLANNED).
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import date, timedelta
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

SCOPES: dict[str, dict] = {
    "garage": {"name": "Garage", "icon": "🚗", "tagline": "Keep it running. Keep it ready.",
               "categories": ("Vehicle", "Power Equipment"), "default_category": "Vehicle"},
    "property": {"name": "Property", "icon": "🏠", "tagline": "The house, the appliances, the tools.",
                 "categories": ("Appliance", "Property", "Tool"), "default_category": "Appliance"},
    "greenhouse": {"name": "Greenhouse", "icon": "🌱", "tagline": "Grow food. Grow freedom.",
                   "categories": ("Garden/Plant",), "default_category": "Garden/Plant"},
    "maintenance": {"name": "Maintenance", "icon": "🔧", "tagline": "Everything you own, cared for.",
                    "categories": None, "default_category": "Other"},
}
NEXT_UP_DAYS = 30
CALENDAR_DAYS = 60


def scope_of(category: str) -> str:
    """Pure logic. Which screen an asset of this category lives on."""
    for key, scope in SCOPES.items():
        if scope["categories"] and category in scope["categories"]:
            return key
    return "maintenance"


def _readings(context, task) -> list:
    if task.trigger_type == "calendar":
        return []
    try:
        return sorted(context.maintenance.readings_for_task(task.task_id) or [], key=lambda r: r.timestamp)
    except AttributeError:  # no data logger on this MIA (tests, headless)
        return []


def task_status(task, readings: list, today: date) -> dict:
    """Pure logic (given readings). A task's urgency and its status line,
    in the PC app's words."""
    from core.maintenance_manager import (days_until_due, is_meter_task_due, is_sensor_task_due,
                                          meter_used_since_last, predicted_due_date, task_urgency)

    urgency = task_urgency(task, readings, today)
    days = None
    quick = (task.is_meter_task and task.meter_interval is None) or (task.is_sensor_task and task.threshold_value is None)
    latest = readings[-1].value if readings else None
    unit = task.meter_unit or ""
    if task.trigger_type == "calendar":
        days = days_until_due(task, today)
        if days is None:
            text = ("one time" if not task.last_completed else "done") if task.interval_days is None else "never done"
        elif days < 0:
            text = f"overdue {-days}d"
        elif days == 0:
            text = "due today"
        else:
            text = f"due in {days}d"
        attention = days is not None and days <= 0
    elif task.is_meter_task:
        if quick:
            text = f"{latest:g} {unit}".strip() if latest is not None else "no reading logged"
            attention = False
        elif task.last_completed_meter_value is None:
            text, attention = "never done", False
        elif not readings:
            text, attention = "no readings logged", False
        else:
            used = meter_used_since_last(task, readings) or 0.0
            left = (task.meter_interval or 0.0) - used
            text = f"overdue {-left:g} {unit}".strip() if left <= 0 else f"{used:g}/{task.meter_interval:g} {unit}".strip()
            attention = is_meter_task_due(task, readings)
    else:
        if latest is None:
            text, attention = "no readings logged", False
        else:
            due = is_sensor_task_due(task, readings) if not quick else False
            text = ("due — " if due else ("" if quick else "ok — ")) + f"{latest:g}{unit}"
            attention = due
    predicted = predicted_due_date(task, readings, today) if task.is_meter_task else None
    return {"urgency": urgency, "text": text, "days": days, "needs_attention": bool(attention), "quick_stat": quick,
            "latest": latest, "predicted": predicted[1] if predicted else None}


def _task_row(context, task, asset, today: date) -> dict:
    from core.equipment_actions import RECORDS

    readings = _readings(context, task)
    status = task_status(task, readings, today)
    data = asdict(task)
    values = {f.name: data.get(f.name) for f in RECORDS["maintenance_task"].fields}
    return {"id": task.task_id, "title": task.title, "asset_id": task.asset_id,
            "asset": asset.name if asset is not None else None, "trigger": task.trigger_type, "unit": task.meter_unit,
            "priority": task.priority, "last_completed": task.last_completed, "interval_days": task.interval_days,
            "meter_interval": task.meter_interval, **status, "values": values,
            "action": None if status["quick_stat"] else
            {"kind": "maintenance.done", "label": "Done", "params": {"task_id": task.task_id},
             "asks_meter": task.is_meter_task}}


def _order(row: dict) -> tuple:
    rank = {"overdue": 0, "due_soon": 1, "on_track": 2, "unknown": 3}.get(row["urgency"], 4)
    return (not row["needs_attention"], rank, row["days"] if row["days"] is not None else 10_000, row["title"])


def _owner(context, asset) -> Optional[str]:
    profiles = getattr(context, "profiles", None)
    owner = profiles.get_profile(asset.owner_profile_id) if profiles is not None and asset.owner_profile_id else None
    return getattr(owner, "name", None)


def _asset_card(context, asset, rows: list, today: date) -> dict:
    current = sorted((r for r in rows if not r["quick_stat"]), key=_order)
    return {"id": asset.asset_id, "name": asset.name, "category": asset.category,
            "make_model": " ".join(p for p in (asset.manufacturer, asset.model) if p), "owner": _owner(context, asset),
            "overdue": sum(r["needs_attention"] for r in rows), "tasks": current[:3], "task_count": len(current),
            "quick_stats": [{"title": r["title"], "text": r["text"]} for r in rows if r["quick_stat"]],
            "warranty_until": asset.warranty_until or None,
            "scope": scope_of(asset.category)}


def equipment_page(context, scope: str = "maintenance", today: Optional[date] = None) -> dict:
    from core.equipment_actions import form_spec
    from core.maintenance_manager import ASSET_CATEGORIES, next_occurrence_date

    today = today or date.today()
    scope = scope if scope in SCOPES else "maintenance"
    info = SCOPES[scope]
    maintenance = getattr(context, "maintenance", None)
    page = {"scope": scope, **{k: v for k, v in info.items() if k != "categories"},
            "categories": list(info["categories"] or ASSET_CATEGORIES), "forms": form_spec(), "as_of": today.isoformat()}
    if maintenance is None:
        page.update(available=False, assets=[], attention=[], next_up=[], tasks=[], calendar=[])
        return page
    assets = [a for a in maintenance.all_assets() if info["categories"] is None or a.category in info["categories"]]
    by_id = {a.asset_id: a for a in assets}
    rows = [_task_row(context, t, by_id[t.asset_id], today) for t in maintenance.all_tasks() if t.asset_id in by_id]
    page["available"] = True
    page["assets"] = sorted((_asset_card(context, a, [r for r in rows if r["asset_id"] == a.asset_id], today)
                             for a in assets), key=lambda c: (-c["overdue"], c["name"].lower()))
    page["attention"] = sorted((r for r in rows if r["needs_attention"]), key=_order)
    page["next_up"] = sorted((r for r in rows if not r["needs_attention"] and not r["quick_stat"]
                              and (r["urgency"] == "due_soon" or (r["days"] is not None and r["days"] <= NEXT_UP_DAYS))),
                             key=_order)
    page["all_assets"] = [{"id": a.asset_id, "name": a.name} for a in maintenance.all_assets()]
    if scope == "maintenance":
        page["tasks"] = sorted((r for r in rows if not r["quick_stat"]), key=_order)
        calendar = []
        for task in maintenance.all_tasks():
            if task.asset_id not in by_id:
                continue
            when = next_occurrence_date(task, _readings(context, task), today)
            if when is not None and when <= today + timedelta(days=CALENDAR_DAYS):
                calendar.append({"date": when.isoformat(), "title": task.title, "asset": by_id[task.asset_id].name,
                                 "task_id": task.task_id, "overdue": when < today})
        page["calendar"] = sorted(calendar, key=lambda c: (c["date"], c["title"]))
    return page


def asset_page(context, asset_id: str, today: Optional[date] = None) -> Optional[dict]:
    from core import life_events
    from core.equipment_actions import RECORDS, form_spec

    today = today or date.today()
    maintenance = getattr(context, "maintenance", None)
    asset = maintenance.get_asset(asset_id) if maintenance is not None else None
    if asset is None:
        return None
    rows = sorted((_task_row(context, t, asset, today) for t in maintenance.tasks_for_asset(asset_id)), key=_order)
    data = asdict(asset)
    page = {"id": asset.asset_id, "name": asset.name, "category": asset.category, "scope": scope_of(asset.category),
            "scope_name": SCOPES[scope_of(asset.category)]["name"], "owner": _owner(context, asset),
            "details": [{"label": label, "value": value} for label, value in (
                ("Make", asset.manufacturer), ("Model", asset.model), ("Serial number", asset.serial_number),
                ("Bought on", asset.purchase_date), ("Warranty until", asset.warranty_until),
                ("Owner", _owner(context, asset))) if value],
            "notes": asset.notes, "values": {f.name: data.get(f.name) for f in RECORDS["asset"].fields},
            "tasks": [r for r in rows if not r["quick_stat"]],
            "attention": [r for r in rows if r["needs_attention"]],
            "forms": form_spec(), "as_of": today.isoformat()}

    stats = [{"title": r["title"], "text": r["text"], "task_id": r["id"]} for r in rows if r["quick_stat"]]
    try:
        for meter in maintenance.asset_meter_names(asset_id):
            readings = sorted(maintenance.asset_readings(asset_id, meter), key=lambda r: r.timestamp)
            if readings:
                last = readings[-1]
                stats.append({"title": meter, "text": f"{last.value:g} {last.unit or ''}".strip(), "meter": meter})
    except AttributeError:
        pass
    page["quick_stats"] = stats

    missions = getattr(context, "missions", None)
    page["missions"] = []
    if missions is not None:
        for m in missions.missions_for_maintenance_asset(asset_id):
            done = sum(1 for i, o in enumerate(m.objectives) if (missions.objective_progress(m.mission_id, i) or 0) >= o.target)
            page["missions"].append({"id": m.mission_id, "name": m.name, "status": m.status, "summary": m.summary,
                                     "objectives": len(m.objectives), "objectives_done": done,
                                     "reward_xp": m.reward_xp, "icon": m.icon})

    page["documents"] = [{"name": name} for name in asset.documents]

    page["costs"] = None
    if getattr(context, "budget", None) is not None:
        try:
            from core.homestead_costs import tool_cost

            cost = tool_cost(context, asset)
            page["costs"] = {"purchase": cost.purchase_price, "upkeep": cost.upkeep, "total": cost.total,
                             "hours": cost.hours, "per_hour": cost.cost_per_hour,
                             "by_category": [{"category": k, "amount": round(v, 2)} for k, v in cost.by_category.items()],
                             "for_builds": cost.for_builds}
        except Exception:
            log.exception("Couldn't work out the cost of %s.", asset.name)

    events = life_events.events_for(context, ref=f"asset:{asset_id}")
    taken_back = life_events.reversed_ids(life_events.events_for(context, types=["undone"]))
    page["history"] = [{"at": e.at, "summary": e.summary, "type": e.type} for e in events
                       if e.event_id not in taken_back][:50]
    page["parts"] = {"status": "PLANNED", "items": []}
    return page
