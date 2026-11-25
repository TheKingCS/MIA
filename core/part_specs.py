"""
core.part_specs
=================

What MIA knows about each electronics part's pins and limits, so his own hardware can be wired in the simulator
(Zac, 2026-11-25: "be able to tell what hardware I have and simulate connecting it. She could fetch the specs online
and import them"). His parts themselves, with how many and where, stay in the Component DB (core/component_manager.py);
a spec is what a part *is*: its pins and their roles, the supply it takes, the level its outputs drive.

- **A spec** (`Spec`, `Pin`): its id and name, a few words of what it is, the supply range (volts), the level its
  outputs drive (`out_volts`: None means its supply), its pins, each with a role, where it came from (`source`:
  built in, or the web pages it was drafted from) and whether he confirmed it. Roles (`ROLES`): power, ground, in (a
  signal into the part), out (a digital signal out of it), analog (a voltage out of it to read), sda and scl (I2C),
  passive (an LED's or resistor's legs, a button's or a pot's).
- **Built in** (`BUILTIN`): the parts the labs and an ELEGOO kit use, from their datasheets: the HC-SR04 (5 V, its
  ECHO at 5 V: too much for a 3.3 V board without a divider), the DHT11 and DHT22, the SG90 servo, a relay module, a
  capacitive soil sensor, the HC-SR501 motion sensor (4.5 to 20 V, its output 3.3 V), the BME280 (1.71 to 3.6 V
  only), and the passive parts.
- **His own** (`SpecBook`): specs added for parts MIA didn't know, kept in data/labs/part_specs.json, each confirmed
  by him (the action `partspec.add`, approved: it comes from outside), removable (`partspec.remove`).
- **From the web** (`draft_from_web`): his own search engine's results for the part (core/online_lookup.py: only the
  part's name leaves the computer), given to the model as web content (core/browser_safety.untrusted), which drafts a
  spec; the draft is checked in code (`clean`: known roles, sane volts, a dozen pins at most) and put to him as an
  approval card with its sources, never kept until he says yes. Tool: `import_part_spec` ("look up the BME280's specs
  and add it"); `part_specs` ("what parts can I wire in the simulator?").
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

from core.actions import ACTION_TYPES, ActionError, ActionType
from core.atomic_write import atomic_write_text
from core.data_root import DATA_DIR
from core.logger import get_logger

log = get_logger(__name__)

ROLES = ("power", "ground", "in", "out", "analog", "sda", "scl", "passive")


@dataclass(frozen=True)
class Pin:
    """One pin of a part: its id ("vcc"), what's printed or said ("VCC"), its role (`ROLES`)."""
    id: str
    name: str
    role: str


@dataclass(frozen=True)
class Spec:
    """One part's spec (see the module's opening)."""
    id: str
    name: str
    about: str
    volts_min: float
    volts_max: float
    pins: tuple
    out_volts: Optional[float] = None
    source: str = "built in"
    confirmed: bool = True

    def pin(self, pin_id: str) -> Optional[Pin]:
        """A pin by its id, or None."""
        return next((p for p in self.pins if p.id == pin_id), None)

    def to_dict(self) -> dict:
        """As saved and as the page reads it."""
        out = asdict(self)
        out["pins"] = [asdict(p) for p in self.pins]
        return out

    @staticmethod
    def from_dict(data: dict) -> "Spec":
        """From its saved dict."""
        return Spec(str(data["id"]), str(data["name"]), str(data.get("about", "")), float(data["volts_min"]),
                    float(data["volts_max"]), tuple(Pin(str(p["id"]), str(p["name"]), str(p["role"]))
                                                    for p in data.get("pins", ())),
                    None if data.get("out_volts") in (None, "") else float(data["out_volts"]),
                    str(data.get("source", "")), bool(data.get("confirmed", True)))


def _spec(id_, name, about, vmin, vmax, pins, out_volts=None) -> Spec:
    """A built-in spec from (id, name, role) triples."""
    return Spec(id_, name, about, vmin, vmax, tuple(Pin(*p) for p in pins), out_volts)


