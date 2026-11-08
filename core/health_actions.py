"""
core.health_actions
=====================

Every change to Health (core/health_manager.py) as an action, so the page,
the phone, the glasses and voice agree and undo takes each one back, and
the Health page's data (`health_page`) with its forms.

Kinds: `sleep.log`, `sleep.delete`; `visit.add`, `visit.edit`,
`visit.delete`; `med.add`, `med.edit` (also stop and restart), `med.take`,
`med.delete`; `record.add`, `record.delete`. Health is the person's own:
none of these are open to a child account, and none of it goes into a
prompt beyond the turn that asked.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from core.actions import ACTION_TYPES, ActionError, ActionType, _need
from core.health_manager import RECORD_KINDS, VISIT_KINDS


def _store(context):
    """The person's health store; ActionError without one."""
    return _need(context, "health")


def _call(fn, *args, **kwargs):
    """Runs a store change, turning its ValueError or KeyError into the ActionError a person reads."""
    try:
        return fn(*args, **kwargs)
    except (ValueError, KeyError) as problem:
        raise ActionError(str(problem).strip("'\"")) from None


def _num(value, kind=float) -> Optional[float]:
    """A number from a form or a tool ("" and None are None)."""
    if value in (None, ""):
        return None
    try:
        return kind(float(value))
    except (TypeError, ValueError):
        raise ActionError(f"{value} isn't a number.") from None


def _row(rows: list, item_id: str, what: str) -> dict:
    """The row with this id; ActionError when it's gone."""
    found = next((r for r in rows if r["id"] == str(item_id or "")), None)
    if found is None:
        raise ActionError(f"That {what} isn't there anymore.")
    return found


def _fields(params: dict, names: tuple) -> dict:
    """The params a change gives, by name (leaving out ones not sent)."""
    return {k: params[k] for k in names if k in params and params[k] is not None}


# ---------------------------------------------------------------- sleep
def _sleep_log(context, params) -> str:
    """Does sleep.log."""
    entry = _call(_store(context).log_sleep, _num(params.get("hours")) or 0, _num(params.get("rested"), int),
                  params.get("night") or None, str(params.get("note") or ""))
    rested = f", rested {entry['rested']} of 5" if entry["rested"] else ""
    return f"Logged {entry['hours']:g} hours for the night of {entry['night']}{rested}."


def _sleep_delete(context, params) -> str:
    """Does sleep.delete."""
    entry = _call(_store(context).remove, "sleep", str(params.get("sleep_id") or ""))
    return f"Took out the night of {entry['night']}."


# ---------------------------------------------------------------- visits
VISIT_FIELDS = ("kind", "when", "who", "what_for", "notes", "next_due")


def _visit_add(context, params) -> str:
    """Does visit.add."""
    v = _call(_store(context).add_visit, str(params.get("kind") or "Doctor"), str(params.get("when") or ""),
              str(params.get("who") or ""), str(params.get("what_for") or ""), str(params.get("notes") or ""),
              str(params.get("next_due") or ""))
    nxt = f" Next one due {v['next_due']}." if v["next_due"] else ""
    return f"Saved the {v['kind'].lower()} visit on {v['when']}.{nxt}"


def _visit_edit(context, params) -> str:
    """Does visit.edit."""
    v = _call(_store(context).update_visit, str(params.get("visit_id") or ""), **_fields(params, VISIT_FIELDS))
    return f"Updated the {v['kind'].lower()} visit on {v['when']}."


def _visit_delete(context, params) -> str:
    """Does visit.delete."""
    v = _call(_store(context).remove, "visits", str(params.get("visit_id") or ""))
    return f"Took out the {v['kind'].lower()} visit on {v['when']}."


# ---------------------------------------------------------------- medications
def _med_add(context, params) -> str:
    """Does med.add."""
    m = _call(_store(context).add_med, str(params.get("name") or ""), str(params.get("dose") or ""),
              params.get("times") or "", str(params.get("kind") or "Medication"), _num(params.get("refills"), int),
              str(params.get("refill_on") or ""), str(params.get("notes") or ""))
    times = (" Reminders at " + ", ".join(m["times"]) + ".") if m["times"] else ""
    return f"Added {m['name']}{' (' + m['dose'] + ')' if m['dose'] else ''}.{times}"


