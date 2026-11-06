"""
core.diagnostics
==================

Diagnostic procedures (ACAF step 4, T-0040; `docs/ACAF_REVIEW.md` section 6):
a check-up written as a spec, not code, over what inspection's PASSIVE
methods already read (core/inspection.py: the OS, CPU and memory, the drives,
the network, the firewall, the AI runtime, MIA's own health). Nothing here
probes, scans or changes anything: a procedure can only name facts a passive
method gives, and compare them.

A spec: `{"kind": "diagnostic", "title", "subject", "checks": [{"fact",
"op", "value", "say"}]}`. `fact` may end in `*` for every drive or adapter
(`disk.*.free_gb`); `op` is one of `OPS`; `say` is what MIA tells the person
when the check fails (`{value}` and `{item}` fill in). `check()` says
everything wrong with a spec before it's kept or run; `run()` inspects and
answers in plain lines, with what couldn't be read said as such (never as a
pass).

`PROCEDURES` are the built-in ones; MIA can make more as specs (ACAF), held
to the same check.
"""

from __future__ import annotations

import fnmatch
from typing import Optional

OPS = {"<": lambda a, b: a < b, "<=": lambda a, b: a <= b, ">": lambda a, b: a > b, ">=": lambda a, b: a >= b,
       "==": lambda a, b: a == b, "!=": lambda a, b: a != b, "present": lambda a, b: a not in (None, "", [], {}),
       "contains": lambda a, b: str(b).lower() in str(a).lower()}
# the facts a PASSIVE method gives (core/inspection.py), by prefix
FACTS = ("os.", "computer.", "python.", "cpu.", "memory.", "gpu.", "motherboard", "firmware.", "disk.", "network.",
         "devices.", "security.", "ai.", "health.", "mia.", "code.", "decisions.", "capabilities.", "issues.", "internet")

PROCEDURES = {
    "pc_ready": {"kind": "diagnostic", "title": "Is the PC ready for MIA?", "subject": "this_computer", "checks": [
        {"fact": "disk.C.free_gb", "op": ">=", "value": 20, "say": "Drive C has {value} GB free: under 20 GB, models and "
                                                                    "updates run out of room."},
        {"fact": "memory.use_percent", "op": "<", "value": 90, "say": "Memory is {value}% used."},
        {"fact": "cpu.use_percent", "op": "<", "value": 90, "say": "The processor is {value}% busy."},
        {"fact": "security.firewall", "op": "==", "value": "on for every profile",
         "say": "The firewall isn't on everywhere ({value})."},
        {"fact": "ai.model", "op": "present", "value": None, "say": "No AI model is answering on this PC."}]},
    "network": {"kind": "diagnostic", "title": "The network", "subject": "this_computer", "checks": [
        {"fact": "network.*.ipv4", "op": "present", "value": None, "say": "{item} has no address."},
        {"fact": "network.Ethernet.speed_mbps", "op": ">=", "value": 1000,
         "say": "The wired connection is running at {value} Mb/s, under a gigabit."}]},
    "big_download": {"kind": "diagnostic", "title": "Room for a big download", "subject": "this_computer", "checks": [
        {"fact": "disk.*.free_gb", "op": ">=", "value": 50, "say": "Drive {item} has {value} GB free."}]},
}


class DiagnosticError(ValueError):
    """A procedure that can't be run as written; the message says why."""


def check(spec: dict) -> list[str]:
    """Pure logic. Everything wrong with a diagnostic spec ([] when it's fine)."""
    from core.inspection import SUBJECTS

    problems = []
    if not isinstance(spec, dict) or spec.get("kind") != "diagnostic":
        return ["A diagnostic's kind is \"diagnostic\"."]
    if not str(spec.get("title", "")).strip():
        problems.append("It needs a title.")
    if spec.get("subject") not in SUBJECTS:
        problems.append(f"Its subject is one of {', '.join(SUBJECTS)}.")
    checks = spec.get("checks")
    if not isinstance(checks, list) or not 1 <= len(checks) <= 20:
        problems.append("It needs 1 to 20 checks.")
        return problems
    for i, c in enumerate(checks, 1):
        if not isinstance(c, dict):
            problems.append(f"Check {i} isn't a check.")
            continue
        fact = str(c.get("fact", ""))
        if not fact.startswith(FACTS):
            problems.append(f"Check {i}: {fact!r} isn't something inspection reads passively.")
        if c.get("op") not in OPS:
            problems.append(f"Check {i}: the comparison is one of {', '.join(OPS)}.")
        if c.get("op") in ("<", "<=", ">", ">=") and not isinstance(c.get("value"), (int, float)):
            problems.append(f"Check {i}: {c.get('op')} needs a number.")
        if not str(c.get("say", "")).strip():
            problems.append(f"Check {i}: say what it means when it fails.")
    return problems


