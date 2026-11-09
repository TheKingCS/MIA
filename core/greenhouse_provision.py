"""
core.greenhouse_provision
===========================

Setting up the greenhouse's hardware from MIA (DEC-0150; Zac, 2026-11-08: "MIA needs to be able to flash/program the
pi and other components and help me set them up when it comes time. Maybe have like preloaded configs set up and all
internal info able to be pushed by MIA").

- **The safety MCU** (`flash_mcu`): MIA Homestead's ESP32 firmware (`homestead/firmware/safety_mcu`, PlatformIO) built
  and uploaded from this PC over USB. MIA finds the board's port (`serial_ports`, `likely_mcu`), says exactly what
  she'll run, and does it only on the person's yes. The firmware's own first test comes first: LEDs in place of relays
  (its README), the hold point in the controls job (core/trade_jobs.py).
- **The Pi** (`prepare_pi`): an SSH key made for the node (`data/.keys/`, the private half never leaves this PC),
  preloaded config files written from the node's own templates (`homestead/config/`) with what MIA knows filled in,
  and the Raspberry Pi Imager steps (the OS, the hostname, the user, the key; the Wi-Fi password is typed into Imager
  by the person, never by MIA), all in `data/provisioning/greenhouse/` (device-level, gitignored: it holds a place
  and contacts).
- **Pushing it** (`push_node`): the node's code and the preloaded configs copied to the Pi over SSH with that key,
  then its own install steps run there (a Python environment, the schema, the service with its rollback,
  homestead/deploy/README.md). Only on the person's yes. Secrets stay out: the SMTP app password is left for the
  person to add on the node.

Every command goes through a `run` that tests replace, with no window on Windows. Nothing here sends the node a
control command: the node and its safety MCU act (DEC-0150 answer 4).
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Callable, Optional

from core.logger import get_logger

log = get_logger(__name__)

ROOT = Path(__file__).resolve().parent.parent
NODE = ROOT / "homestead"
FIRMWARE = NODE / "firmware" / "safety_mcu"
BUNDLE = ROOT / "data" / "provisioning" / "greenhouse"
KEY = ROOT / "data" / ".keys" / "greenhouse_node_ed25519"
HOSTNAME = "mia-greenhouse"
REMOTE_DIR = "~/mia-homestead"
FLASH_TIMEOUT = 900
# USB-serial chips ESP32 boards use (vendor:product): CP210x, CH340, CH9102, the ESP32-S3's own USB
ESP32_USB = {(0x10C4, 0xEA60), (0x1A86, 0x7523), (0x1A86, 0x55D4), (0x303A, 0x1001)}
_EXCLUDE = (".venv", "__pycache__", "mia_homestead.db", "*.db-wal", "*.db-shm", "viewer/*_state.json",
            "viewer/home_snapshot.json", "viewer/state.json")


def _run(cmd: list, timeout: int = 120) -> tuple[int, str]:
    """Runs a command with no window and a timeout; (exit code, the tail of what it printed)."""
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.SubprocessError) as problem:
        return 1, str(problem)
    return out.returncode, ((out.stdout or "") + (out.stderr or ""))[-1500:]


# ------------------------------------------------------------------ the safety MCU

def serial_ports() -> list[dict]:
    """The serial ports on this PC: {device, description, vid, pid}; [] without pyserial."""
    try:
        from serial.tools import list_ports
    except ImportError:
        return []
    return [{"device": p.device, "description": p.description or "", "vid": p.vid, "pid": p.pid}
            for p in list_ports.comports()]


def likely_mcu(ports: list[dict]) -> Optional[dict]:
    """Pure logic. The port that's most likely an ESP32 board (its USB chip), or the only port there is; None."""
    found = [p for p in ports if (p.get("vid"), p.get("pid")) in ESP32_USB]
    if found:
        return found[0]
    return ports[0] if len(ports) == 1 else None


def platformio() -> Optional[list]:
    """How to run PlatformIO here (pio on the PATH, or as a Python module), or None when it isn't installed."""
    exe = shutil.which("pio") or shutil.which("platformio")
    if exe:
        return [exe]
    try:
        import platformio  # noqa: F401
    except ImportError:
        return None
    import sys

    return [sys.executable, "-m", "platformio"]


def flash_command(pio: list, port: str, firmware: Path = FIRMWARE) -> list:
    """Pure logic. The command that builds the safety MCU's firmware and uploads it to the board on `port`."""
    return list(pio) + ["run", "-t", "upload", "-d", str(firmware), "--upload-port", port]


