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
- blocks (optional): leave it out to use the blueprint. Give your own only if the blueprint wouldn't
  show it well. Blocks are: {blocks}. A value is {{"count": true}} or {{"sum"|"avg"|"min"|"max"|"latest": "field"}}.
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


def spec_from(design: dict, blueprints: dict) -> tuple[dict, str]:
    """Pure logic. A design (the model's reply) -> a spec, and the blueprint it used ("" for her own blocks)."""
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
        said = ask(PROMPT.format(need=need, blueprints=listing, blocks=", ".join(BLOCKS), icons=", ".join(ICONS),
                                 again=again), DESIGN_SCHEMA)
        try:
            design = json.loads(said)
        except ValueError:
            problems, again = ["the design wasn't JSON"], "\nYour last reply wasn't JSON. Reply with JSON only."
            continue
        spec, blueprint = spec_from(design, blueprints)
        problems = check(spec, child=child)
        if not problems:
            return store.draft(spec, [], made_by="mia", why=need, blueprint=blueprint)
        again = "\nYour last design had these problems; fix them:\n- " + "\n- ".join(problems[:8])
    raise MakerError("I couldn't make a screen that passes its checks: " + "; ".join(problems[:4]))
