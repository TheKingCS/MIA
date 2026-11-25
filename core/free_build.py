"""
core.free_build
=================

The free build: his own parts, wired to his board as he likes, checked by what each part's spec says (Zac,
2026-11-25: "tell what hardware I have and simulate connecting it"). Where a lab's circuit is judged against its own
build (core/esp32_sim.py), here there's no build to follow: each part is judged by its spec (core/part_specs.py) and
the board's limits (core/boards.py). Pure logic; nothing kept.

`check(board_id, parts, wires)`: `parts` are his part instances ({id, spec}: "p1" an HC-SR04), `wires` pairs of
terminals ("p1.echo", "D8", "GPIO 21"). The rules, each said with why and what to do:

- **The board**: a supply shorted to GND or to another supply (stop), reset held at GND (stop).
- **Power**: each power pin on a supply (warn when not), within the part's range: over it is a stop (it can be
  damaged), under it a warning (it may not run); VIN on an Arduino counts as up to 12 V (a wall supply), on the ESP32
  as 5 V (USB). A ground pin on GND.
- **Outputs into the board** (out, analog, sda, scl): a part's output drives the level its spec gives, or its own
  supply's; over the board's logic level on a board pin is a stop, with the fix (a divider of 1k and 2k, a level
  shifter, or powering it from 3V3 when its range allows). An analog output on a pin with no ADC, and I2C off the
  board's SDA and SCL pins, are warnings. Two parts' outputs on one net fight (warn).
- **Inputs from the board**: a part's input on an input-only pin can't be driven (warn).
- **An LED**: in a loop from a pin or a supply to GND through a resistor (none: overdriven), never backwards.
- **A pot**: its ends across a supply and GND; its wiper on a pin at that supply's level (5 V into a 3.3 V board:
  stop).

Returns {ok, problems [{level, text}], connections [in words]}.
"""

from __future__ import annotations

from typing import Optional

# The pins that read analog on each board family, and its I2C pins (SDA, SCL).
_ADC = {"esp32": {f"GPIO {n}" for n in (0, 2, 4, 12, 13, 14, 15, 25, 26, 27, 32, 33, 34, 35, 36, 39)},
        "arduino": {f"A{n}" for n in range(8)}}
_I2C = {"esp32": {"sda": ("GPIO 21",), "scl": ("GPIO 22",)},
        "arduino": {"sda": ("A4", "SDA"), "scl": ("A5", "SCL")}}


def _volts(board, rail: str) -> Optional[float]:
    """A supply rail's voltage on this board (VIN: 5 V on the ESP32's USB, up to 12 V on an Arduino's wall supply)."""
    if rail == "VIN":
        return 5.0 if board.family == "esp32" else 12.0
    return {"3V3": 3.3, "5V": 5.0, "GND": 0.0}.get(rail)


def check(board_id: str, parts: list, wires: list, specs: Optional[dict] = None) -> dict:
    """Pure logic. His free build judged (see the module's opening). ValueError for an unknown board, part spec or
    terminal."""
    from core import boards, esp32_sim, part_specs

    board = boards.BOARDS.get(board_id)
    if board is None:
        raise ValueError("Which board? The ESP32, the Mega or a Nano.")
    specs = specs if specs is not None else part_specs.BUILTIN
    known = set(boards.FAMILY_PINS[board.family])
    placed = {}
    for item in parts or ():
        spec = specs.get(str(item.get("spec", "")))
        if spec is None:
            raise ValueError(f"MIA doesn't know the part {item.get('spec')}: add its spec first.")
        placed[str(item["id"])] = spec
        known |= {f"{item['id']}.{p.id}" for p in spec.pins}
    cleaned = []
    for wire in wires or ():
        a, b = (str(x).strip() for x in wire)
        for t in (a, b):
            if t not in known:
                raise ValueError(f"{t} isn't on the board or one of the parts.")
        if a != b:
            cleaned.append((a, b))
    token = esp32_sim._BOARD.set(board)
    try:
        return _judge(board, placed, cleaned)
    finally:
        esp32_sim._BOARD.reset(token)