def flash_plan(ports: Optional[list] = None, pio: Optional[list] = None) -> dict:
    """What flashing would do now: {ok, port, command, said}; said explains what's missing when it can't."""
    ports = serial_ports() if ports is None else ports
    pio = platformio() if pio is None else pio
    board = likely_mcu(ports)
    if not pio:
        return {"ok": False, "said": "PlatformIO isn't installed here: `pip install platformio` (or the VS Code "
                                     "extension), then ask again."}
    if board is None:
        listed = ", ".join(p["device"] for p in ports) or "none"
        return {"ok": False, "said": f"I can't tell which port is the ESP32 (ports: {listed}). Plug it in by USB, "
                                     "or tell me its port, like COM5."}
    cmd = flash_command(pio, board["device"])
    return {"ok": True, "port": board["device"], "command": cmd,
            "said": f"I'll build the safety MCU's firmware and upload it to the board on {board['device']} "
                    f"({board['description'] or 'a USB serial board'}). Wire LEDs in place of the relays first, as "
                    "its README says. Say “yes, flash it” to go ahead."}


def flash_mcu(port: str, run: Optional[Callable] = None, pio: Optional[list] = None) -> str:
    """Builds and uploads the firmware to the board on `port`; says how it went."""
    pio = platformio() if pio is None else pio
    if not pio:
        return "PlatformIO isn't installed here."
    code, said = (run or _run)(flash_command(pio, port), FLASH_TIMEOUT)
    if code != 0:
        return f"The flash didn't finish (exit {code}). The last of what it said: {said[-400:]}"
    return (f"Flashed the safety MCU on {port}. Next, its LED test: run the node in simulation and watch it announce, "
            "pair, pulse and fall back (the controls job's first hold point).")


# ------------------------------------------------------------------ the Pi

def node_key(run: Optional[Callable] = None, key: Path = KEY) -> str:
    """The public half of the node's SSH key, made once (ed25519, no passphrase, the private half kept in
    data/.keys/); "" when ssh-keygen isn't here."""
    pub = key.with_name(key.name + ".pub")
    if not pub.exists():
        key.parent.mkdir(parents=True, exist_ok=True)
        code, _said = (run or _run)(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "mia-greenhouse",
                                     "-f", str(key)], 60)
        if code != 0 or not pub.exists():
            return ""
    return pub.read_text(encoding="utf-8").strip()


def _yaml_value(value) -> str:
    """Pure logic. A value as YAML's plain scalar: null, a number, or a quoted string."""
    if value is None or value == "":
        return "null" if value is None else '""'
    if isinstance(value, (int, float)):
        return repr(value)
    return json.dumps(str(value))


def filled(template: str, values: dict) -> str:
    """Pure logic. A node config template with the given top-level keys set (`key: value` lines), every comment and
    every other line kept as the node wrote it."""
    out = []
    for line in template.splitlines():
        m = re.match(r"^(\w+):(\s*)([^#\n]*?)(\s*#.*)?$", line)
        if m and m.group(1) in values:
            comment = m.group(4) or ""
            out.append(f"{m.group(1)}: {_yaml_value(values[m.group(1)])}{comment}")
        else:
            out.append(line)
    return "\n".join(out) + "\n"


def prepare_pi(answers: dict, run: Optional[Callable] = None, node: Path = NODE, bundle: Path = BUNDLE) -> dict:
    """The Pi's preloaded configs and its setup steps, in data/provisioning/greenhouse/: location (latitude,
    longitude), notifications (contacts; the SMTP password left for the person), and the sync left to MIA's fetching.
    Returns {folder, files, key, steps}."""
    configs = bundle / "config"
    configs.mkdir(parents=True, exist_ok=True)
    plan = {
        "location.yaml": {k: answers.get(k) for k in ("latitude", "longitude") if k in answers},
        "notifications.yaml": {k: answers.get(k) for k in ("smtp_host", "smtp_user", "from_address",
                                                            "primary_contact_email", "secondary_contact_email")
                               if answers.get(k)},
        "mia_home_sync.yaml": {"destination": None},  # MIA fetches from the node's export server instead (answer 3b)
    }
    files = []
    for name, values in plan.items():
        try:
            template = (node / "config" / name).read_text(encoding="utf-8")
        except OSError:
            continue
        (configs / name).write_text(filled(template, values), encoding="utf-8")
        files.append(name)
    public = node_key(run)
    steps = [
        "In Raspberry Pi Imager: choose Raspberry Pi OS Lite (64-bit) and the SD card.",
        f"Edit settings: hostname {HOSTNAME}, a username of your choice, and your Wi-Fi (you type its password "
        "there, never MIA).",
        "Services: enable SSH with public-key authentication only, and paste MIA's key "
        f"({KEY.name}.pub in data/.keys/).",
        "Write the card, put it in the Pi, power it on, and wait two minutes.",
        f"Tell MIA “push the greenhouse to {HOSTNAME}” (or its address): she copies the node and these configs and "
        "installs its service.",
        "On the node, add the SMTP app password to config/notifications.yaml yourself (MIA never writes it).",
    ]
    (bundle / "PI_SETUP.md").write_text("# The greenhouse Pi\n\n" + "\n".join(f"{n}. {s}" for n, s in
                                                                         enumerate(steps, 1)) + "\n", encoding="utf-8")
    return {"folder": str(bundle), "files": files, "key": public, "steps": steps}