def _med_edit(context, params) -> str:
    """Does med.edit (and stopping or restarting one: active "no" / "yes")."""
    fields = _fields(params, ("name", "dose", "times", "refill_on", "notes"))
    if params.get("refills") not in (None, ""):
        fields["refills"] = _num(params.get("refills"), int)
    if params.get("active") not in (None, ""):
        fields["active"] = str(params["active"]).lower() in ("yes", "true", "1", "on")
    m = _call(_store(context).update_med, str(params.get("med_id") or ""), **fields)
    if "active" in fields:
        return f"{'Restarted' if m['active'] else 'Stopped'} {m['name']}" + ("." if m["active"] else "; its reminders are off.")
    return f"Updated {m['name']}."


def _med_take(context, params) -> str:
    """Does med.take."""
    store = _store(context)
    med = _row(store.meds, params.get("med_id"), "medication")
    _call(store.take, med["id"])
    n = store.taken_today(med["id"])
    return f"Logged {med['name']}: {n} today."


def _med_delete(context, params) -> str:
    """Does med.delete."""
    m = _call(_store(context).remove_med, str(params.get("med_id") or ""))
    return f"Removed {m['name']} and its reminders."


# ---------------------------------------------------------------- records
def _record_add(context, params) -> str:
    """Does record.add."""
    r = _call(_store(context).add_record, str(params.get("kind") or "Other"), str(params.get("name") or ""),
              str(params.get("when") or ""), str(params.get("value") or ""), str(params.get("notes") or ""))
    return f"Saved {r['kind'].lower()}: {r['name']}."


def _record_delete(context, params) -> str:
    """Does record.delete."""
    r = _call(_store(context).remove, "records", str(params.get("record_id") or ""))
    return f"Took out {r['name']}."


def _named(section: str, key: str, what: str):
    """An approval sentence maker for a change to one existing row: "<verb> <its name>"."""
    def describe(verb: str):
        """The describe function for this verb."""
        def inner(context, params) -> str:
            """The approval sentence (ActionError when the row is gone)."""
            row = _row(getattr(_store(context), section), params.get(key), what)
            return f"{verb} {row.get('name') or row.get('night') or (row.get('kind', '') + ' visit on ' + row.get('when', ''))}"
        return inner
    return describe


_sleep_d, _visit_d, _med_d, _rec_d = (_named("sleep", "sleep_id", "night"), _named("visits", "visit_id", "visit"),
                                      _named("meds", "med_id", "medication"), _named("records", "record_id", "record"))

HEALTH_ACTIONS = {a.kind: a for a in (
    ActionType("sleep.log", "Log Sleep", {"hours": "hours slept", "rested": "1 to 5", "night": "the date", "note": "a note"},
               lambda c, p: f"Log {p.get('hours')} hours of sleep", _sleep_log),
    ActionType("sleep.delete", "Delete", {"sleep_id": "the night"}, _sleep_d("Take out the night of"), _sleep_delete),
    ActionType("visit.add", "Add Visit", {"kind": "doctor, dentist...", "when": "the date", "who": "who",
                                          "what_for": "what for", "notes": "notes", "next_due": "next due"},
               lambda c, p: f"Save a {str(p.get('kind') or 'doctor').lower()} visit on {p.get('when')}", _visit_add),
    ActionType("visit.edit", "Save", {"visit_id": "the visit", **{f: f for f in VISIT_FIELDS}},
               _visit_d("Update the"), _visit_edit),
    ActionType("visit.delete", "Delete", {"visit_id": "the visit"}, _visit_d("Take out the"), _visit_delete),
    ActionType("med.add", "Add", {"name": "the name", "dose": "the dose", "times": "times to take it",
                                  "kind": "Medication or Supplement", "refills": "refills left",
                                  "refill_on": "next refill", "notes": "notes"},
               lambda c, p: f"Add {p.get('name')}" + (f", reminders at {p.get('times')}" if p.get("times") else ""),
               _med_add),
    ActionType("med.edit", "Save", {"med_id": "the medication", "name": "", "dose": "", "times": "", "refills": "",
                                    "refill_on": "", "notes": "", "active": "yes or no"}, _med_d("Update"), _med_edit),
    ActionType("med.take", "Taken", {"med_id": "the medication"}, _med_d("Log a dose of"), _med_take),
    ActionType("med.delete", "Delete", {"med_id": "the medication"}, _med_d("Remove"), _med_delete),
    ActionType("record.add", "Add Record", {"kind": "result, vaccination...", "name": "what", "when": "the date",
                                            "value": "the value", "notes": "notes"},
               lambda c, p: f"Save {str(p.get('kind') or 'a record').lower()}: {p.get('name')}", _record_add),
    ActionType("record.delete", "Delete", {"record_id": "the record"}, _rec_d("Take out"), _record_delete),
)}
ACTION_TYPES.update(HEALTH_ACTIONS)