def _judge(board, placed: dict, wires: list) -> dict:
    """The rules, on the board already set for the nets."""
    from core import esp32_sim

    nets = esp32_sim._Nets(wires)
    problems: list = []

    def say(level: str, text: str) -> None:
        """One problem, once."""
        if not any(p["text"] == text for p in problems):
            problems.append({"level": level, "text": text})

    for supply in board.supplies:
        if nets.same(supply, "GND"):
            say("stop", f"{supply} is wired straight to GND: a short. Pull that wire.")
    for i, a in enumerate(board.supplies):
        for b in board.supplies[i + 1:]:
            if nets.same(a, b):
                say("stop", f"{a} and {b} are joined: two supplies pushing into each other. Pull that wire.")
    reset = "EN" if board.family == "esp32" else "RST"
    if nets.same(reset, "GND"):
        say("stop", f"{reset} to GND holds the board in reset.")
    touched = {t for w in wires for t in w}
    for pin in board.signals:
        if pin in touched and nets.rail(pin) == "VIN":
            say("stop", f"{board.label(pin)} is wired to VIN: over {board.short}'s {board.logic_volts:g} V limit.")

    outputs: dict = {}
    resistors = [pid for pid, s in placed.items() if s.id == "resistor"]
    for pid, spec in placed.items():
        if spec.id == "led":
            _led(nets, pid, resistors, touched, say, board)
            continue
        if spec.id == "pot10k":
            _pot(nets, pid, say, board)
            continue
        power = [p for p in spec.pins if p.role == "power"]
        supply_v = None
        for p in power:
            term = f"{pid}.{p.id}"
            rail = nets.rail(term)
            if rail is None or rail == "GND":
                if term in touched or any(t.startswith(pid + ".") for t in touched):
                    say("warn", f"The {spec.name}'s {p.name} isn't on a supply yet: it has no power.")
                continue
            supply_v = _volts(board, rail)
            if supply_v > spec.volts_max:
                fix = " Use 3V3." if spec.volts_min <= 3.3 <= spec.volts_max else ""
                where = "VIN (up to 12 V from a wall supply)" if rail == "VIN" and board.family != "esp32" else rail
                say("stop", f"The {spec.name} takes {spec.volts_min:g} to {spec.volts_max:g} V; {where} is "
                            f"{supply_v:g} V: it can be damaged.{fix}")
            elif supply_v < spec.volts_min:
                say("warn", f"The {spec.name} needs at least {spec.volts_min:g} V; {rail} gives {supply_v:g} V: it may "
                            "not run.")
        for p in spec.pins:
            term = f"{pid}.{p.id}"
            if p.role == "ground" and nets.rail(term) != "GND" and any(t.startswith(pid + ".") for t in touched):
                say("warn", f"The {spec.name}'s {p.name} isn't on GND: without a shared ground there's no signal.")
            on = nets.pins_on(term)
            if p.role in ("out", "analog", "sda", "scl"):
                level = spec.out_volts if spec.out_volts is not None else supply_v
                if on and level is not None and level > board.logic_volts + 0.3:
                    fix = (" Or power it from 3V3: it runs from " f"{spec.volts_min:g} V."
                           if spec.volts_min <= 3.3 and spec.out_volts is None else "")
                    say("stop", f"The {spec.name}'s {p.name} puts out {level:g} V into {board.label(on[0])}, over "
                                f"{board.short}'s {board.logic_volts:g} V limit: put a divider between (1k from it, 2k "
                                f"to GND) or a level shifter.{fix}")
                for q in on:
                    outputs.setdefault(nets.find(q), []).append(f"the {spec.name}'s {p.name}")
                if p.role == "analog" and on and not set(on) & _ADC[board.family]:
                    say("warn", f"The {spec.name}'s {p.name} is a voltage to read, but {board.label(on[0])} has no "
                                "ADC: use an analog pin.")
                if p.role in ("sda", "scl"):
                    wanted = _I2C[board.family][p.role]
                    if (on or nets.rail(term)) and not any(nets.same(term, w) for w in wanted):
                        say("warn", f"The {spec.name}'s {p.name} goes on {' or '.join(board.label(w) for w in wanted)}"
                                    f", {board.short}'s I2C {p.role.upper()}.")
            if p.role == "in" and on and on[0] in board.input_only:
                say("warn", f"{board.label(on[0])} is input-only: it can't drive the {spec.name}'s {p.name}.")
    for net, names in outputs.items():
        if len(names) > 1:
            say("warn", f"{' and '.join(names)} are joined: two outputs on one wire fight each other.")
    words = [f"{_term_words(t, placed, board)} to {_term_words(u, placed, board)}" for t, u in wires]
    return {"ok": not any(p["level"] in ("stop", "warn") for p in problems), "problems": problems,
            "connections": words}


