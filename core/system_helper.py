"""
core.system_helper
====================

MIA's side of the system helper (FW-06, DEC-0194, REQ-AGT-024): the only way she changes the operating system. The
helper itself is os/files/mia-system-helper, `org.mia.System1` on the system bus, with three fixed operations; each
is confirmed twice, first on her approval card (the action kinds here, `act_with_approval`), then by him again in
the operating system's own dialog (polkit, his password), so refusing either changes nothing (acceptance A7).

- `system.restart_service` restarts one of `ALLOWED_UNITS` (the model server, the update stager);
- `system.power` powers off or restarts the computer;
- `system.apply_update` restarts into an update already staged (MIA OS never restarts by itself: Q-114).

`call()` runs `gdbus` with fixed arguments (never a shell), after checking them against the same lists the helper
checks; the helper checks them again, since it trusts no caller. Off MIA OS (on Windows) every kind is Unavailable.
"""

from __future__ import annotations

import subprocess
import sys
from typing import Callable

from core.actions import ACTION_TYPES, ActionError, ActionType, Refused, Unavailable

NAME, PATH = "org.mia.System1", "/org/mia/System1"
ALLOWED_UNITS = {"ollama.service": "the model server", "mia-update-stage.service": "the update stager"}
POWER = {"poweroff": "Power off", "reboot": "Restart"}
WAIT_SECONDS = 330  # the dialog waits for him to type his password


def argv(method: str, *args: str) -> list[str]:
    """Pure logic. The gdbus command for one helper call, its text arguments quoted as D-Bus strings. Only the three
    methods, only their fixed arguments (ValueError otherwise), so nothing he or a model says reaches the command."""
    if method == "RestartUnit" and (len(args) != 1 or args[0] not in ALLOWED_UNITS):
        raise ValueError("not a unit MIA may restart")
    if method == "Power" and (len(args) != 1 or args[0] not in POWER):
        raise ValueError("not poweroff or reboot")
    if method == "ApplyUpdate" and args:
        raise ValueError("ApplyUpdate takes nothing")
    if method not in ("RestartUnit", "Power", "ApplyUpdate"):
        raise ValueError("not one of the helper's operations")
    return ["gdbus", "call", "--system", "--dest", NAME, "--object-path", PATH, "--method", f"{NAME}.{method}",
            "--timeout", str(WAIT_SECONDS), *[f"'{a}'" for a in args]]


def call(method: str, *args: str, run: Callable = subprocess.run) -> str:
    """One helper call: its outcome in words. Unavailable off MIA OS or when the helper can't be reached; Refused when
    the helper or polkit said no (the dialog refused, or no one to ask)."""
    if sys.platform != "linux":
        raise Unavailable("That's done by MIA OS's system helper, on MIA OS.")
    try:
        done = run(argv(method, *args), capture_output=True, text=True, timeout=WAIT_SECONDS + 10)
    except (OSError, subprocess.SubprocessError) as problem:
        raise Unavailable(f"The system helper couldn't be reached: {problem}") from None
    if done.returncode != 0:
        said = (done.stderr or done.stdout or "").strip()
        if "Refused" in said or "NotAuthorized" in said:
            raise Refused("Not done: " + (said.split("Refused:")[-1].strip() or "you didn't confirm it")[:200])
        raise Unavailable(f"The system helper didn't do it: {said[:200]}")
    return done.stdout.strip().strip("(),'\" ") or "done"


def _unit(params) -> str:
    """The unit asked for, checked against the list."""
    unit = str((params or {}).get("unit", "")).strip()
    if unit not in ALLOWED_UNITS:
        raise ActionError("MIA may restart only " + " or ".join(f"{v} ({k})" for k, v in ALLOWED_UNITS.items()) + ".")
    return unit


def _what(params) -> str:
    """Power off or restart, checked."""
    what = str((params or {}).get("what", "")).strip().lower()
    if what not in POWER:
        raise ActionError("Say poweroff or reboot.")
    return what


SYSTEM_ACTIONS: dict[str, ActionType] = {a.kind: a for a in (
    ActionType("system.restart_service", "Restart it", {"unit": "ollama.service or mia-update-stage.service"},
               lambda c, p: f"Restart {ALLOWED_UNITS[_unit(p)]} ({_unit(p)}); the computer then asks for your password",
               lambda c, p: f"Done: {call('RestartUnit', _unit(p))}."),
    ActionType("system.power", "Do it", {"what": "poweroff or reboot"},
               lambda c, p: f"{POWER[_what(p)]} the computer; it then asks for your password",
               lambda c, p: f"{call('Power', _what(p)).capitalize()}."),
    ActionType("system.apply_update", "Restart now", {},
               lambda c, p: "Restart now to finish MIA OS's update (only if one is waiting); the computer then asks "
                            "for your password",
               lambda c, p: f"{call('ApplyUpdate').capitalize()}."),
)}
ACTION_TYPES.update(SYSTEM_ACTIONS)
