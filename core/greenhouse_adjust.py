"""
core.greenhouse_adjust
========================

MIA adjusting the greenhouse's targets (DEC-0185; Zac, 2026-11-16: "MIA absolutely should be able to adjust
greenhouse controllers"; homestead/docs/MIA_COMMAND_INTERFACE.md step 4, MIA's side). Targets only: the pH and EC
bands, and the air's temperature band (°F) and humidity limit, as the node lists them in its command limits. Never a dose, a pump, a valve or the safety MCU: those aren't things
she can ask the node for at all, and the node checks everything again itself.

**Asking** (`parse`, `plan`, `reply`): "set the greenhouse pH minimum to 6.4" (or "EC max to 1600", "lower the pH
ceiling to 7.0") reads the node fresh (core/greenhouse_link.fetch), takes the cell's current value from its export
(`mia_directions.targets`), checks the value against the shipped limits (homestead/config/command_limits.default.yaml,
so a plain mistake is said at once; the node's own copy is what counts), says exactly what she'll send, and waits for
"yes, set it". The tool `adjust_greenhouse` does the same; the Greenhouse page's control is the action
`greenhouse.adjust`, approved on its card. A change of the greenhouse is never made on the model's word alone.

**Where it sits** (`against_targets`): "how's the greenhouse pH against its target?" reads the node and says each
cell's latest pH and EC against the band it reports: inside, or below or above by how much, a stale reading said so.

**Sending** (`send`): one direction, signed with this node's key (`sign`, the same HMAC-SHA256 the node checks in
homestead/core/command_auth.py; the key made for this node at provisioning, core/greenhouse_provision.command_key_path;
none yet means nothing is sent), to the node's `POST /mia/command`, only on his own network (greenhouse_link.own_node).
Then the node's export is read again and the change is said as what it became there: applied, waiting for his
Approve on the node's dashboard (the node's default until WAITING_ON 0zu), or refused with why. Nothing local
changes, so there's no Undo here: setting it back is another adjustment (the node allows one change an hour per
target), and a change still waiting can be denied on the node.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
import time
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import urlparse

from core.actions import ACTION_TYPES, ActionError, ActionType
from core.assistant_actions import AssistantAction
from core.logger import get_logger

log = get_logger(__name__)

ROOT = Path(__file__).resolve().parent.parent
LIMITS = ROOT / "homestead" / "config" / "command_limits.default.yaml"
COMMAND_PATH = "/mia/command"
# What he says -> the node's parameter.
_WHICH = re.compile(r"\b(ph|ec|(?:air )?temp(?:erature)?|heat(?:ing)?)\b[\s\w]*?\b(min(?:imum)?|low(?:er (?:end|limit|"
                    r"bound))?|floor|bottom|max(?:imum)?|high(?:er (?:end|limit|bound))?|ceiling|top)\b")
_HUMID = re.compile(r"\bhumidity\b")
_THING = r"(?:ph|ec|temp(?:erature)?|heat(?:ing)?|humidity)"
_ASK = re.compile(rf"\b(?:set|change|raise|lower|move|put|make|adjust)\b.*\bgreenhouse\b.*\b{_THING}\b|"
                  rf"\b(?:set|change|raise|lower|move|put|make|adjust)\b.*\b{_THING}\b.*\bgreenhouse\b")
_TO = re.compile(r"\bto\s+(\d+(?:\.\d+)?)\b")
_YES = re.compile(r"^\s*yes,? set it[.!]*\s*$")
WORDS = {"ph_target_min": "pH minimum", "ph_target_max": "pH maximum", "ec_target_min": "EC minimum",
         "ec_target_max": "EC maximum", "temp_min": "air temperature minimum",
         "temp_max": "air temperature maximum", "humidity_max": "humidity maximum"}
UNITS = {"ec_target_min": " uS/cm", "ec_target_max": " uS/cm", "temp_min": " °F", "temp_max": " °F",
         "humidity_max": "%"}


def _v(param: str, value: float) -> str:
    """Pure logic. A value with its unit: "80 °F", "70%", "6.4"."""
    return f"{value:g}{UNITS.get(param, '')}"


def parse(text: str) -> Optional[tuple[str, float]]:
    """Pure logic. (parameter, value) from "set the greenhouse pH minimum to 6.4", "the greenhouse air temperature
    maximum to 82" or "the greenhouse humidity to 70", or None when it isn't one."""
    said = (text or "").lower()
    if not _ASK.search(said):
        return None
    to = _TO.search(said)
    if to is None:
        return None
    if _HUMID.search(said):  # one limit only: venting above it
        return "humidity_max", float(to.group(1))
    which = _WHICH.search(said)
    if which is None:
        return None
    end = "min" if which.group(2).startswith(("min", "low", "floor", "bottom")) else "max"
    what = which.group(1)
    if what in ("ph", "ec"):
        return f"{what}_target_{end}", float(to.group(1))
    return f"temp_{end}", float(to.group(1))


