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
to the same check. `hardware()` turns the same inspection's facts into the
screen's hardware list (This PC), saying only what was read; and
`recent_problems()` reads the newest warnings and errors from MIA's own log
("any errors in your log?" reads them out: `log_words`). `repository_view()`
puts the inspection of her own repository (T-0020: where her docs disagree
with it) on the same screen, grouped.
"""

from __future__ import annotations

import fnmatch
import re
from pathlib import Path
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


def hardware(facts: dict) -> list[dict]:
    """Pure logic. The hardware list for the Diagnostics screen, from one inspection's facts: the computer, its
    processor, memory, each drive of a gigabyte or more (size, free, how full), each network adapter with an address,
    when it started and its Python. A part the inspection couldn't read is left out, never guessed."""
    rows = []

    def add(name, value, note=""):
        """One row, only when there's something to say."""
        if value not in (None, ""):
            rows.append({"name": name, "value": str(value), "note": note})

    add("Computer", facts.get("computer.name"), facts.get("os.machine", ""))
    cores, threads = facts.get("cpu.cores_physical"), facts.get("cpu.threads")
    add("Processor", facts.get("cpu.model"), " · ".join(x for x in (f"{cores} cores" if cores else "",
                                                                        f"{threads} threads" if threads else "") if x))
    if facts.get("memory.total_gb") is not None:
        use = facts.get("memory.use_percent")
        add("Memory", f"{facts['memory.total_gb']:g} GB", f"{use:g}% in use" if isinstance(use, (int, float)) else "")
    drives = sorted({k[len("disk."):-len(".size_gb")] for k in facts if k.startswith("disk.") and k.endswith(".size_gb")})
    for drive in drives:
        size = facts.get(f"disk.{drive}.size_gb")
        if not isinstance(size, (int, float)) or size < 1:
            continue  # tiny or virtual mounts aren't drives anyone looks after
        free, use = facts.get(f"disk.{drive}.free_gb"), facts.get(f"disk.{drive}.use_percent")
        add("Drive " + ("/" if drive == "root" else drive), f"{size:g} GB",
            " · ".join(x for x in (f"{free:g} GB free" if isinstance(free, (int, float)) else "",
                                    f"{use:g}% full" if isinstance(use, (int, float)) else "") if x))
    for key in sorted(k for k in facts if k.startswith("network.") and k.endswith(".ipv4")):
        add("Network " + key[len("network."):-len(".ipv4")], facts[key])
    add("Started", str(facts.get("os.booted") or "").replace("T", " "))
    add("Python", facts.get("python.version"))
    return rows


_LOG_LINE = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \[(WARNING|ERROR|CRITICAL)\s*\] ([\w.]+): (.*)$")


def recent_problems(log_file: Optional[Path] = None, limit: int = 30, read_bytes: int = 400_000) -> list[dict]:
    """The newest warnings and errors in MIA's log (logs/mia.log, core/logger.py), newest first: when, how bad
    (warning or error), which part of MIA said it (without the "mia." prefix) and what, cut at 300 characters. Only
    the end of the file is read; [] when there's no log."""
    if log_file is None:
        from core.logger import _LOG_FILE as log_file
    try:
        with open(log_file, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - read_bytes))
            text = f.read().decode("utf-8", errors="replace")
    except OSError:
        return []
    found = []
    for line in text.splitlines():
        m = _LOG_LINE.match(line)
        if m:
            found.append({"when": m.group(1), "level": "warning" if m.group(2) == "WARNING" else "error",
                          "where": m.group(3).removeprefix("mia."), "text": m.group(4)[:300]})
    return list(reversed(found))[:limit]


REPO_GROUPS = (("repository.doc_paths_missing", "Files Her Docs Name That Aren't There"),
               ("repository.built_files_missing", "Built (Say the Decisions) But Missing"),
               ("repository.requirements_missing", "Listed Requirements Not Installed"))


def repository_view(report) -> dict:
    """Pure logic. Her own repository's read-only inspection (core/inspection.py's `repository` subject, T-0020) as the
    page shows it: how many places her docs disagree with it, grouped (each group only when it has any), or why it
    couldn't be read (not a development install)."""
    if report is None:
        return {"available": False, "why": "", "findings": 0, "groups": []}
    facts = {e.fact: e.value for e in report.evidence}
    if "repository.findings" not in facts:
        why = next((g.why for g in getattr(report, "gaps", []) if getattr(g, "why", "")), "")
        return {"available": False, "why": why, "findings": 0, "groups": []}
    groups = [{"title": title, "items": [str(x) for x in facts.get(fact) or []]} for fact, title in REPO_GROUPS]
    return {"available": True, "why": "", "findings": int(facts["repository.findings"] or 0),
            "groups": [g for g in groups if g["items"]]}


def screen(context, inspect=None) -> dict:
    """The Diagnostics web screen (web/diagnostics.html, the PC's owner's): every built-in check-up over one
    passive inspection, the hardware list it read (hardware), the log's newest problems (recent_problems), and where
    her docs disagree with her own repository (repository_view)."""
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
    facts = {}
    for e in report.evidence:
        facts.setdefault(e.fact, e.value)
    try:
        repo = repository_view(inspect(context, "repository"))
    except Exception:  # noqa: BLE001 - her repository is a side panel; the PC's check-up stands without it
        repo = repository_view(None)
    return {"checks": checks, "error": "", "hardware": hardware(facts), "problems": recent_problems(), "repository": repo}


_ASK = (("network", ("network", "internet connection", "wifi", "wi-fi", "connection")),
        ("big_download", ("download", "room for", "disk space", "space for")),
        ("pc_ready", ("check my pc", "check the pc", "pc check", "check-up", "checkup", "diagnose", "health check",
                      "is my pc", "is the pc")))


_LOG_ASK = ("errors in your log", "errors in the log", "problems in your log", "problems in the log", "check your log",
            "check the log", "any errors lately", "anything in your log")


def log_words(problems: list[dict]) -> str:
    """Pure logic. The log's newest problems said aloud: how many, and the newest three."""
    if not problems:
        return "No warnings or errors in my log lately."
    errors = sum(1 for p in problems if p["level"] == "error")
    head = (f"{len(problems)} recent problem{'s' if len(problems) != 1 else ''} in my log"
            + (f", {errors} of them errors" if errors else ", all warnings") + ". Newest first: ")
    return head + "; ".join(f"{p['text']} ({p['where']}, {p['when'][11:16]})" for p in problems[:3]) + "."


def reply(context, text: str) -> Optional[str]:
    """"check my PC", "check the network", "is there room for a big download?": the check-up, in plain lines; "any
    errors in your log?": the log's newest problems (log_words)."""
    low = " ".join(str(text or "").lower().split())
    if any(w in low for w in _LOG_ASK):
        return log_words(recent_problems())
    if not any(w in low for w in ("check", "diagnos", "room for", "is my pc", "is the pc")):
        return None
    for key, words in _ASK:
        if any(w in low for w in words):
            try:
                return "\n".join(run(context, key)["lines"])
            except DiagnosticError as problem:
                return str(problem)
    return None
