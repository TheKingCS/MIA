"""
core.assistant_health_actions
===============================

Health by voice (DEC-0129, DEC-0125; the screen is web/health.html, the
records core/health_manager.py): "I slept seven hours, pretty rested", "add
a dentist visit on the 20th", "add vitamin D, 2000 IU at 8 am", "I took my
vitamin D", "stop the antibiotics", "add my tetanus shot from 2024", "how
have I been sleeping?". Each change is the same action the page uses, so
undo takes it back. MIA repeats what the person said; she never suggests a
dose, reads a result or names a condition.
"""

from __future__ import annotations

from core.assistant_actions import AssistantAction


def _run(context, kind: str, params: dict) -> str:
    """Runs a health action and says what happened (or why not)."""
    from core.actions import run_as_tool

    return run_as_tool(context, kind, params)


def _store(context):
    """The person's health store, or None."""
    return getattr(context, "health", None)


def _med(context, name: str):
    """(med, None) for the one medication the name means, or (None, what to say back)."""
    from core.assistant_lookup import resolve_by_name

    store = _store(context)
    if store is None:
        return None, "Health isn't set up on this MIA."
    return resolve_by_name(store.meds, name, lambda m: m["name"], "medication or supplement")


def _log_sleep(context, a: dict) -> str:
    """Tool log_sleep."""
    return _run(context, "sleep.log", {"hours": a.get("hours"), "rested": a.get("rested"), "night": a.get("night") or "",
                                       "note": a.get("note") or ""})


def _add_visit(context, a: dict) -> str:
    """Tool add_health_visit."""
    return _run(context, "visit.add", {k: a.get(k) or "" for k in ("kind", "when", "who", "what_for", "next_due", "notes")})


def _add_med(context, a: dict) -> str:
    """Tool add_medication."""
    return _run(context, "med.add", {k: a.get(k) or "" for k in ("name", "dose", "times", "kind", "refill_on", "notes")})


def _took(context, a: dict) -> str:
    """Tool took_medication."""
    med, problem = _med(context, str(a.get("name") or ""))
    return problem if med is None else _run(context, "med.take", {"med_id": med["id"]})


def _stop(context, a: dict) -> str:
    """Tool stop_medication (or restart it)."""
    med, problem = _med(context, str(a.get("name") or ""))
    if med is None:
        return problem
    return _run(context, "med.edit", {"med_id": med["id"], "active": "no" if a.get("stop", True) else "yes"})


def _add_record(context, a: dict) -> str:
    """Tool add_health_record."""
    return _run(context, "record.add", {k: a.get(k) or "" for k in ("kind", "name", "when", "value", "notes")})


def _summary(context, a: dict) -> str:
    """Tool get_health: the week's sleep, the medications and doses today, visits coming up, or the records."""
    store = _store(context)
    if store is None:
        return "Health isn't set up on this MIA."
    what = str(a.get("what") or "all").lower()
    parts = []
    if what in ("sleep", "all"):
        week = store.sleep_week()
        logged = [n for n in week["nights"] if n["hours"] is not None]
        parts.append(f"Sleep: {len(logged)} of the last 7 nights logged, averaging {week['average']:g} hours."
                     if logged else "Sleep: no nights logged this week.")
    if what in ("meds", "medications", "all"):
        active = [m for m in store.meds if m.get("active", True)]
        parts.append("Medications and supplements: " + "; ".join(
            f"{m['name']}{' ' + m['dose'] if m['dose'] else ''}"
            + (f" at {', '.join(m['times'])}" if m["times"] else "") + f" ({store.taken_today(m['id'])} taken today)"
            for m in active) + "." if active else "No medications or supplements listed.")
    if what in ("visits", "all"):
        due = [d for d in store.due() if d["what"] == "visit"]
        upcoming = sorted((v for v in store.visits if v.get("next_due")), key=lambda v: v["next_due"])
        if upcoming:
            parts.append("Next visits due: " + "; ".join(f"{v['kind']} {v['next_due']}" for v in upcoming[:3]) + ".")
        elif not due:
            parts.append("No visits coming up.")
    if what in ("records", "all"):
        parts.append(f"{len(store.records)} health record{'s' if len(store.records) != 1 else ''} kept."
                     if what == "all" else "; ".join(f"{r['kind']}: {r['name']}" + (f" {r['value']}" if r["value"] else "")
                                                     + (f" ({r['when']})" if r["when"] else "") for r in store.records)
                     or "No health records kept yet.")
    return " ".join(parts)


