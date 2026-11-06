"""
core.creation_maker
=====================

MIA making a screen for something nobody built one for (DEC-0088/0091;
ACAF's first maker, `docs/ACAF_REVIEW.md` section 3.5). From a need in plain
words ("I want to keep track of the seeds I save"):

1. Her local model designs the record set: a name, the fields and their
   types, who it belongs to, which blueprint fits, and, if she sees a better
   arrangement, her own blocks. Its reply is held to `DESIGN_SCHEMA`
   (Ollama's structured output), so it's always the right shape.
2. Code builds the spec: her own blocks if they pass the checks, else the
   blueprint's, filled from the fields (core/blueprints.py).
3. The checker (core/creation_spec.py) passes it or says why not; a failure
   goes back to the model once, with the reasons.
4. It's kept as a **draft** (core/creations.py), private, until the person
   approves `creation.publish`.

Nothing here changes any data: the record set itself is made only when the
creation is published.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Callable, Optional

from core import blueprints as bp
from core.creation_spec import BLOCKS, ICONS, check
from core.logger import get_logger
from core.record_sets import FIELD_TYPES

log = get_logger(__name__)

MODEL = "qwen2.5:14b"

DESIGN_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "icon": {"type": "string", "enum": list(ICONS)},
        "about": {"type": "string"},
        "owner": {"type": "string", "enum": ["personal", "household"]},
        "set_name": {"type": "string"},
        "fields": {"type": "array", "items": {"type": "object", "properties": {
            "name": {"type": "string"}, "label": {"type": "string"},
            "type": {"type": "string", "enum": list(FIELD_TYPES)},
            "choices": {"type": "array", "items": {"type": "string"}}}, "required": ["name", "label", "type"]}},
        "blueprint": {"type": "string"},
        "source": {"type": "string"},
        "blocks": {"type": "array", "items": {"type": "object"}},
    },
    "required": ["title", "icon", "owner", "set_name", "fields", "blueprint"],
}

PROMPT = """You design screens for MIA, a personal assistant. Someone said what they need. Design the records
it needs and how to show them. Reply only with JSON.

What they said: {need}

Rules:
- fields: 2 to 8, each with a name (lower_case_with_underscores), a label, and a type: text, number,
  money, date, choice (give its choices) or yesno. Prefer a choice when there are a few known options.
- owner: "household" if it's about the home, family or a shared business; "personal" if it's just theirs.
- blueprint: one of these.
{blueprints}
{hint}- source (optional): if what they want is about something MIA already keeps, name it here and
  leave fields empty; the screen shows that history and nothing new is stored. These exist:
{sources}
- blocks (optional): leave it out to use the blueprint. Give your own only if the blueprint wouldn't
  show it well. Blocks are: {blocks}. A value is {{"count": true}} or {{"sum"|"avg"|"min"|"max"|"latest": "field"}}. A chart
  over a date can add "by": "day", "week" or "month".
- icon: one of {icons}.
{again}"""


class MakerError(RuntimeError):
    """MIA couldn't make it; the message says why."""


def _ollama(prompt: str, schema: dict) -> str:
    import urllib.request

    body = json.dumps({"model": MODEL, "prompt": prompt, "stream": False, "format": schema,
                       "options": {"temperature": 0.2}}).encode("utf-8")
    request = urllib.request.Request("http://127.0.0.1:11434/api/generate", data=body,
                                     headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=300) as answer:
            return json.loads(answer.read()).get("response", "")
    except (OSError, ValueError) as problem:
        raise MakerError(f"My local model isn't answering ({problem}), so I can't design it right now.") from problem


PERIOD_WORDS = {"week": ("week", "weekly", "weeks"), "month": ("month", "monthly", "months"),
                "day": ("day", "daily", "days")}


def _periods(spec: dict, need: str) -> dict:
    """Pure logic. "each month", "per week": a chart over dates groups by that, if it doesn't already."""
    import re

    words = set(re.findall(r"[a-z]+", (need or "").lower()))
    by = next((p for p, said in PERIOD_WORDS.items() if words & set(said)), None)
    if not by:
        return spec
    from core.creation_spec import _fields

    fields = _fields(spec)
    blocks = [{**b, "by": by} if b.get("block") == "chart" and "by" not in b
              and fields.get(b.get("x"), {}).get("type") == "date" else b for b in spec["blocks"]]
    return {**spec, "blocks": blocks}


def spec_from(design: dict, blueprints: dict, need: str = "") -> tuple[dict, str]:
    """Pure logic. A design (the model's reply) -> a spec, and the blueprint it used ("" for her own blocks)."""
    spec, used = _spec_from(design, blueprints)
    return _periods(spec, need), used