BUILTIN: dict = {s.id: s for s in (
    _spec("hcsr04", "HC-SR04 ultrasonic sensor", "measures distance by echo", 4.5, 5.5,
          (("vcc", "VCC", "power"), ("trig", "TRIG", "in"), ("echo", "ECHO", "out"), ("gnd", "GND", "ground"))),
    _spec("dht11", "DHT11 temperature and humidity", "one-wire temperature and humidity", 3.0, 5.5,
          (("vcc", "VCC (+)", "power"), ("data", "DATA", "out"), ("gnd", "GND (-)", "ground"))),
    _spec("dht22", "DHT22 (AM2302) temperature and humidity", "one-wire temperature and humidity", 3.3, 6.0,
          (("vcc", "VCC (+)", "power"), ("data", "DATA", "out"), ("gnd", "GND (-)", "ground"))),
    _spec("sg90", "SG90 micro servo", "turns to an angle, 0 to 180 degrees", 4.8, 6.0,
          (("gnd", "brown (GND)", "ground"), ("vcc", "red (+)", "power"), ("sig", "orange (signal)", "in"))),
    _spec("relay5v", "1-channel relay module (5 V)", "switches a low-voltage load", 4.5, 5.5,
          (("vcc", "VCC", "power"), ("gnd", "GND", "ground"), ("in", "IN", "in"))),
    _spec("soil_cap", "capacitive soil moisture sensor (v1.2)", "soil moisture as a voltage", 3.3, 5.5,
          (("vcc", "VCC", "power"), ("gnd", "GND", "ground"), ("aout", "AOUT", "analog")), out_volts=3.0),
    _spec("hcsr501", "HC-SR501 PIR motion sensor", "goes high when something warm moves", 4.5, 20.0,
          (("vcc", "VCC", "power"), ("out", "OUT", "out"), ("gnd", "GND", "ground")), out_volts=3.3),
    _spec("bme280", "BME280 temperature, humidity and pressure (bare chip board)", "I2C weather sensor", 1.71, 3.6,
          (("vin", "VIN", "power"), ("gnd", "GND", "ground"), ("scl", "SCL", "scl"), ("sda", "SDA", "sda"))),
    _spec("pot10k", "10k potentiometer", "a knob: a voltage between its ends", 0.0, 50.0,
          (("end1", "outer leg", "passive"), ("wiper", "middle leg (wiper)", "passive"),
           ("end2", "other outer leg", "passive"))),
    _spec("led", "LED", "lights one way only, through a resistor", 0.0, 5.5,
          (("anode", "long leg (+)", "passive"), ("cathode", "short leg (-)", "passive"))),
    _spec("resistor", "resistor", "limits current, or divides a voltage", 0.0, 50.0,
          (("a", "one end", "passive"), ("b", "the other end", "passive"))),
    _spec("button", "push button", "joins its legs while pressed", 0.0, 50.0,
          (("a", "one leg", "passive"), ("b", "the leg across from it", "passive"))),
    _spec("buzzer", "buzzer", "beeps, or plays a tone", 3.0, 5.5,
          (("plus", "+ leg", "in"), ("minus", "- leg", "ground"))),
)}


class SpecBook:
    """His own specs (data/labs/part_specs.json), beside the built-in ones."""

    def __init__(self, context=None, data_dir: Optional[Path] = None):
        """Loads his specs from `data_dir` (data/labs by default)."""
        self.data_dir = Path(data_dir or DATA_DIR / "labs")
        self._file = self.data_dir / "part_specs.json"
        self.specs: dict = {}
        self._load()

    def _load(self) -> None:
        """Reads the file (none yet: no specs of his own)."""
        try:
            raw = json.loads(self._file.read_text(encoding="utf-8")) if self._file.exists() else {}
            self.specs = {d["id"]: Spec.from_dict(d) for d in raw.get("specs", [])}
        except (OSError, ValueError, KeyError, TypeError) as problem:
            log.warning("Couldn't read his part specs: %s", problem)
            self.specs = {}

    def _save(self) -> None:
        """Writes it atomically (so "undo that" can restore it)."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._file, json.dumps({"specs": [s.to_dict() for s in self.specs.values()]}, indent=1,
                                                 ensure_ascii=False))

    def add(self, spec: Spec) -> Spec:
        """Keeps one of his (replacing one with the same id); never over a built-in one."""
        known = builtin_like(spec)
        if known is not None:
            raise ValueError(f"MIA already knows the {known.name}.")
        self.specs[spec.id] = spec
        self._save()
        return spec

    def remove(self, spec_id: str) -> Spec:
        """Takes one of his away. KeyError for one that isn't his."""
        spec = self.specs.pop(spec_id)
        self._save()
        return spec

    def all(self) -> dict:
        """Every spec: the built-in ones, then his."""
        return {**BUILTIN, **self.specs}