def evaluate(spec: dict, facts: dict) -> dict:
    """Pure logic. The checks against the facts: {"passed", "failed": [lines], "unknown": [facts]}."""
    passed, failed, unknown = 0, [], []
    for c in spec["checks"]:
        matched = {k: v for k, v in facts.items() if fnmatch.fnmatchcase(k, c["fact"])}
        if not matched:
            unknown.append(c["fact"])
            continue
        for fact, value in matched.items():
            item = fact.split(".")[1] if fact.count(".") >= 2 else fact
            try:
                ok = OPS[c["op"]](value, c.get("value"))
            except TypeError:
                unknown.append(fact)
                continue
            if ok:
                passed += 1
            else:
                failed.append(str(c["say"]).replace("{value}", f"{value:g}" if isinstance(value, float) else str(value))
                              .replace("{item}", item))
    return {"passed": passed, "failed": failed, "unknown": unknown}


def run(context, procedure, inspect=None) -> dict:
    """A procedure (a built-in's id, or a spec) run over a fresh passive inspection: {"title", "lines", ...}."""
    spec = PROCEDURES.get(procedure) if isinstance(procedure, str) else procedure
    if spec is None:
        raise DiagnosticError(f"No check-up called {procedure}; there are {', '.join(PROCEDURES)}.")
    problems = check(spec)
    if problems:
        raise DiagnosticError("That check-up can't run: " + "; ".join(problems[:3]))
    if inspect is None:
        from core.inspection import inspect
    report = inspect(context, spec["subject"])
    facts = {}
    for e in report.evidence:
        facts.setdefault(e.fact, e.value)  # correlated: the first is the confirmed one
    result = evaluate(spec, facts)
    lines = [f"{spec['title']}: " + ("all good" if not result["failed"] else f"{len(result['failed'])} to look at")
             + f" ({result['passed']} check{'s' if result['passed'] != 1 else ''} passed)."]
    lines += [f"- {line}" for line in result["failed"]]
    if result["unknown"]:
        lines.append("Couldn't read: " + ", ".join(sorted(set(result["unknown"]))) + " (not a pass, not a failure).")
    return {"title": spec["title"], "lines": lines, **result}


def screen(context, inspect=None) -> dict:
    """The Diagnostics web screen (web/diagnostics.html, the PC's owner's): every built-in check-up over one
    passive inspection."""
    if inspect is None:
        from core.inspection import inspect
    try:
        report = inspect(context, "this_computer")
    except Exception as problem:
        return {"checks": [], "error": f"The PC couldn't be inspected: {str(problem)[:200]}"}
    once = lambda _context, _subject: report  # noqa: E731
    checks = []
    for pid, spec in PROCEDURES.items():
        try:
            done = run(context, pid, inspect=once)
        except DiagnosticError as problem:
            done = {"title": spec["title"], "lines": [str(problem)], "passed": 0, "failed": [str(problem)],
                    "unknown": []}
        checks.append({"id": pid, "title": done["title"], "ok": not done["failed"], "passed": done["passed"],
                       "failed": done["failed"], "unknown": sorted(set(done["unknown"]))})
    return {"checks": checks, "error": ""}


_ASK = (("network", ("network", "internet connection", "wifi", "wi-fi", "connection")),
        ("big_download", ("download", "room for", "disk space", "space for")),
        ("pc_ready", ("check my pc", "check the pc", "pc check", "check-up", "checkup", "diagnose", "health check",
                      "is my pc", "is the pc")))


def reply(context, text: str) -> Optional[str]:
    """"check my PC", "check the network", "is there room for a big download?": the check-up, in plain lines."""
    low = " ".join(str(text or "").lower().split())
    if not any(w in low for w in ("check", "diagnos", "room for", "is my pc", "is the pc")):
        return None
    for key, words in _ASK:
        if any(w in low for w in words):
            try:
                return "\n".join(run(context, key)["lines"])
            except DiagnosticError as problem:
                return str(problem)
    return None
