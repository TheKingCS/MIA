"""
core.model_inspection
=======================

Claude inspects MIA's models before they're used (DEC-0200; Zac, 2026-11-17: "MIA should have the ability to have
her models inspected by Claude to test and approve them. This is similar to the Night School detail we have
discussed."). The Specialist Forge's F6 (`docs/mia_os/MIA_OS_SPECIALIST_FORGE.md`).

**What's inspected** (`pending`): each specialist's chosen model (core/specialist_models.py) on the bench results it
was chosen from. A choice is identified by the specialist, the model and a fingerprint of those results, so a re-run
of the bench, or a different model winning, makes it pending again.

**How** (`inspect`): code assembles the evidence (the bench's counts for the specialist's disciplines, the problems it
got wrong, guessed or couldn't read, each with the question and what was expected) and asks the inspector, Claude
Code read-only, as Night School's teacher (Codex when Claude is resting), for a verdict in JSON: pass or hold, with
findings. The inspector reads; it changes nothing.

**What code holds it to** (`verdict_from`):
- a choice whose bench didn't pass can't be passed, whatever the inspector says (it's recorded as held, "the bench
  didn't pass");
- a reply that isn't a readable verdict is a hold, never a pass;
- every verdict is kept (`work/inspections.json`, in the repository, beside the bench's results): who inspected, when,
  the fingerprint, the verdict and the findings.

**What a pass does** (DEC-0200, as Claude read it): a model choice goes live on Claude's pass (`cleared`). Code
(a new specialist or calculator) still merges only on Zac's approval, with the inspection attached; that half waits
for the Forge's lab builds (F4).

Night School inspects one pending choice a night, before study hall (`core/night_school.py`).
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from core.data_root import work_path
from core.logger import get_logger

log = get_logger(__name__)

RECORD = work_path("inspections.json")
INSPECTORS = ("claude-code", "codex")
EVIDENCE_ROWS = 12  # problems shown to the inspector, at most
PASS, HOLD = "pass", "hold"

_ASK = """You are inspecting one of MIA's local models for one of her specialists before it is used (DEC-0200). You only
read; you change nothing. MIA's specialists never do arithmetic: the model chooses calculators and code computes, so
what matters is whether it chooses the right calculator with the person's own values, asks when a value is missing
instead of guessing, and replies in a form code can read.

The specialist: {name} ({disciplines}).
The model chosen for it: {model}. Why it was chosen: {why}

Its bench results for this work (the model choosing calculators; "good" counts right answers and correct questions):
{summary}

The problems it didn't get right, with what was expected:
{rows}

Decide whether this model should do this specialist's work. Hold it if it guesses missing values, picks the wrong
calculator for a kind of question that will come up often, or fails anything safety-critical (electrical, battery,
structural, food, chemicals). Reply with only a JSON object:
{{"verdict": "pass" or "hold", "findings": ["one short sentence each"], "checked": ["what you looked at"]}}"""


def fingerprint(model: str, summary: dict, disciplines: tuple) -> str:
    """Pure logic. What a verdict is about: the model and its results on these disciplines (a re-run changes it)."""
    cells = {d: summary.get("tools", {}).get(d) for d in disciplines}
    raw = json.dumps({"model": model, "cells": cells}, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def load(path: Optional[Path] = None) -> list[dict]:
    """Every verdict kept, oldest first; a missing or unreadable record is none."""
    try:
        data = json.loads(Path(path or RECORD).read_text(encoding="utf-8"))
        return [v for v in data.get("verdicts", []) if isinstance(v, dict)]
    except (OSError, ValueError, AttributeError):
        return []


def _save(verdicts: list[dict], path: Optional[Path] = None) -> None:
    """Writes the record atomically."""
    from core.atomic_write import atomic_write_text

    path = path or RECORD
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(Path(path), json.dumps({"about": "Claude's inspections of MIA's models (DEC-0200, "
                                                       "core/model_inspection.py)", "verdicts": verdicts},
                                             indent=1, ensure_ascii=False) + "\n")


def latest(specialist: str, print_: str, verdicts: Optional[list] = None) -> Optional[dict]:
    """The newest verdict on this exact choice, or None."""
    found = [v for v in (verdicts if verdicts is not None else load())
             if v.get("specialist") == specialist and v.get("fingerprint") == print_]
    return found[-1] if found else None


def _choice(specialist: str, results: dict):
    """(choice, disciplines, fingerprint or "") for a specialist on these results."""
    from core import specialist_models
    from core.specialist_work import DISCIPLINES

    disciplines = DISCIPLINES.get(specialist, ())
    choice = specialist_models.choose(specialist, results)
    if choice.model is None:
        return choice, disciplines, ""
    return choice, disciplines, fingerprint(choice.model, results.get(choice.model, {}), disciplines)


def pending(results: Optional[dict] = None, verdicts: Optional[list] = None) -> list[str]:
    """The specialists whose chosen model has no verdict on its current results, in the worksheet's order."""
    from core import specialist_models
    from core.specialist_work import DISCIPLINES

    results = specialist_models.load() if results is None else results
    verdicts = load() if verdicts is None else verdicts
    out = []
    for sid in DISCIPLINES:
        choice, _d, print_ = _choice(sid, results)
        if print_ and latest(sid, print_, verdicts) is None:
            out.append(sid)
    return out