def builtin_like(spec: Spec) -> Optional[Spec]:
    """Pure logic. The built-in spec a new one would shadow (the same id or name), or None."""
    name = spec.name.lower()
    return BUILTIN.get(spec.id) or next((b for b in BUILTIN.values() if b.name.lower() == name), None)


def book(context=None) -> SpecBook:
    """His spec book: the context's, else one on the data folder."""
    found = getattr(context, "part_specs", None) if context is not None else None
    return found if found is not None else SpecBook(context)


def slug(name: str) -> str:
    """Pure logic. A spec id from a part's name: "BME280 sensor" -> "bme280_sensor"."""
    return re.sub(r"[^a-z0-9]+", "_", str(name or "").lower()).strip("_")[:40] or "part"


def clean(data: dict, source: str) -> Spec:
    """Pure logic. A drafted spec checked: a name, a supply range between 0 and 60 V with the low end first, two to
    twelve pins with known roles and unique ids, a power and a ground pin. ValueError saying what's wrong.
    A draft that isn't a dict, or pins that aren't, is a ValueError; two pins of one name are numbered (gnd, gnd_2)."""
    if not isinstance(data, dict):
        raise ValueError("The draft isn't a spec.")
    name = " ".join(str(data.get("name", "") or "").split())[:80]
    if not name:
        raise ValueError("The draft has no name.")
    try:
        vmin, vmax = float(data.get("volts_min")), float(data.get("volts_max"))
    except (TypeError, ValueError):
        raise ValueError("The draft doesn't give the supply voltage as numbers.")
    if not (0 <= vmin <= vmax <= 60):
        raise ValueError(f"The supply range {vmin:g} to {vmax:g} V doesn't make sense.")
    out = data.get("out_volts")
    out = None if out in (None, "", "null") else float(out)
    if out is not None and not (0 < out <= 60):
        raise ValueError("The output level doesn't make sense.")
    pins = []
    raw_pins = data.get("pins") or []
    if not isinstance(raw_pins, list) or not all(isinstance(r, dict) for r in raw_pins):
        raise ValueError("The draft's pins aren't a list of pins.")
    for raw in raw_pins[:13]:
        pin_id = slug(raw.get("id") or raw.get("name"))
        n = 2
        while any(p.id == pin_id for p in pins):  # two GND pins on one module: gnd, gnd_2
            pin_id = f"{slug(raw.get('id') or raw.get('name'))}_{n}"
            n += 1
        role = str(raw.get("role", "")).lower().strip()
        if role not in ROLES:
            raise ValueError(f"The pin {raw.get('name')} has a role MIA doesn't know: {role or 'none'}.")
        pins.append(Pin(pin_id, " ".join(str(raw.get("name") or pin_id).split())[:30], role))
    if not 2 <= len(pins) <= 12 or len({p.id for p in pins}) != len(pins):
        raise ValueError("The draft needs two to twelve pins, each named once.")
    if not any(p.role == "power" for p in pins) or not any(p.role == "ground" for p in pins):
        raise ValueError("The draft needs a power pin and a ground pin.")
    return Spec(slug(name), name, " ".join(str(data.get("about", "") or "").split())[:120], vmin, vmax, tuple(pins),
                out, source[:400], confirmed=False)


DRAFT = (
    "From the web search results below, draft the electronics part's spec as JSON only, no other words: "
    "{\"name\": ..., \"about\": a few words, \"volts_min\": the lowest supply voltage, \"volts_max\": the highest, "
    "\"out_volts\": the level its signal outputs drive, or null if it's the supply, \"pins\": [{\"id\": ..., \"name\": "
    "as printed, \"role\": one of power, ground, in, out, analog, sda, scl, passive}]}. Use only numbers the results "
    "give; if they don't give the supply voltage, answer {\"missing\": \"the supply voltage\"}.")


