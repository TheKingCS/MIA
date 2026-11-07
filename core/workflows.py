"""
core.workflows
================

Workflows MIA makes (ACAF step 3, DEC-0092; `docs/ACAF_REVIEW.md` section 6):
something done again and again, written as a specification, not code. A
trigger (every day, week or month) and steps from a fixed vocabulary:

- `read`: records from a source (core/creation_sources.py: `history:spending`)
  or one of the person's published screens (`creation:C-0001`), optionally
  within the last N days, kept under a name;
- `count`, `sum`, `avg`, `min`, `max`, `latest`: a number from what was read;
- `when`: steps that run only if a number is above, below or equal to a value;
- `tell`: a message, made from those numbers, offered through the
  communication gate (its daily limit, no repeats), never sent around it;
- `add`: a record into one of the person's own published screens, through
  the `records.add` action, so it's in the history and undoable.

**Standing approval by kind**: publishing a workflow approves exactly what it
lists it may do (tell, add to which screen, how many adds a run), within its
limits; a new kind needs approving again (a new version). `dry_run()` shows
what it would do without doing any of it. Every run is logged on the
creation. Like screens, no HTML, script or free formula: placeholders in a
message are only the workflow's own numbers.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Optional

STEPS = ("read", "count", "sum", "avg", "min", "max", "latest", "when", "tell", "add")
NUMBERS = ("count", "sum", "avg", "min", "max", "latest")
EVERY = ("day", "week", "month")
MAX_STEPS = 12
MAX_ADDS = 5
NAME = re.compile(r"^[a-z][a-z0-9_]{0,23}$")
PLACEHOLDER = re.compile(r"\{([a-z][a-z0-9_]*)\}")
KEYS = {"read": {"step", "source", "within_days", "as"}, "when": {"step", "value", "above", "below", "equals", "then"},
        "tell": {"step", "title", "text"}, "add": {"step", "to", "values"}}
for _n in NUMBERS:
    KEYS[_n] = {"step", "of", "as"}


def _sources(context, child: bool) -> dict:
    """name -> fields for every source this person's workflow may read."""
    from core import creation_sources

    out = {f"history:{s.id}": {f["name"]: f for f in s.fields} for s in creation_sources.listing(child)}
    store = getattr(context, "creations", None)
    for c in (store.published() if store is not None else []):
        spec = store.shown(c["id"])["spec"]
        if spec.get("kind") == "screen" and spec.get("record_set"):
            out[f"creation:{c['id']}"] = {f["name"]: f for f in spec["record_set"]["fields"]}
    return out