_LIMIT_LINE = re.compile(r"^\s+(\w+):\s*\{[^}]*?\blow:\s*(-?[\d.]+)[^}]*?\bhigh:\s*(-?[\d.]+)", re.M)


def shipped_limits(path: Path = LIMITS) -> dict:
    """The shipped limits ({param: {low, high}}), read from their one-line entries (MIA has no YAML library; the
    node, which does, is what counts), for saying a plain mistake at once; {} when unreadable."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    return {m.group(1): {"low": float(m.group(2)), "high": float(m.group(3))} for m in _LIMIT_LINE.finditer(text)}


def sign(key: bytes, timestamp: str, nonce: str, body: bytes) -> str:
    """The node's signature (homestead/core/command_auth.sign): HMAC-SHA256, hex, over timestamp, nonce and body."""
    return hmac.new(key, f"{timestamp}\n{nonce}\n".encode() + body, hashlib.sha256).hexdigest()


def _link(context):
    """The greenhouse link, or ActionError."""
    link = getattr(context, "greenhouse_link", None)
    if link is None or not link.url:
        raise ActionError("I don't have the greenhouse node's address. Say \"take over the greenhouse at <address>\" "
                          "first.")
    return link


def plan(context, param: str, value, cell: str = "", get: Optional[Callable] = None) -> dict:
    """What would be sent, read fresh from the node: {param, value, cell_id, cell, current}; ActionError when it
    can't be (no node, not a target she may set, outside the shipped limits, no such cell, the node unreadable).
    A value outside the shipped limits is said with its unit."""
    from core.greenhouse_link import LinkError, fetch

    if param not in WORDS:
        raise ActionError("I can only set the greenhouse's pH or EC minimum or maximum.")
    try:
        value = float(value)
    except (TypeError, ValueError):
        raise ActionError("To what value?") from None
    limits = shipped_limits().get(param)
    if limits and not (limits["low"] <= value <= limits["high"]):
        raise ActionError(f"The node won't take a {WORDS[param]} of {_v(param, value)}: its limits are "
                          f"{_v(param, limits['low'])} to {_v(param, limits['high'])}.")
    link = _link(context)
    try:
        state = fetch(context, link, get=get)
    except LinkError as problem:
        raise ActionError(str(problem)) from None
    targets = ((state.get("mia_directions") or {}).get("targets") or {})
    names = {str(c.get("id")): c.get("name", "") for c in state.get("cells") or []}
    if not targets:
        raise ActionError("The node doesn't report its targets yet: it needs the latest MIA Homestead.")
    wanted = str(cell or "").strip().lower()
    ids = [i for i in targets if not wanted or wanted in str(names.get(i, "")).lower() or wanted == i]
    if len(ids) != 1:
        raise ActionError("Which cell? " + ", ".join(names.get(i) or f"cell {i}" for i in targets) + ".")
    current = targets[ids[0]].get(param)
    if current is None:
        raise ActionError(f"The node doesn't have a {WORDS[param]} set for that cell.")
    return {"param": param, "value": value, "cell_id": int(ids[0]), "cell": names.get(ids[0]) or f"cell {ids[0]}",
            "current": float(current)}


def say_plan(p: dict) -> str:
    """Pure logic. The sentence he approves, each value with its unit (`_v`)."""
    return (f"Set the greenhouse's {WORDS[p['param']]} on {p['cell']} from {_v(p['param'], p['current'])} to "
            f"{_v(p['param'], p['value'])}. The node checks it against its own limits, and applies it or holds it for "
            "your Approve on its dashboard.")


def _post(url: str, body: bytes, headers: dict) -> tuple[int, dict]:
    """POSTs a signed direction; (status, the node's answer)."""
    import urllib.error
    import urllib.request

    request = urllib.request.Request(url, data=body, method="POST",
                                     headers={"Content-Type": "application/json", "User-Agent": "MIA", **headers})
    try:
        with urllib.request.urlopen(request, timeout=15) as answer:
            return answer.status, json.loads(answer.read() or b"{}")
    except urllib.error.HTTPError as problem:
        try:
            return problem.code, json.loads(problem.read() or b"{}")
        except ValueError:
            return problem.code, {}