def draft_from_web(context, part: str, search=None, ask=None) -> Spec:
    """A spec for a part drafted from his own search engine's results (see the module's opening), unconfirmed.
    ValueError (or core.online_lookup.LookupUnavailable) saying why there's none."""
    from core import online_lookup
    from core.browser_safety import untrusted

    part = " ".join(str(part or "").split())[:60]
    if not part:
        raise ValueError("Which part?")
    found = (search or online_lookup.search)(context, f"{part} datasheet pinout operating voltage")
    results = found.get("results") or []
    if not results:
        raise ValueError(f"My search found nothing on the {part}.")
    text = "\n\n".join(f"{r.get('title', '')}\n{r.get('url', '')}\n{r.get('content', '')}" for r in results[:6])
    messages = [{"role": "system", "content": DRAFT}, {"role": "user", "content": untrusted(text)}]
    if ask is None:
        llm = getattr(context, "llm", None)
        reply = llm.chat_with_tools(messages, tools=[]) if llm is not None else None
        said = getattr(reply, "content", "") if reply is not None else ""
    else:
        said = ask(messages)
    match = re.search(r"\{.*\}", said or "", re.S)
    try:
        data = json.loads(match.group(0)) if match else {}
    except ValueError:
        data = {}
    if not data or data.get("missing"):
        raise ValueError(f"The search results don't give the {part}'s {data.get('missing') or 'specs'} clearly: "
                         "check its datasheet, then tell me.")
    data.setdefault("name", part)
    sources = "; ".join(r.get("url", "") for r in results[:3] if r.get("url"))
    return clean(data, f"drafted from a web search ({found.get('at', '')[:10]}): {sources}")


def summary(spec: Spec) -> str:
    """Pure logic. A spec in a sentence: its supply, its outputs' level, its pins."""
    level = f", outputs at {spec.out_volts:g} V" if spec.out_volts is not None else ""
    pins = ", ".join(f"{p.name} ({p.role})" for p in spec.pins)
    return f"{spec.name}: {spec.volts_min:g} to {spec.volts_max:g} V{level}; pins {pins}"


# ------------------------------------------------------------------ actions and tools

def _add_describe(context, params) -> str:
    """What partspec.add says: the spec in full and where it came from."""
    try:
        spec = clean(params.get("spec") or {}, str(params.get("source", "")))
    except ValueError as problem:
        raise ActionError(str(problem))
    known = builtin_like(spec)
    if known is not None:
        raise ActionError(f"MIA already knows the {known.name}.")
    return f"Add to the parts MIA can wire: {summary(spec)}. {spec.source}. Check it against the datasheet first"


def _add_execute(context, params) -> str:
    """Does partspec.add: keeps the spec, confirmed by his yes."""
    from dataclasses import replace

    spec = replace(clean(params.get("spec") or {}, str(params.get("source", ""))), confirmed=True)
    book(context).add(spec)
    return f"Added the {spec.name}: you can wire it in the simulator's free build now."


def _remove_describe(context, params) -> str:
    """What partspec.remove says."""
    spec = book(context).specs.get(str(params.get("spec_id", "")))
    if spec is None:
        raise ActionError("That isn't one of the parts you added.")
    return f"Take the {spec.name} off the parts MIA can wire"


def _remove_execute(context, params) -> str:
    """Does partspec.remove."""
    spec = book(context).remove(str(params.get("spec_id", "")))
    return f"Took the {spec.name} off."


ACTIONS = {a.kind: a for a in (
    ActionType("partspec.add", "Add This Part", {"spec": "the drafted spec", "source": "where it came from"},
               _add_describe, _add_execute),
    ActionType("partspec.remove", "Remove This Part", {"spec_id": "one of the parts he added"},
               _remove_describe, _remove_execute),
)}
ACTION_TYPES.update(ACTIONS)


def _import_tool(context, arguments: dict) -> str:
    """Tool import_part_spec: looks the part up online and puts the drafted spec to him as an approval card."""
    from core.online_lookup import LookupUnavailable

    part = str(arguments.get("part", "") or "").strip()
    known = next((s for s in book(context).all().values()
                  if part and (slug(part) == s.id or part.lower() in s.name.lower())), None)
    if known is not None:
        return f"I already know it: {summary(known)}."
    try:
        spec = draft_from_web(context, part)
    except (ValueError, LookupUnavailable) as problem:
        return str(problem)
    actions = getattr(context, "actions", None)
    if actions is None:
        return f"I found: {summary(spec)} ({spec.source}). Add it from the bench page."
    try:
        card = actions.propose(context, "partspec.add", {"spec": spec.to_dict(), "source": spec.source})
    except ActionError as problem:
        return str(problem)
    return f"{card.summary}. It's waiting for your yes: press Approve, or say \"approve it\"."