def _spec_from(design: dict, blueprints: dict) -> tuple[dict, str]:
    from core.creation_sources import SOURCES, fields_of

    source = str(design.get("source") or "").removeprefix("history:")
    if source in SOURCES:
        base = {"kind": "screen", "title": str(design.get("title", ""))[:60] or SOURCES[source].title,
                "icon": design.get("icon") or "apps", "about": str(design.get("about", ""))[:300],
                "owner": design.get("owner", "personal"), "source": f"history:{source}"}
        own = [b for b in design.get("blocks") or [] if isinstance(b, dict) and b.get("block") != "form"]
        if own and not check({**base, "blocks": own}):
            return {**base, "blocks": own}, ""
        chosen = blueprints.get(design.get("blueprint")) or blueprints["log"]
        filled = [b for b in bp.fill(chosen, fields_of(source)) if b.get("block") != "form"]
        return {**base, "blocks": filled}, f"{chosen['id']}@{chosen['version']}"
    fields = [{k: f[k] for k in ("name", "label", "type", "choices") if k in f} for f in design.get("fields") or []]
    for f in fields:
        f["name"] = "".join(c if c.isalnum() else "_" for c in str(f["name"]).lower()).strip("_")[:32] or "field"
        if f["type"] != "choice":
            f.pop("choices", None)
    base = {"kind": "screen", "title": str(design.get("title", ""))[:60], "icon": design.get("icon") or "apps",
            "about": str(design.get("about", ""))[:300], "owner": design.get("owner", "personal"),
            "record_set": {"name": str(design.get("set_name") or design.get("title", ""))[:60], "fields": fields}}
    own = design.get("blocks")
    if own:
        candidate = {**base, "blocks": own}
        if not check(candidate):
            return candidate, ""
    chosen = blueprints.get(design.get("blueprint")) or blueprints["tracker"]
    return {**base, "blocks": bp.fill(chosen, fields)}, f"{chosen['id']}@{chosen['version']}"


RECURRING = re.compile(r"\b(every|each)\s+(day|morning|evening|night|week|month|monday|tuesday|wednesday|thursday|"
                       r"friday|saturday|sunday)\b|\bremind me\b|\blet me know (when|if)\b|\btell me (when|if)\b|"
                       r"\b(daily|weekly|monthly)\b", re.I)

WORKFLOW_SCHEMA = {"type": "object", "properties": {
    "title": {"type": "string"}, "owner": {"type": "string", "enum": ["personal", "household"]},
    "trigger": {"type": "object"}, "limits": {"type": "object"}, "steps": {"type": "array", "items": {"type": "object"}}},
    "required": ["title", "owner", "trigger", "steps"]}

WORKFLOW_PROMPT = """You design workflows for MIA, a personal assistant: something done again and again. Someone said
what they want. Reply only with JSON.

What they said: {need}

A workflow is: title, owner ("personal" or "household"), trigger {{"every": "day"|"week"|"month"}} (a week may
add "weekday": 0-6, Monday is 0; a month "day": 1-28), optional limits {{"adds_per_run": 0-5}}, and steps,
each one of:
- {{"step": "read", "source": <a source below>, "within_days": N (optional), "as": "name"}}
- {{"step": "count", "of": "name", "as": "n"}} or sum / avg / min / max / latest with "of": "name.field"
- {{"step": "when", "value": "n", "above"|"below"|"equals": number, "then": [steps]}} (no when inside a when)
- {{"step": "tell", "title": "...", "text": "a message; {{n}} puts in a number worked out above"}}
- {{"step": "add", "to": "creation:C-0001", "values": {{"field": "value"}}}} (needs limits.adds_per_run)

Sources it may read (and their fields):
{sources}
{again}"""


def _workflow_sources(context, child: bool) -> str:
    from core.workflows import _sources

    return "\n".join(f"  - {name}: " + ", ".join(f"{f} ({d['type']})" for f, d in fields.items())
                     for name, fields in _sources(context, child).items())


def _miscounts(spec: dict, need: str, context, child: bool) -> list[str]:
    """A valid workflow that counts records when the need is about a number they hold ("fewer than 20
    eggs" counts collections, not eggs): sent back once to be fixed."""
    from core.workflows import _flat, _sources

    sources = _sources(context, child)
    reads = {s.get("as"): sources.get(s.get("source"), {}) for s in _flat(spec.get("steps")) if s.get("step") == "read"}
    words = set(re.findall(r"[a-z]+", need.lower()))
    out = []
    for s in _flat(spec.get("steps")):
        if s.get("step") != "count":
            continue
        for name, f in (reads.get(str(s.get("of", "")).partition(".")[0]) or {}).items():
            said = {name, *re.findall(r"[a-z]+", str(f.get("label", "")).lower())}
            if f["type"] in ("number", "money") and words & said:
                base = str(s["of"]).partition(".")[0]
                out.append(f"count of {base} counts its records; to total the {f['label'].lower()}, use "
                           f"\"sum\" of {base}.{name}.")
    return out


