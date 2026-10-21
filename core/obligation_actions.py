"""
core.obligation_actions
=========================

Obligations' actions (DEC-0040, core/obligations.py) on the action
contract: proposed in plain words, approved, run, undoable. Grown-ups
only (money and legal matters).

- `obligation.add/edit/delete`: one obligation.
- `obligation.verify`: someone checked the official source: its link,
  the day, and whether it applies (or doesn't). The only way an
  obligation becomes verified.
- `obligation.status`: submitted, paid, done…, with proof; a repeating
  one that's done makes the next one.
- `obligation.starters`: starters to verify (`s_<id>`), added as tasks
  to check, never as confirmed.
"""

from __future__ import annotations

from datetime import date

from core.actions import ACTION_TYPES, ActionError, ActionType, _need
from core.obligations import CLOSED, JURISDICTIONS, KINDS, RECURRENCES, STATUSES
from core.record_actions import Field, Record, record_kinds

OBLIGATION = Record("obligation", "obligation", "obligation_id", "get", "add", "update", "delete", store="obligations",
                    fields=(
                        Field("title", "What it is", "text", True),
                        Field("kind", "Kind", "choice", options=KINDS, default="other"),
                        Field("authority", "Owed to (IRS, the state, the county clerk…)", "text", say="authority"),
                        Field("jurisdiction", "Level", "choice", options=JURISDICTIONS, default="other",
                              quiet_default=True),
                        Field("applies_to", "For (the household, the rental, the homestead…)", "text", say="for"),
                        Field("period", "Period (2026 Q3, tax year 2026)", "text", say="period"),
                        Field("due_date", "Due (as the rule states it)", "date", say="due"),
                        Field("pay_date", "Money due (if different)", "date", say="money due"),
                        Field("extended_to", "Extended to (filing only; never moves the money's date)", "date",
                              say="extension"),
                        Field("recurrence", "Repeats", "choice", options=RECURRENCES, default="", quiet_default=True),
                        Field("fee", "Fee", "money", say="fee"),
                        Field("estimate", "Expected to owe", "money", say="estimate"),
                        Field("documents", "Documents needed", "textarea", say="documents"),
                        Field("next_action", "Next step", "text", say="next step"),
                        Field("source_url", "Official source (link)", "text", say="source"),
                        Field("rule", "The rule (form, statute, guidance)", "text", say="rule"),
                        Field("reminders", "Remind me this many days before (e.g. 90 60 30 14 7 0)", "text",
                              say="reminders"),
                        Field("notes", "Notes", "textarea"),
                    ))


def _grown_up(context) -> None:
    from core.child_accounts import is_child

    if is_child(context):
        raise ActionError("That's for a grown-up.")


def _obligation(context, params):
    _grown_up(context)
    o = _need(context, "obligations").get(str(params.get("obligation_id") or ""))
    if o is None:
        raise ActionError("That obligation isn't there anymore.")
    return o


def _day(raw, label: str) -> str:
    text = str(raw or "").strip()
    if not text:
        return date.today().isoformat()
    try:
        return date.fromisoformat(text[:10]).isoformat()
    except ValueError:
        raise ActionError(f"{label} has to look like 2026-10-21.") from None


# ---------------------------------------------------------------- verify


def _verifying(context, params):
    o = _obligation(context, params)
    url = str(params.get("source_url") or o.source_url or "").strip()
    if not url.startswith(("http://", "https://")) and not str(params.get("how") or "").strip():
        raise ActionError("Where did you check it? The official page's link, or who you asked (\"how\").")
    applies = str(params.get("applies") or "yes").lower() not in ("no", "false", "0")
    return o, url, _day(params.get("verified_on"), "The day you checked"), applies, str(params.get("how") or "").strip()


def _verify_describe(context, params) -> str:
    o, url, day, applies, how = _verifying(context, params)
    where = url or how
    return f"{o.title}: checked {day} ({where}); " + ("it applies" if applies else "it doesn't apply")