def _model_at(text: str, model: str) -> Optional[int]:
    """Pure logic. Where a model number stands whole in the text, its parts joined or not ("HC-SR04", "hc sr04",
    "hcsr04"; never inside a longer word), or None."""
    pattern = r"(?<![a-z0-9])" + r"[\s_-]?".join(re.escape(ch) for ch in model) + r"(?![a-z0-9])"
    found = re.search(pattern, text)
    return found.start() if found else None


def named_spec(context, words: str, models_only: bool = False) -> Optional[Spec]:
    """Pure logic, with his specs. The spec his words name, or None: by a model number with a digit in it, standing
    whole ("HC-SR04", "bme280", "1-channel"); or, unless `models_only` (a photo's answer, core/sight.py: "a push mower"
    is no push button), by its whole name or id as words ("the buzzer", "a push button"). When several are named, the
    first in the words ("a DHT11, or possibly a DHT22" is the DHT11: the fifth review)."""
    text = " ".join(str(words or "").lower().split())
    best: Optional[tuple] = None
    for spec in book(context).all().values():
        at = None
        for model in (re.sub(r"[^a-z0-9]+", "", spec.name.lower().split(" ")[0]), re.sub(r"[^a-z0-9]+", "", spec.id)):
            if len(model) >= 4 and re.search(r"\d", model):
                where = _model_at(text, model)
                if where is not None and (at is None or where < at):
                    at = where
        if at is None and not models_only:
            for phrase in (spec.name.lower(), spec.id.replace("_", " ")):
                found = re.search(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", text)
                if found and (at is None or found.start() < at):
                    at = found.start()
        if at is not None and (best is None or at < best[0]):
            best = (at, spec)
    return best[1] if best else None


def _list_tool(context, arguments: dict) -> str:
    """Tool part_specs: a named part's pins and limits ("what's the pinout for the HC-SR04?"), else the parts MIA can
    wire in the simulator; read in code from his words (the model, asked, answered from memory)."""
    named = named_spec(context, str(arguments.get("question", "") or ""))
    if named is not None:
        warn = ""
        if named.out_volts is None and named.volts_min > 3.6 and any(p.role in ("out", "analog") for p in named.pins):
            warn = " Its outputs are at its supply's level, so on a 3.3 V board like the ESP32 they need a divider."
        return f"{summary(named)}.{warn}"
    specs = book(context).all()
    mine = [s.name for s in specs.values() if s.id not in BUILTIN]
    return ("I can wire these in the simulator: " + ", ".join(s.name for s in BUILTIN.values()) + "."
            + (f" And the ones you added: {', '.join(mine)}." if mine else "")
            + " For another part, say \"look up the specs for\" it and I'll draft one for you to check.")


def register_part_spec_tools(registry) -> None:
    """Registers import_part_spec and part_specs, and the bench's designs (core/bench_designs.design_build) and
    saved builds (core/bench_builds.bench_builds)."""
    from core.bench_builds import register_build_tools
    from core.bench_designs import register_design_tools

    register_design_tools(registry)
    register_build_tools(registry)
    _register_specs(registry)


def _register_specs(registry) -> None:
    """Registers import_part_spec and part_specs."""
    from core.assistant_actions import AssistantAction

    registry.register(AssistantAction(
        name="import_part_spec", domain="learning",
        description="Look an electronics part up online and draft its spec (pins, voltages) for him to approve, so "
                    "he can wire it in MIA's simulator: \"look up the specs for a BME280 and add it\".",
        parameters={"type": "object", "properties": {"part": {"type": "string", "description": "the part's name or "
                                                                                             "model number"}},
                    "required": ["part"]},
        handler=_import_tool, trigger_phrases=("look up the specs", "add a part", "import the specs",
                                              "look up the datasheet", "find the specs"),
    ))
    registry.register(AssistantAction(
        name="part_specs", domain="learning",
        description="A part's pins and voltage limits (\"what's the pinout for the HC-SR04?\"), or the electronics "
                    "parts MIA can wire in her simulator, built in and his own.",
        parameters={"type": "object", "properties": {"question": {"type": "string", "description": "his words"}},
                    "required": []}, prompt_arg="question", subjects=("parts", "part", "pinout", "pins", "specs"),
        handler=_list_tool, trigger_phrases=("parts can i wire", "parts do you know", "parts can you simulate",
                                            "pinout for", "pinout of", "pins on the", "specs for the",
                                            "voltage does the"),
    ))