def register_health_actions(registry) -> None:
    """Registers log_sleep, add_health_visit, add_medication, took_medication, stop_medication, add_health_record and
    get_health (domain health), and get_wallet (the ID wallet's names and expiry dates, never a number)."""
    s, n, b = {"type": "string"}, {"type": "number"}, {"type": "boolean"}
    reg = lambda name, desc, props, req, handler, phrases: registry.register(AssistantAction(  # noqa: E731
        name=name, domain="health", description=desc,
        parameters={"type": "object", "properties": props, "required": req}, handler=handler, trigger_phrases=phrases))
    reg("log_sleep", "Logs a night's sleep: hours and how rested, 1 (not at all) to 5 (fully).",
        {"hours": {**n, "description": "Hours slept."}, "rested": {**n, "description": "1 to 5."},
         "night": {**s, "description": "YYYY-MM-DD, the night of; last night if not said."}}, ["hours"], _log_sleep,
        ("i slept", "hours of sleep", "log my sleep", "slept"))
    reg("add_health_visit", "Saves a doctor, dentist, eye or other visit, and when the next is due.",
        {"kind": {**s, "description": "Doctor, Dentist, Eye or Other."}, "when": {**s, "description": "YYYY-MM-DD."},
         "who": {**s, "description": "The doctor or office."}, "what_for": s,
         "next_due": {**s, "description": "YYYY-MM-DD the next one is due."}}, ["when"], _add_visit,
        ("doctor visit", "dentist", "appointment", "checkup"))
    reg("add_medication", "Adds a medication or supplement as written on its label, with times for daily reminders.",
        {"name": s, "dose": {**s, "description": "As written on the label."},
         "times": {**s, "description": "Times to take it, like '8:00, 20:00'."},
         "kind": {**s, "description": "Medication or Supplement."}, "refill_on": {**s, "description": "YYYY-MM-DD."}},
        ["name"], _add_med, ("add a medication", "add my vitamin", "add a supplement", "prescription"))
    reg("took_medication", "Logs a dose of a listed medication or supplement as taken now.",
        {"name": s}, ["name"], _took, ("i took", "took my", "taken my"))
    reg("stop_medication", "Stops a listed medication or supplement (its reminders go off), or restarts it.",
        {"name": s, "stop": {**b, "description": "False to restart it."}}, ["name"], _stop,
        ("stop taking", "stopped my", "no longer taking"))
    reg("add_health_record", "Saves a health record as given: a test result, a vaccination, an allergy or a document.",
        {"kind": {**s, "description": "Test result, Vaccination, Allergy, Document or Other."}, "name": s,
         "when": {**s, "description": "YYYY-MM-DD."}, "value": {**s, "description": "The result, with units."}},
        ["name"], _add_record, ("vaccination", "allergic to", "test result", "lab result"))
    reg("get_health", "The user's own health records: the week's sleep, medications and doses today, visits coming "
        "up, or the records.", {"what": {**s, "description": "sleep, meds, visits, records or all."}}, [], _summary,
        ("how have i been sleeping", "what medications", "my health", "when is my next"))
    reg("get_wallet", "The user's ID wallet: each card's name and when it expires (never a number). To show a card, "
        "they say 'show my' and its name.", {}, [], lambda c, a: __import__("core.id_wallet", fromlist=["describe"]).describe(c),
        ("my passport expire", "my license expire", "id wallet", "when does my"))