def push_commands(host: str, user: str, archive: Path, key: Path = KEY, bundle: Path = BUNDLE) -> list[list]:
    """Pure logic. The commands that copy the node and its preloaded configs to the Pi and install it there."""
    target = f"{user}@{host}"
    ssh = ["ssh", "-i", str(key), "-o", "StrictHostKeyChecking=accept-new", target]
    install = (f"mkdir -p {REMOTE_DIR} && tar -xzf ~/mia-homestead.tgz -C {REMOTE_DIR} && cd {REMOTE_DIR} && "
               "cp -f ~/mia-provision/*.yaml config/ && python3 -m venv .venv && .venv/bin/pip install -q -r "
               "requirements.txt && .venv/bin/python -c \"import sqlite3; sqlite3.connect('mia_homestead.db')"
               ".executescript(open('schema/mia_homestead_schema.sql').read())\" && bash deploy/install_service.sh")
    return [
        ["tar", "-czf", str(archive)] + [f"--exclude={x}" for x in _EXCLUDE] + ["-C", str(NODE), "."],
        ["scp", "-i", str(key), "-o", "StrictHostKeyChecking=accept-new", str(archive), f"{target}:~/mia-homestead.tgz"],
        ssh + ["mkdir -p ~/mia-provision"],
        ["scp", "-i", str(key), "-o", "StrictHostKeyChecking=accept-new"]
        + [str(p) for p in sorted((bundle / "config").glob("*.yaml"))] + [f"{target}:~/mia-provision/"],
        ssh + [install],
    ]


def push_node(host: str, user: str, run: Optional[Callable] = None) -> str:
    """Copies the node and its preloaded configs to the Pi and installs it; stops at the first step that fails and
    says which."""
    if not KEY.exists():
        return "There's no key for the node yet: ask me to prepare the Pi first."
    archive = BUNDLE / "mia-homestead.tgz"
    BUNDLE.mkdir(parents=True, exist_ok=True)
    names = ("packing the node", "copying it to the Pi", "making the config folder", "copying the configs",
             "installing it")
    for name, cmd in zip(names, push_commands(host, user, archive)):
        code, said = (run or _run)(cmd, 900)
        if code != 0:
            return f"Stopped at {name} (exit {code}): {said[-300:]}"
    return (f"The greenhouse node is on {host} with its configs, and its service is installed. Start it there "
            "(systemctl --user start mia-homestead.service), then its export server, and tell me “take over the "
            f"greenhouse at {host}”.")


# ------------------------------------------------------------------ talking about it

_FLASH = re.compile(r"\b(?:flash|program|upload (?:to|the firmware))\b.*\b(?:mcu|esp32|safety|firmware|board)\b")
_PREP = re.compile(r"\b(?:prepare|set up|setup|provision)\b.*\b(?:the )?(?:pi|raspberry pi|greenhouse node)\b")
_PUSH = re.compile(r"\bpush (?:the )?greenhouse to\s+([\w.\-]+)")
_YES_FLASH = re.compile(r"^\s*yes,? (?:flash|do) it[.!]*\s*$")
_YES_PUSH = re.compile(r"^\s*yes,? push it[.!]*\s*$")
_PORT = re.compile(r"\b(COM\d+|/dev/tty\w+)\b", re.I)


def reply(context, text: str, run: Optional[Callable] = None) -> Optional[str]:
    """What MIA says, in code, to setting up the greenhouse's hardware: "flash the safety MCU" (the plan, then
    "yes, flash it"), "prepare the Pi" (the configs and the Imager steps), "push the greenhouse to <host>" (then "yes,
    push it"); None otherwise. Each device step waits for its yes."""
    link = getattr(context, "greenhouse_link", None)
    if link is None:
        return None
    said = (text or "").strip()
    low = said.lower()
    pending = getattr(link, "pending", None) or {}
    if pending.get("kind") == "flash" and _YES_FLASH.match(low):
        link.pending = {}
        return flash_mcu(pending["port"], run)
    if pending.get("kind") == "push" and _YES_PUSH.match(low):
        link.pending = {}
        return push_node(pending["host"], pending["user"], run)
    if _FLASH.search(low):
        port = _PORT.search(said)
        plan = flash_plan([{"device": port.group(1), "description": "the port you named", "vid": None,
                            "pid": None}]) if port else flash_plan()
        if plan["ok"]:
            link.pending = {"kind": "flash", "port": plan["port"]}
        return plan["said"]
    if _PREP.search(low):
        done = prepare_pi({}, run)
        return ("The Pi's preloaded configs and setup steps are in " + done["folder"] + ". " + " ".join(
            f"{n}. {s}" for n, s in enumerate(done["steps"], 1)))
    found = _PUSH.search(low)
    if found:
        host = found.group(1)
        user = (re.search(r"\bas (\w+)\b", low) or [None, "pi"])[1]
        link.pending = {"kind": "push", "host": host, "user": user}
        return (f"I'll copy the greenhouse node and its preloaded configs to {user}@{host} over SSH with its key, "
                "then install it there. Say “yes, push it” to go ahead.")
    return None