def check(spec: dict, context=None, child: bool = False) -> list[str]:
    """Every problem with a workflow spec; an empty list passes."""
    if not isinstance(spec, dict):
        return ["A workflow is a JSON object."]
    allowed = {"kind", "title", "about", "owner", "trigger", "steps", "limits"}
    problems = [f"Unknown part {k!r}." for k in spec if k not in allowed]
    if spec.get("kind") != "workflow":
        problems.append("Its kind is \"workflow\".")
    if not 1 <= len(str(spec.get("title", "")).strip()) <= 60:
        problems.append("It needs a title of up to 60 characters.")
    if spec.get("owner") not in ("personal", "household"):
        problems.append("It's personal or the household's.")
    trigger = spec.get("trigger") or {}
    if not isinstance(trigger, dict) or trigger.get("every") not in EVERY or set(trigger) - {"every", "weekday", "day"}:
        problems.append("Its trigger is {\"every\": \"day\" | \"week\" | \"month\"} (a week may add \"weekday\", 0-6; "
                        "a month \"day\", 1-28).")
    elif "weekday" in trigger and not (isinstance(trigger["weekday"], int) and 0 <= trigger["weekday"] <= 6):
        problems.append("weekday is 0 (Monday) to 6.")
    elif "day" in trigger and not (isinstance(trigger["day"], int) and 1 <= trigger["day"] <= 28):
        problems.append("day is 1 to 28.")
    limits = spec.get("limits") or {}
    adds_allowed = limits.get("adds_per_run", 0)
    if not isinstance(adds_allowed, int) or not 0 <= adds_allowed <= MAX_ADDS:
        problems.append(f"adds_per_run is 0 to {MAX_ADDS}.")
    sources = _sources(context, child)
    names: dict[str, Optional[dict]] = {}  # name -> fields (a read) or None (a number)

    def walk(steps, where: str, depth: int) -> None:
        if not isinstance(steps, list) or not steps:
            problems.append(f"{where}: it needs steps.")
            return
        for i, s in enumerate(steps, 1):
            at = f"{where} step {i}"
            if not isinstance(s, dict) or s.get("step") not in STEPS:
                problems.append(f"{at}: one of {', '.join(STEPS)}.")
                continue
            kind = s["step"]
            problems.extend(f"{at} ({kind}): unknown part {k!r}." for k in s if k not in KEYS[kind])
            if kind == "read":
                if s.get("source") not in sources:
                    problems.append(f"{at}: there's no source {s.get('source')!r} this person can read.")
                if not NAME.match(str(s.get("as", ""))):
                    problems.append(f"{at}: name what's read with \"as\" (lower-case).")
                elif s.get("source") in sources:
                    names[s["as"]] = sources[s["source"]]
                if "within_days" in s and not (isinstance(s["within_days"], int) and 1 <= s["within_days"] <= 366):
                    problems.append(f"{at}: within_days is 1 to 366.")
            elif kind in NUMBERS:
                of, _, field = str(s.get("of", "")).partition(".")
                if names.get(of) is None:
                    problems.append(f"{at}: {of!r} isn't something read before this step.")
                elif kind == "count" and field:
                    problems.append(f"{at}: count counts {of}'s records and takes no field; to total {field}, use sum.")
                elif kind != "count":
                    fields = names[of]
                    if field not in fields:
                        problems.append(f"{at}: {kind} needs a field, like {of}.{next(iter(fields), 'amount')}.")
                    elif kind in ("sum", "avg") and fields[field]["type"] not in ("number", "money"):
                        problems.append(f"{at}: {kind} needs a number or money field.")
                if not NAME.match(str(s.get("as", ""))):
                    problems.append(f"{at}: name the number with \"as\".")
                else:
                    names[s["as"]] = None
            elif kind == "when":
                if s.get("value") not in names or names[s["value"]] is not None:
                    problems.append(f"{at}: \"value\" is a number worked out before this step.")
                tests = [k for k in ("above", "below", "equals") if k in s]
                if len(tests) != 1 or not isinstance(s[tests[0]], (int, float)):
                    problems.append(f"{at}: one of above, below or equals, with a number.")
                if depth:
                    problems.append(f"{at}: a when can't hold another when.")
                walk(s.get("then"), at, depth + 1)
            elif kind == "tell":
                text = str(s.get("text", ""))
                if not 1 <= len(text.strip()) <= 300 or len(str(s.get("title", ""))) > 60:
                    problems.append(f"{at}: a message of up to 300 characters (and a short title).")
                problems.extend(f"{at}: {{{p}}} isn't a number this workflow works out." for p in PLACEHOLDER.findall(text)
                                if p not in names or names[p] is not None)
            elif kind == "add":
                target = sources.get(str(s.get("to", "")))
                if not str(s.get("to", "")).startswith("creation:") or target is None:
                    problems.append(f"{at}: \"to\" is one of your published screens with its own records.")
                elif not isinstance(s.get("values"), dict) or not s["values"]:
                    problems.append(f"{at}: the values to add.")
                else:
                    problems.extend(f"{at}: there's no field {k!r} there." for k in s["values"] if k not in target)
                    problems.extend(f"{at}: {{{p}}} isn't a number this workflow works out."
                                    for v in s["values"].values() for p in PLACEHOLDER.findall(str(v))
                                    if p not in names or names[p] is not None)
                if not adds_allowed:
                    problems.append(f"{at}: it adds records, so its limits need adds_per_run of 1 or more.")

    walk(spec.get("steps"), "", 0)
    if len(_flat(spec.get("steps") or [])) > MAX_STEPS:
        problems.append(f"At most {MAX_STEPS} steps.")
    return [p.lstrip(" ") for p in problems]