def page(context, board_id: str = "") -> dict:
    """The bench page's data (web/bench.html): the boards to choose from and the one chosen with its pins drawn, every
    part spec MIA can wire (built in and his), his own parts from the Component DB (name, value, how many), and
    whether a part can be looked up online now (core/online_lookup.allowed) and why not."""
    from core import boards, part_specs
    from core.online_lookup import allowed

    board = boards.BOARDS.get(board_id) or boards.ESP32
    side = lambda pins: [{"id": p, "label": board.label(p)} for p in pins]  # noqa: E731
    store = getattr(context, "components", None)
    mine = [{"name": c.name, "value": c.value, "quantity": c.quantity, "category": c.category}
            for c in (store.all_components() if store is not None else [])]
    ok, why = allowed(context)
    return {"boards": [{"id": b.id, "name": b.name} for b in boards.BOARDS.values()],
            "board": {"id": board.id, "name": board.name, "label": board.short.replace("the ", "").upper(),
                      "left": side(board.left), "right": side(board.right)},
            "specs": [dict(s.to_dict(), builtin=s.id in part_specs.BUILTIN)
                      for s in part_specs.book(context).all().values()],
            "components": mine, "lookup": {"allowed": ok, "why": why}}


def _term_words(terminal: str, placed: dict, board) -> str:
    """A terminal in words: a board pin as printed, a part's pin by its name."""
    if "." not in terminal:
        return board.label(terminal)
    pid, pin = terminal.split(".", 1)
    spec = placed[pid]
    found = spec.pin(pin)
    return f"the {spec.name}'s {found.name if found else pin}"


def _led(nets, pid: str, resistors: list, touched: set, say, board) -> None:
    """An LED: from a pin or a supply to GND through a resistor, the right way round."""
    from core.esp32_sim import _reach

    anode, cathode = f"{pid}.anode", f"{pid}.cathode"
    if not {anode, cathode} & touched:
        return
    to_a, to_c = _reach(nets, anode, resistors), _reach(nets, cathode, resistors)
    ground = nets.find("GND")
    sources = list(board.signals) + list(board.supplies)
    forward = [to_a[nets.find(s)] + to_c[ground] for s in sources if nets.find(s) in to_a and ground in to_c]
    if forward:
        if min(forward) == 0:
            say("warn", "An LED with no resistor in its loop draws far more current than it or the pin should: put a "
                        "220 ohm resistor in series.")
        return
    if any(nets.find(s) in to_c for s in sources) and ground in to_a:
        say("warn", "An LED is in backwards: its long leg (+) goes toward the pin or supply, the short leg to GND.")
        return
    say("note", "An LED isn't in a loop from a pin to GND yet.")


def _pot(nets, pid: str, say, board) -> None:
    """A pot: ends across a supply and GND, its wiper at that supply's level on a pin."""
    ends = [nets.rail(f"{pid}.end1"), nets.rail(f"{pid}.end2")]
    supply = next((e for e in ends if e and e != "GND"), None)
    wiper = nets.pins_on(f"{pid}.wiper")
    if supply and "GND" in ends and wiper:
        level = _volts(board, supply)
        if level > board.logic_volts + 0.3:
            say("stop", f"The pot is across {supply}: turned up, its wiper puts {level:g} V into "
                        f"{board.label(wiper[0])}, over {board.short}'s {board.logic_volts:g} V limit. Use "
                        f"{board.logic_rail}.")
        elif not set(wiper) & _ADC[board.family]:
            say("warn", f"The pot's wiper is on {board.label(wiper[0])}, which has no ADC: use an analog pin.")