def cleared(specialist: str, results: Optional[dict] = None, verdicts: Optional[list] = None) -> bool:
    """Whether the specialist's chosen model passed Claude's inspection on its current results."""
    from core import specialist_models

    results = specialist_models.load() if results is None else results
    _c, _d, print_ = _choice(specialist, results)
    found = latest(specialist, print_, verdicts) if print_ else None
    return bool(found and found.get("verdict") == PASS)


def evidence(specialist: str, model: str, rows_folder: Optional[Path] = None) -> list[dict]:
    """The bench problems in the specialist's disciplines this model didn't get right (tools mode), from its results
    file: [{task, verdict, ask, expected, said}], at most EVIDENCE_ROWS."""
    from core import eng_bench
    from core.specialist_models import RESULTS
    from core.specialist_work import DISCIPLINES

    folder = Path(rows_folder or RESULTS)
    path = folder / (model.replace(":", "_").replace("/", "_") + ".json")
    try:
        rows = json.loads(path.read_text(encoding="utf-8")).get("rows", [])
    except (OSError, ValueError):
        return []
    tasks = {t.id: t for t in eng_bench.TASKS}
    mine = set(DISCIPLINES.get(specialist, ()))
    out = []
    for row in rows:
        task = tasks.get(row.get("task", ""))
        if task is None or task.discipline not in mine or row.get("mode") != "tools":
            continue
        if row.get("verdict") in ("right", "asked"):
            continue
        out.append({"task": task.id, "verdict": row.get("verdict", ""), "ask": task.ask,
                    "expected": str(row.get("expected") or (f"ask for {task.missing}" if task.missing else
                                                            f"{task.answer} in {task.unit}"))[:200],
                    "said": " ".join(str(x) for x in (row.get("got"), row.get("detail")) if x)[:300]})
    return out[:EVIDENCE_ROWS]


def prompt(specialist: str, choice, disciplines: tuple, summary: dict, rows: list[dict]) -> str:
    """Pure logic. What the inspector is asked (see `_ASK`)."""
    from core.specialists import BY_ID

    cells = "\n".join(f"- {d}: {json.dumps(summary.get('tools', {}).get(d), sort_keys=True)}" for d in disciplines)
    shown = "\n".join(f"- {r['task']} ({r['verdict']}): {r['ask']} Expected: {r['expected']}. It said: {r['said']}"
                      for r in rows) or "- none: it got every one right"
    spec = BY_ID.get(specialist)
    return _ASK.format(name=spec.name if spec else specialist, disciplines=", ".join(disciplines), model=choice.model,
                       why=choice.why, summary=cells, rows=shown)


def verdict_from(reply: str, bench_passed: bool) -> tuple[str, list[str]]:
    """Pure logic. The verdict code accepts from the inspector's reply: never a pass against a failing bench, and a
    hold when the reply can't be read."""
    from core.night_school import _json_in

    try:
        data = _json_in(reply or "")
    except Exception:  # noqa: BLE001 - an unreadable reply is a hold
        data = {}
    said = str(data.get("verdict", "")).strip().lower()
    findings = [str(f)[:300] for f in (data.get("findings") or []) if str(f).strip()][:10]
    if said not in (PASS, HOLD):
        return HOLD, ["the inspector's reply couldn't be read as a verdict"] + findings
    if said == PASS and not bench_passed:
        return HOLD, ["the bench didn't pass, so it can't be passed"] + findings
    return said, findings


def inspect(specialist: str, ask: Callable[[str], str], inspector: str, results: Optional[dict] = None,
            now: Optional[datetime] = None, path: Optional[Path] = None, rows_folder: Optional[Path] = None) -> dict:
    """Inspects one specialist's chosen model and keeps the verdict. ValueError when there's no model to inspect."""
    from core import specialist_models

    results = specialist_models.load() if results is None else results
    choice, disciplines, print_ = _choice(specialist, results)
    if not print_:
        raise ValueError(f"{specialist} has no benched model to inspect.")
    rows = evidence(specialist, choice.model, rows_folder)
    reply = ask(prompt(specialist, choice, disciplines, results.get(choice.model, {}), rows))
    said, findings = verdict_from(reply, choice.passed)
    record = {"specialist": specialist, "model": choice.model, "fingerprint": print_, "verdict": said,
              "findings": findings, "bench_passed": choice.passed, "inspector": inspector,
              "at": (now or datetime.now()).isoformat(timespec="seconds")}
    verdicts = load(path)
    verdicts.append(record)
    _save(verdicts, path)
    return record


def said(results: Optional[dict] = None) -> str:
    """The inspections in words, for voice: which specialists' models Claude passed, held, or hasn't looked at."""
    from core import specialist_models
    from core.specialist_work import DISCIPLINES
    from core.specialists import BY_ID

    results = specialist_models.load() if results is None else results
    verdicts = load()
    passed, held, waiting = [], [], []
    for sid in DISCIPLINES:
        _c, _d, print_ = _choice(sid, results)
        if not print_:
            continue
        name = BY_ID[sid].name if sid in BY_ID else sid
        found = latest(sid, print_, verdicts)
        (waiting if found is None else passed if found["verdict"] == PASS else held).append(
            name if found is None or found["verdict"] == PASS else f"{name} ({(found['findings'] or ['held'])[0]})")
    parts = []
    if passed:
        parts.append("Claude passed the models for " + ", ".join(passed) + ".")
    if held:
        parts.append("Held: " + "; ".join(held) + ".")
    if waiting:
        parts.append("Not inspected yet: " + ", ".join(waiting) + ". Night School inspects one a night.")
    return " ".join(parts) or "There are no benched models to inspect yet."