def _flat(steps) -> list[dict]:
    """Pure logic. A workflow's steps, nested then-steps included, as one flat list."""
    out = []
    for s in steps if isinstance(steps, list) else []:
        if isinstance(s, dict):
            out.append(s)
            out += _flat(s.get("then"))
    return out


def may(spec: dict) -> list[str]:
    """Pure logic. What approving it allows, in words (its standing approval)."""
    out = []
    flat = _flat(spec.get("steps"))
    if any(s.get("step") == "tell" for s in flat):
        out.append("tell you things (through MIA's message limits)")
    for to in sorted({s.get("to", "") for s in flat if s.get("step") == "add"}):
        out.append(f"add up to {spec.get('limits', {}).get('adds_per_run', 0)} record(s) a run to {to.split(':', 1)[-1]}")
    return out or ["only read"]


def describe(spec: dict) -> list[str]:
    """Pure logic. The workflow in plain sentences, for its screen and its approval."""
    t = spec.get("trigger", {})
    when = {"day": "Every day", "week": "Every week", "month": "Every month"}.get(t.get("every"), "")
    if "weekday" in t:
        when += " on " + ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")[t["weekday"]]
    if "day" in t:
        when += f" on day {t['day']}"
    lines = [when + ":"]

    def say(steps, indent=""):
        for s in steps:
            k = s.get("step")
            if k == "read":
                lines.append(f"{indent}read {s['source'].split(':', 1)[-1]}" +
                             (f" from the last {s['within_days']} days" if s.get("within_days") else "") + f" ({s['as']})")
            elif k in NUMBERS:
                lines.append(f"{indent}{k} of {s['of']} as {s['as']}")
            elif k == "when":
                test = next(k2 for k2 in ("above", "below", "equals") if k2 in s)
                lines.append(f"{indent}if {s['value']} is {test} {s[test]:g}:")
                say(s.get("then") or [], indent + "  ")
            elif k == "tell":
                lines.append(f"{indent}tell you: “{s['text']}”")
            elif k == "add":
                lines.append(f"{indent}add a record to {s['to'].split(':', 1)[-1]}")
    say(spec.get("steps") or [])
    return lines


# ------------------------------------------------------------------ running

def due(spec: dict, last_run: str, now: datetime) -> bool:
    """Pure logic. Whether the trigger has come round since the last run."""
    t, today = spec.get("trigger", {}), now.date()
    if last_run and last_run[:10] == today.isoformat():
        return False
    if t.get("every") == "day":
        return True
    if t.get("every") == "week":
        if today.weekday() != t.get("weekday", 0):
            return False
        return not last_run or date.fromisoformat(last_run[:10]) <= today - timedelta(days=6)
    if t.get("every") == "month":
        return today.day == t.get("day", 1) and (not last_run or last_run[:7] != today.isoformat()[:7])
    return False


def _records(context, source: str, within: Optional[int], now: datetime) -> tuple[list[dict], dict]:
    """A workflow's records and their fields from its source: history:<type> (life events) or a creation of hers (its sets), only those within the days given."""
    from core import creation_sources

    if source.startswith("history:"):
        rows = creation_sources.records(context, source.split(":", 1)[1])
        fields = {f["name"]: f for f in creation_sources.fields_of(source.split(":", 1)[1])}
    else:
        from core.creation_actions import sets_for

        store = context.creations
        found = store.get(source.split(":", 1)[1])
        spec = store.shown(found["id"])["spec"]
        rows = sets_for(context, found["owner"]).get(found["set_id"])["records"]
        fields = {f["name"]: f for f in spec["record_set"]["fields"]}
    if within:
        cut = (now.date() - timedelta(days=within)).isoformat()
        dated = next((n for n, f in fields.items() if f["type"] == "date"), None)
        rows = [r for r in rows if str(r["values"].get(dated) or r.get("at", ""))[:10] >= cut]
    return rows, fields