def send(context, p: dict, approved_by: str = "", post: Optional[Callable] = None,
         get: Optional[Callable] = None) -> str:
    """Sends one planned direction to the node, signed with its key, then reads the node again and says what it
    became there. ActionError when it can't be sent (no key for this node, not on his network, no answer).
    Values are said with their units (`_v`)."""
    from datetime import datetime

    from core.greenhouse_link import LinkError, fetch, own_node
    from core.greenhouse_provision import command_key_path

    link = _link(context)
    if not own_node(link.url):
        raise ActionError("I only talk to the greenhouse on your own network or Tailscale.")
    host = urlparse(link.url).hostname or ""
    try:
        key = bytes.fromhex(command_key_path(host).read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        raise ActionError("The node hasn't been given its key for my directions yet: say \"push the greenhouse to "
                          f"{host}\" (it's sent at the end).") from None
    body = json.dumps({"cell_id": p["cell_id"], "param_name": p["param"], "value": p["value"],
                       "believed_current": p["current"], "approved_by": approved_by or "the owner",
                       "approved_at": datetime.utcnow().isoformat(timespec="seconds")}).encode("utf-8")
    stamp, nonce = str(int(time.time())), secrets.token_hex(16)
    try:
        status, answer = (post or _post)(link.url.rstrip("/") + COMMAND_PATH, body,
                                         {"X-MIA-Timestamp": stamp, "X-MIA-Nonce": nonce,
                                          "X-MIA-Signature": sign(key, stamp, nonce, body)})
    except OSError as problem:
        raise ActionError(f"The greenhouse didn't answer ({type(problem).__name__}).") from None
    if status == 401:
        raise ActionError("The node refused my signature: its key and mine don't match, or its clock is off. "
                          "Pushing the greenhouse again sends the key.")
    if status != 200:
        raise ActionError(f"The node couldn't take it ({status}).")
    what = f"the {WORDS[p['param']]} on {p['cell']} to {_v(p['param'], p['value'])}"
    if answer.get("state") == "refused":
        return f"The node refused {what}: {answer.get('reason', 'no reason given')}."
    try:  # what it became there, from the node's own export
        state = fetch(context, link, get=get)
        row = next((r for r in (state.get("mia_directions") or {}).get("recent", [])
                    if r.get("id") == answer.get("command_id")), None)
    except LinkError:
        row = None
    outcome = (row or {}).get("outcome") or answer.get("state")
    if outcome == "applied":
        return (f"Done: the node applied {what} (it was {_v(p['param'], p['current'])}). To set it back, ask me; it "
                "allows one change an hour.")
    return (f"Sent {what}. The node is holding it for your Approve on its dashboard (and Deny works there too); "
            "I'll see when it's applied.")


_AGAINST = re.compile(r"\b(?:ph|ec)\b.*\b(?:against|vs\.?|versus|compared to|within|inside|in)\b.*\b(?:targets?|"
                      r"range|band)\b|\b(?:is|are)\b.*\b(?:ph|ec)\b.*\b(?:on target|in range|where it should be)\b")


def against_targets(state: dict) -> list[str]:
    """Pure logic. Each cell's latest pH and EC said against the targets the node reports (mia_directions.targets):
    inside, below or above, by how much, and a stale reading said as stale. [] when the node reports no targets."""
    targets = ((state or {}).get("mia_directions") or {}).get("targets") or {}
    lines = []
    for cell in (state or {}).get("cells") or []:
        band = targets.get(str(cell.get("id"))) or {}
        if not band:
            continue
        for kind, label, unit in (("ph", "pH", ""), ("ec", "EC", " uS/cm")):
            low, high = band.get(f"{kind}_target_min"), band.get(f"{kind}_target_max")
            reading = next((r for r in cell.get("readings") or [] if r.get("type") == kind), None)
            if reading is None or reading.get("value") is None or low is None or high is None:
                continue
            value = float(reading["value"])
            where = (f"below its {low:g}{unit} minimum by {low - value:.2g}{unit}" if value < low else
                     f"above its {high:g}{unit} maximum by {value - high:.2g}{unit}" if value > high else
                     f"inside its {low:g}-{high:g}{unit} band")
            stale = " (that reading is stale)" if reading.get("is_stale") else ""
            lines.append(f"{cell.get('name') or 'A cell'}'s {label} is {value:g}{unit}, {where}{stale}.")
    return lines


def node_card(context) -> dict:
    """The Greenhouse page's node card, from the node's last read (no network on a page load): {linked, cells
    [{id, name, targets {param: value}}], recent [{param, value, outcome, reason}], params {param: words}}."""
    link = getattr(context, "greenhouse_link", None)
    state = getattr(link, "state", None) or {}
    directions = state.get("mia_directions") or {}
    names = {str(c.get("id")): c.get("name", "") for c in state.get("cells") or []}
    return {"linked": bool(link is not None and link.url and directions.get("targets")),
            "cells": [{"id": i, "name": names.get(i) or f"cell {i}", "targets": t}
                      for i, t in (directions.get("targets") or {}).items()],
            "recent": [{"param": WORDS.get(r.get("param_name"), r.get("param_name")), "value": r.get("value"),
                        "outcome": r.get("outcome", ""), "reason": r.get("reason", "") if r.get("outcome") == "refused"
                        else "", "when": str(r.get("received_at", ""))[:16]}
                       for r in (directions.get("recent") or [])[:5]],
            "params": WORDS}


# ------------------------------------------------------------------ the action, the words, the tool

def _describe(context, params) -> str:
    """greenhouse.adjust's card: the exact change, read fresh from the node (its refusals said here)."""
    return say_plan(plan(context, params.get("param"), params.get("value"), params.get("cell", "")))


def _execute(context, params) -> str:
    """greenhouse.adjust approved: sent, and what it became."""
    from core.person_settings import person_id

    p = plan(context, params.get("param"), params.get("value"), params.get("cell", ""))
    return send(context, p, approved_by=f"profile {person_id(context) or 'owner'}")


ADJUST_ACTIONS = {k.kind: k for k in (
    ActionType("greenhouse.adjust", "Set Target", {"param": "ph_target_min, ph_target_max, ec_target_min or "
                                                   "ec_target_max", "value": "the new value", "cell": "which cell "
                                                   "(optional with one)"}, _describe, _execute),
)}
ACTION_TYPES.update(ADJUST_ACTIONS)


def reply(context, text: str, post: Optional[Callable] = None, get: Optional[Callable] = None) -> Optional[str]:
    """In code, before the model: "set the greenhouse pH minimum to 6.4" says the exact change and waits; "yes, set
    it" sends it; "how's the greenhouse pH against its target?" reads the node and says each cell's pH and EC against
    its band (`against_targets`, read only). None when the words aren't for it."""
    link = getattr(context, "greenhouse_link", None)
    if link is None:
        return None
    low = (text or "").strip().lower()
    if "greenhouse" in low and _AGAINST.search(low):  # "how's the greenhouse pH against its target?": read only
        from core.greenhouse_link import LinkError, fetch

        try:
            state = fetch(context, link, get=get) if link.url else link.state
        except LinkError as problem:
            return str(problem)
        lines = against_targets(state)
        return " ".join(lines) if lines else ("The node doesn't report its targets yet, so I can't say where its "
                                              "readings sit against them.")
    pending = getattr(link, "pending", {}) or {}
    if pending.get("kind") == "adjust" and _YES.match(low):
        link.pending = {}
        try:
            return send(context, pending["plan"], approved_by="the owner, by voice", post=post, get=get)
        except ActionError as problem:
            return str(problem)
    asked = parse(low)
    if asked is None:
        return None
    try:
        p = plan(context, asked[0], asked[1], get=get)
    except ActionError as problem:
        return str(problem)
    link.pending = {"kind": "adjust", "plan": p}
    return say_plan(p) + " Say \"yes, set it\" to send it."


def _tool(context, arguments: dict) -> str:
    """Tool adjust_greenhouse: says the exact change and waits for "yes, set it" (never sends on its own)."""
    link = getattr(context, "greenhouse_link", None)
    try:
        p = plan(context, str(arguments.get("param", "")), arguments.get("value"), str(arguments.get("cell", "")))
    except ActionError as problem:
        return str(problem)
    link.pending = {"kind": "adjust", "plan": p}
    return say_plan(p) + " Say \"yes, set it\" to send it."


def register_greenhouse_adjust_actions(registry) -> None:
    """Registers adjust_greenhouse."""
    registry.register(AssistantAction(
        name="adjust_greenhouse", domain="development",
        description="Change one of the greenhouse node's targets: its pH or EC minimum or maximum (never a dose or a "
                    "pump). Says the exact change and waits for his \"yes, set it\"; the node checks it again.",
        parameters={"type": "object", "properties": {
            "param": {"type": "string", "description": "ph_target_min, ph_target_max, ec_target_min or ec_target_max"},
            "value": {"type": "number", "description": "the new value"},
            "cell": {"type": "string", "description": "which cell, only if there's more than one"}},
            "required": ["param", "value"]},
        handler=_tool, trigger_phrases=("greenhouse ph", "greenhouse ec", "greenhouse target", "greenhouse's ph",
                                        "greenhouse's ec"),
    ))