def _verify(context, params) -> str:
    o, url, day, applies, how = _verifying(context, params)
    notes = (o.notes + "\n" if o.notes else "") + f"Checked {day}: {how}" if how else o.notes
    status = ("applies" if o.status == "to verify" else o.status) if applies else "not applicable"
    context.obligations.update(o.obligation_id, source_url=url, verified_on=day, status=status, notes=notes)
    return "Verified." if applies else "Marked as not applying (kept, with when you checked)."


# ---------------------------------------------------------------- status


def _status(context, params):
    o = _obligation(context, params)
    status = str(params.get("status") or "")
    if status not in STATUSES or status == "to verify":
        raise ActionError("Pick where it stands.")
    return o, status, str(params.get("proof") or "").strip()


def _status_describe(context, params) -> str:
    from core.obligations import next_period

    o, status, proof = _status(context, params)
    text = f"{o.title}: {status}" + (f" (proof: {proof})" if proof else "")
    nxt = next_period(o) if status in CLOSED and status != "not applicable" else None
    if nxt and nxt["due_date"]:
        text += f"; then the next one, due {nxt['due_date']}"
    return text


def _status_run(context, params) -> str:
    from dataclasses import asdict

    from core.obligations import next_period

    o, status, proof = _status(context, params)
    book = context.obligations
    book.update(o.obligation_id, status=status, proof=proof or o.proof)
    nxt = next_period(o) if status in CLOSED and status != "not applicable" else None
    if nxt and nxt["due_date"]:
        carry = {k: v for k, v in asdict(o).items() if k not in ("obligation_id", "created_at", "closed_at", "proof",
                                                                    "title", "status", "extended_to", "period")}
        carry.update(nxt, status="applies" if o.verified_on else "to verify")
        book.add(o.title, **carry)
        return f"{o.title}: {status}. The next one is on the list, due {nxt['due_date']}."
    return f"{o.title}: {status}."


# ---------------------------------------------------------------- starters


def _picked(context, params) -> list[str]:
    from core.obligations import STARTERS_BY_ID

    _grown_up(context)
    _need(context, "obligations")
    picked = [name[2:] for name, value in params.items() if name.startswith("s_")
              and str(value).lower() in ("1", "true", "yes", "on") and name[2:] in STARTERS_BY_ID]
    if not picked:
        raise ActionError("Pick at least one to check.")
    have = {o.starter_id for o in context.obligations.obligations if o.starter_id and o.status not in CLOSED}
    fresh = [p for p in picked if p not in have]
    if not fresh:
        raise ActionError("Those are already on your list.")
    return fresh


def _starters_describe(context, params) -> str:
    from core.obligations import STARTERS_BY_ID

    names = [STARTERS_BY_ID[p]["title"] for p in _picked(context, params)]
    return f"Add {len(names)} to check (not confirmed, each with where to check it): " + "; ".join(names)


def _starters(context, params) -> str:
    from core.obligations import STARTERS_BY_ID, starter_fields

    today = date.today()
    for p in _picked(context, params):
        md = STARTERS_BY_ID[p].get("month_day")
        year = today.year + (1 if md and date(today.year, *md) < today else 0)
        fields = starter_fields(p, year)
        context.obligations.add(fields.pop("title"), **fields)
    return "Added. Each says where to check it; verify one and it becomes a confirmed deadline."


def _register() -> None:
    kinds = [k for k in record_kinds(OBLIGATION)] + [
        ActionType("obligation.verify", "Verify", {"obligation_id": "the obligation", "source_url": "the official page",
                                                   "how": "or: who you asked, how", "verified_on": "the day you checked",
                                                   "applies": "yes or no"}, _verify_describe, _verify),
        ActionType("obligation.status", "Update", {"obligation_id": "the obligation", "status": "where it stands",
                                                   "proof": "a confirmation number, a receipt"},
                   _status_describe, _status_run),
        ActionType("obligation.starters", "Add To Check", {"s_<id>": "yes for each starter"},
                   _starters_describe, _starters),
    ]
    for kind in kinds:
        ACTION_TYPES[kind.kind] = kind


_register()