def run(context, creation_id: str, dry: bool = False, now: Optional[datetime] = None) -> dict:
    """Run a published workflow (or, `dry`, show what it would do). Returns {"lines", "offers", "added"}.
    Offers are Candidates for the communication gate; the caller offers them."""
    from core.communication_gate import Candidate
    from core.region import money

    now = now or datetime.now()
    store = context.creations
    found = store.get(creation_id)
    spec = store.shown(creation_id)["spec"]
    if not dry and found["status"] != "published":
        raise ValueError(f"{found['title']} isn't published.")
    problems = check(spec, context)
    if problems:
        raise ValueError("It doesn't pass its checks now: " + " ".join(problems[:3]))
    values: dict[str, object] = {}
    texts: dict[str, str] = {}
    read: dict[str, tuple[list[dict], dict]] = {}
    lines, offers, added = [], [], 0
    limit = (spec.get("limits") or {}).get("adds_per_run", 0)

    def fill(text: str) -> str:
        return PLACEHOLDER.sub(lambda m: texts.get(m.group(1), "?"), text)

    def do(steps) -> None:
        nonlocal added
        for s in steps:
            k = s["step"]
            if k == "read":
                read[s["as"]] = _records(context, s["source"], s.get("within_days"), now)
                lines.append(f"read {len(read[s['as']][0])} from {s['source'].split(':', 1)[-1]}")
            elif k in NUMBERS:
                of, _, field = s["of"].partition(".")
                rows, fields = read[of]
                present = [r["values"].get(field) for r in rows if r["values"].get(field) is not None] if field else rows
                if k == "count":
                    number = float(len(rows))
                elif not present:
                    number = None
                elif k == "latest":
                    number = present[-1]
                elif k in ("min", "max"):
                    number = (min if k == "min" else max)(present)
                else:
                    number = sum(present) / (len(present) if k == "avg" else 1)
                values[s["as"]] = number
                is_money = bool(field) and fields.get(field, {}).get("type") == "money"
                texts[s["as"]] = "—" if number is None else money(number) if is_money and isinstance(number, (int, float)) \
                    else f"{number:g}" if isinstance(number, float) else str(number)
                lines.append(f"{s['as']} = {texts[s['as']]}")
            elif k == "when":
                test = next(t for t in ("above", "below", "equals") if t in s)
                v = values.get(s["value"])
                ok = isinstance(v, (int, float)) and {"above": v > s[test], "below": v < s[test], "equals": v == s[test]}[test]
                lines.append(f"{s['value']} is {'' if ok else 'not '}{test} {s[test]:g}")
                if ok:
                    do(s["then"])
            elif k == "tell":
                message = fill(s["text"])
                offers.append(Candidate(topic=f"workflow:{creation_id}", title=s.get("title") or found["title"],
                                        message=message, source="workflow", fingerprint=f"{creation_id}:{now.date()}:{message}"))
                lines.append(f"{'would tell' if dry else 'tell'}: {message}")
            elif k == "add":
                if added >= limit:
                    lines.append("add skipped: this run's limit is reached")
                    continue
                params = {"creation_id": s["to"].split(":", 1)[1], "values": {f: fill(str(v)) for f, v in s["values"].items()}}
                if dry:
                    lines.append(f"would add to {params['creation_id']}: {params['values']}")
                else:
                    proposal = context.actions.propose(context, "records.add", params, proposed_by="mia")
                    result = context.actions.approve(context, proposal.proposal_id)  # its standing approval (DEC-0092)
                    lines.append(f"add: {result.result}")
                    if result.status == "executed":
                        added += 1
    do(spec["steps"])
    if not dry:
        store.log_run(creation_id, {"at": now.isoformat(timespec="seconds"), "lines": lines[:40]})
    return {"lines": lines, "offers": offers, "added": added}


def run_due(context, now: Optional[datetime] = None) -> list:
    """Every published workflow whose trigger has come round: run, and return the offers for the gate."""
    now = now or datetime.now()
    store = getattr(context, "creations", None)
    offers = []
    for c in (store.published() if store is not None else []):
        spec = store.shown(c["id"])["spec"]
        if spec.get("kind") != "workflow":
            continue
        last = (c.get("runs") or [{}])[-1].get("at", "")
        if due(spec, last, now):
            try:
                offers += run(context, c["id"], now=now)["offers"]
            except Exception as problem:  # one broken workflow never stops the others; its log says why
                store.log_run(c["id"], {"at": now.isoformat(timespec="seconds"), "lines": [f"stopped: {problem}"[:300]]})
    return offers