def make_workflow(context, need: str, ask: Optional[Callable[[str, dict], str]] = None, child: bool = False) -> dict:
    """A draft workflow for `need` (core/workflows.py, DEC-0092), or MakerError. Changes no data."""
    from core.workflows import check as check_workflow

    store = getattr(context, "creations", None)
    if store is None:
        raise MakerError("Creations aren't available here.")
    ask = ask or _ollama
    again, problems = "", []
    for _attempt in range(2):
        said = ask(WORKFLOW_PROMPT.format(need=need, sources=_workflow_sources(context, child), again=again),
                   WORKFLOW_SCHEMA)
        try:
            design = json.loads(said)
        except ValueError:
            problems, again = ["the design wasn't JSON"], "\nYour last reply wasn't JSON. Reply with JSON only."
            continue
        spec = {"kind": "workflow", "title": str(design.get("title", ""))[:60], "owner": design.get("owner", "personal"),
                "trigger": design.get("trigger") or {}, "steps": design.get("steps") or [],
                **({"limits": design["limits"]} if design.get("limits") else {})}
        problems = check_workflow(spec, context, child=child) or _miscounts(spec, need, context, child)
        if not problems:
            _note(context, "workflow", "first" if _attempt == 0 else "retried", [])
            return store.draft(spec, [], made_by="mia", why=need, blueprint="")
        again = "\nYour last design had these problems; fix them:\n- " + "\n- ".join(problems[:8])
    _note(context, "workflow", "failed", problems)
    raise MakerError("I couldn't make a workflow that passes its checks: " + "; ".join(problems[:4]))


def _note(context, kind: str, outcome: str, problems: list) -> None:
    """For the creations.maker loop: each design, how it went and what its checks said (never the request)."""
    from datetime import datetime

    folder = getattr(getattr(context, "failures", None), "data_dir", None)
    if folder is None:
        return
    try:
        Path(folder).mkdir(parents=True, exist_ok=True)
        with open(Path(folder) / "maker_log.jsonl", "a", encoding="utf-8") as out:
            out.write(json.dumps({"at": datetime.now().isoformat(timespec="seconds"), "kind": kind, "outcome": outcome,
                                  "problems": [str(p)[:120] for p in problems[:4]]}) + "\n")
    except OSError:
        pass


def maker_log(context, days: int = 30) -> list[dict]:
    from datetime import datetime, timedelta

    folder = getattr(getattr(context, "failures", None), "data_dir", None)
    if folder is None:
        return []
    since = (datetime.now() - timedelta(days=days)).isoformat(timespec="seconds")
    try:
        lines = (Path(folder) / "maker_log.jsonl").read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    out = []
    for line in lines:
        try:
            found = json.loads(line)
        except ValueError:
            continue
        if found.get("at", "") >= since:
            out.append(found)
    return out


def make(context, need: str, ask: Optional[Callable[[str, dict], str]] = None, child: bool = False) -> dict:
    """A draft creation for `need`, or MakerError. Changes no data."""
    need = " ".join((need or "").split())
    if len(need) < 8:
        raise MakerError("Tell me a little more about what you want to keep track of.")
    store = getattr(context, "creations", None)
    if store is None:
        raise MakerError("Creations aren't available here.")
    ask = ask or _ollama
    blueprints = bp.load()
    listing = "\n".join(f"  - {b['id']}: {b['purpose']} (fits {b['fits']})" for b in blueprints.values())
    again, problems = "", []
    for _attempt in range(2):
        from core.creation_sources import describe

        from core.creation_sources import SOURCES, matching

        hint = "".join(f"- MIA already keeps {SOURCES[m].title.lower()}: this sounds like source \"{m}\". Use it "
                       "unless they clearly want something new.\n" for m in matching(need, child))
        said = ask(PROMPT.format(need=need, blueprints=listing, blocks=", ".join(BLOCKS), icons=", ".join(ICONS),
                                 sources=describe(child), hint=hint, again=again), DESIGN_SCHEMA)
        try:
            design = json.loads(said)
        except ValueError:
            problems, again = ["the design wasn't JSON"], "\nYour last reply wasn't JSON. Reply with JSON only."
            continue
        spec, blueprint = spec_from(design, blueprints, need)
        problems = check(spec, child=child)
        if not problems:
            _note(context, "screen", "first" if _attempt == 0 else "retried", [])
            return store.draft(spec, [], made_by="mia", why=need, blueprint=blueprint)
        again = "\nYour last design had these problems; fix them:\n- " + "\n- ".join(problems[:8])
    _note(context, "screen", "failed", problems)
    raise MakerError("I couldn't make a screen that passes its checks: " + "; ".join(problems[:4]))