FORMS = {
    "sleep": [{"name": "hours", "label": "Hours slept", "type": "number", "required": True},
              {"name": "rested", "label": "How rested, 1 (not at all) to 5 (fully)", "type": "int"},
              {"name": "night", "label": "The night of", "type": "date"},
              {"name": "note", "label": "Note", "type": "text"}],
    "visit": [{"name": "kind", "label": "Kind", "type": "choice", "options": list(VISIT_KINDS)},
              {"name": "when", "label": "When", "type": "date", "required": True},
              {"name": "who", "label": "Who (doctor or office)", "type": "text"},
              {"name": "what_for", "label": "What for", "type": "text"},
              {"name": "next_due", "label": "Next one due", "type": "date"},
              {"name": "notes", "label": "Notes", "type": "textarea"}],
    "med": [{"name": "name", "label": "Name", "type": "text", "required": True},
            {"name": "kind", "label": "Kind", "type": "choice", "options": ["Medication", "Supplement"]},
            {"name": "dose", "label": "Dose, as written on the label", "type": "text"},
            {"name": "times", "label": "Times to take it, like 8:00, 20:00 (each gets a reminder)", "type": "text"},
            {"name": "refills", "label": "Refills left", "type": "int"},
            {"name": "refill_on", "label": "Next refill", "type": "date"},
            {"name": "notes", "label": "Notes", "type": "textarea"}],
    "record": [{"name": "kind", "label": "Kind", "type": "choice", "options": list(RECORD_KINDS)},
               {"name": "name", "label": "What (a test, a vaccine, an allergy...)", "type": "text", "required": True},
               {"name": "when", "label": "Date", "type": "date"},
               {"name": "value", "label": "Result or value (with units)", "type": "text"},
               {"name": "notes", "label": "Notes", "type": "textarea"}],
}


def health_page(context, today: Optional[date] = None) -> dict:
    """The Health page: the week's sleep and its average, visits (next due first, then latest), medications (active
    first, each with today's doses and times), records by kind, what's coming up, and the forms. Not available without
    the store."""
    store = getattr(context, "health", None)
    if store is None:
        return {"available": False}
    today = today or date.today()
    visits = sorted(store.visits, key=lambda v: v.get("when", ""), reverse=True)
    meds = sorted(store.meds, key=lambda m: (not m.get("active", True), m["name"].lower()))
    return {
        "available": True,
        "sleep": store.sleep_week(today),
        "visits": [{**v, "upcoming": v["when"] >= today.isoformat()} for v in visits],
        "meds": [{**{k: v for k, v in m.items() if k != "alarm_ids"}, "taken_today": store.taken_today(m["id"], today),
                  "reminders": bool(m.get("alarm_ids"))} for m in meds],
        "records": sorted(store.records, key=lambda r: (RECORD_KINDS.index(r["kind"]) if r["kind"] in RECORD_KINDS
                                                         else 99, r.get("when", "")), reverse=False),
        "due": store.due(today),
        "forms": FORMS,
    }
