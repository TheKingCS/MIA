"""
core.greenhouse_link
======================

"Take over the greenhouse" (DEC-0150; Zac, 2026-11-08: "build it and essentially pass her to it, so that she can
integrate and monitor everything she has set up for monitoring"). MIA's half of the link to the MIA Homestead node
(`homestead/`): she watches; the node, its control loop and its safety MCU act (Zac's answer 4). Nothing here sends
the node a command.

- **How the state arrives** (Zac's answer 3): (a) by hand, as before: the node's `home_snapshot.json` dropped in
  `homestead_snapshots/` (core/homestead_manager.py), and its `dashboard_state.json` dropped there too; (b) fetched
  over the home network or Tailscale from the node's read-only export server (`homestead/viewer/serve_exports.py`),
  every `EVERY_MINUTES`, only from an address on the person's own network; (c) the live link (2026-11-09): the
  node's own dashboard and digital twin served read-only beside the exports (`live_url`, "show me the greenhouse
  live"), and "how's the greenhouse?" read fresh when the last read is over `FRESH_SECONDS` old.
- **What she watches** (`monitors()`): every sensor the node reports, cell by cell, with its latest value and whether
  it's stale. The node decides what exists, so a new probe on the node is a new monitor here with nothing to change.
- **What reaches the person** (`new_alerts()`): each new critical alert from the node as urgent, each new warning as
  timely, through the communication gate, once each.
- **What she keeps**: readings into the grow lab (the Data Logger's `grow:<cell>:<measure>` series, core/grow_lab.py),
  one every `KEEP_MINUTES` a sensor, so its history and ranges work the same as readings typed in.
- **What she knows** (`node_knowledge()`): the node's own generated documents, `homestead/docs/
  FEATURES_AND_CAPABILITIES.md` (each module, what it can do, its limits, its proof) and `HARDWARE_BOM_LIVE.md`
  (every part it needs), so "what can you connect to in the greenhouse?" is answered from what the node declares, not
  from a copy.

State is device-level (`data/greenhouse_link.json`, written through atomic_write_text): the last fetch, the node's
latest state, and which alerts have been raised. Facts in code; the model only phrases them.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import urlparse

from core.atomic_write import atomic_write_text
from core.logger import get_logger

log = get_logger(__name__)

ROOT = Path(__file__).resolve().parent.parent
_DATA_DIR = ROOT / "data"
FILE_NAME = "greenhouse_link.json"
NODE_DOCS = ROOT / "homestead" / "docs"
STATE_FILE = "dashboard_state.json"
EVERY_MINUTES = 4  # the app checks every 5 minutes; a little under, so timer jitter never skips a turn
KEEP_MINUTES = 30
MAX_BYTES = 2_000_000
TIMEOUT = 3  # read on the app's main thread: an unreachable node mustn't hold it up
_MEASURES = {"ph": "ph", "ec": "ec", "temp_water": "water_temp", "do": "oxygen", "temp_air": "air_temp",
             "humidity": "humidity"}  # node sensor type -> grow lab measure


class LinkError(RuntimeError):
    """The node couldn't be reached or read, said plainly."""


# ------------------------------------------------------------------ the store

class GreenhouseLink:
    """The link's own state: whether MIA has taken over, the node's address, the last state read and when, the
    alerts already raised, and where the setup sequence is (core/greenhouse_setup.py)."""

    def __init__(self, context=None, data_dir: Optional[Path] = None) -> None:
        """Loads the link's state from data/ (or the given folder)."""
        self.context = context
        self.data_dir = Path(data_dir) if data_dir is not None else _DATA_DIR
        self._file = self.data_dir / FILE_NAME
        self._load()

    def _load(self) -> None:
        """Reads the state (the setup sequence's place too); a missing or unreadable file starts fresh (logged)."""
        self.taken_over, self.url, self.fetched_at, self.state, self.raised, self.kept = False, "", "", {}, [], {}
        try:
            raw = json.loads(self._file.read_text(encoding="utf-8")) if self._file.exists() else {}
        except (OSError, ValueError):
            log.exception("%s unreadable; starting fresh", FILE_NAME)
            raw = {}
        self.taken_over = bool(raw.get("taken_over"))
        self.url = str(raw.get("url") or "")
        self.fetched_at = str(raw.get("fetched_at") or "")
        self.state = raw.get("state") or {}
        self.raised = list(raw.get("raised") or [])[-500:]
        self.kept = dict(raw.get("kept") or {})
        self.setup_started = bool(raw.get("setup_started"))  # the setup sequence begun (core/greenhouse_setup.py)
        self.setup_said = list(raw.get("setup_said") or [])  # its steps the person said are done, or skipped
        self.pending: dict = {}  # a device step waiting for its yes (core/greenhouse_provision.py); never saved

    def reload(self) -> None:
        """Reads the file again (after undo restored it)."""
        self._load()

    def save(self) -> None:
        """Writes the state atomically, the setup sequence's place with it."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._file, json.dumps({"taken_over": self.taken_over, "url": self.url,
                                                  "fetched_at": self.fetched_at, "state": self.state,
                                                  "raised": self.raised[-500:], "kept": self.kept,
                                                  "setup_started": self.setup_started,
                                                  "setup_said": self.setup_said}, indent=1))


# ------------------------------------------------------------------ reading the node (pure where it can be)

def monitors(state: dict) -> list[dict]:
    """Pure logic. Every sensor the node reports: {cell, type, unit, value, at, stale}, cell by cell."""
    out = []
    for cell in (state or {}).get("cells") or []:
        for r in cell.get("readings") or []:
            out.append({"cell": str(cell.get("name", "")), "type": str(r.get("type", "")), "unit": str(r.get("unit") or ""),
                        "value": r.get("value"), "at": str(r.get("timestamp") or ""), "stale": bool(r.get("is_stale"))})
    return out


def _alert_key(a: dict) -> str:
    """Pure logic. One alert's identity: its id on the node, else its source and message."""
    return str(a.get("id") or f"{a.get('source', '')}|{a.get('message', '')}")


def new_alerts(state: dict, raised: list) -> list[dict]:
    """Pure logic. The node's open critical and warning alerts not raised yet, critical first."""
    seen = set(raised)
    found = [a for a in (state or {}).get("alerts") or []
             if a.get("severity") in ("critical", "warning") and not a.get("resolved") and _alert_key(a) not in seen]
    return sorted(found, key=lambda a: 0 if a.get("severity") == "critical" else 1)


def status_line(state: dict) -> str:
    """Pure logic. The node in one line: each cell's readings, the open alerts, and any sensor that's stale."""
    if not state:
        return "I haven't heard from the greenhouse yet."
    cells = {}
    for m in monitors(state):
        if m["value"] is None:
            continue
        unit = f" {m['unit']}" if m["unit"] else ""
        cells.setdefault(m["cell"], []).append(f"{m['type'].replace('_', ' ')} {m['value']:g}{unit}"
                                               if isinstance(m["value"], (int, float)) else f"{m['type']} {m['value']}")
    alerts = [a for a in state.get("alerts") or [] if not a.get("resolved")]
    crit = sum(1 for a in alerts if a.get("severity") == "critical")
    warn = sum(1 for a in alerts if a.get("severity") == "warning")
    stale = [f"{m['cell']} {m['type']}" for m in monitors(state) if m["stale"]]
    parts = [f"{name}: {', '.join(vals)}" for name, vals in cells.items()]
    parts.append(f"{crit} critical, {warn} warning" if alerts else "no open alerts")
    parts.append(f"stale: {', '.join(stale)}" if stale else "every sensor reporting")
    return "Greenhouse: " + "; ".join(parts) + "."


def node_knowledge(docs: Path = NODE_DOCS) -> dict:
    """What the node declares about itself, from its own generated documents: {modules: [{id, name, does, limits,
    proven}], hardware: [lines]}; empty lists when the documents aren't there."""
    modules, hardware = [], []
    try:
        text = (docs / "FEATURES_AND_CAPABILITIES.md").read_text(encoding="utf-8")
    except OSError:
        text = ""
    for block in re.split(r"^## ", text, flags=re.M)[1:]:
        head = re.match(r"(.+?) \(`([\w.]+)`\)", block)
        if not head:
            continue
        limits = re.search(r"\*\*Limits:\*\* ([^\n]+)", block)
        proof = re.search(r"\*\*Proof this actually works:\*\*\n((?:- [^\n]*\n?)+)", block)
        does = [l[2:].strip() for l in re.findall(r"^- [^\n]+", block.split("**Tracks/produces:**")[0], re.M)]
        modules.append({"id": head.group(2), "name": head.group(1).strip(), "does": does[:6],
                        "limits": (limits.group(1)[:240] if limits else ""), "proven": bool(proof)})
    try:
        bom = (docs / "HARDWARE_BOM_LIVE.md").read_text(encoding="utf-8")
    except OSError:
        bom = ""
    hardware = [l.strip() for l in bom.splitlines() if re.match(r"\s+\d+x ", l)]
    return {"modules": modules, "hardware": hardware}


# ------------------------------------------------------------------ fetching

def own_node(url: str) -> bool:
    """Whether a node address is on the person's own network (this computer, the home network, Tailscale)."""
    from core.port_scanner import own_network

    parts = urlparse(url or "")
    return parts.scheme in ("http", "https") and bool(parts.hostname) and own_network(parts.hostname)


def _get(url: str) -> bytes:
    """GETs a URL with a short timeout and a size cap (the node's own export server only: fetch() checks that)."""
    import urllib.request

    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "MIA"}), timeout=TIMEOUT) as r:
        data = r.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise LinkError("The greenhouse sent more than I'll read.")
    return data


def _dropped(context) -> Optional[dict]:
    """The node's dashboard state dropped in the watched folder by hand (answer 3a), or None."""
    manager = getattr(context, "homestead", None)
    folder = None
    try:
        folder = manager.import_folder_path() if manager is not None else None
    except Exception:
        folder = None
    path = Path(folder) / STATE_FILE if folder else ROOT / "homestead_snapshots" / STATE_FILE
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None
    except (OSError, ValueError):
        return None


def fetch(context, link: GreenhouseLink, get: Optional[Callable[[str], bytes]] = None,
          now: Optional[datetime] = None) -> dict:
    """The node's latest state: fetched from its export server when an address is set (only on the person's own
    network), else the file dropped by hand. Kept on the link; LinkError when neither is there."""
    now = now or datetime.now()
    state = None
    if link.url:
        if not own_node(link.url):
            raise LinkError("I only read the greenhouse from an address on your own network or Tailscale.")
        try:
            state = json.loads((get or _get)(link.url.rstrip("/") + "/" + STATE_FILE).decode("utf-8", "replace"))
        except (OSError, ValueError) as problem:
            raise LinkError(f"The greenhouse at {link.url} didn't answer ({type(problem).__name__}). Is "
                            "viewer/serve_exports.py running on the node?") from problem
    else:
        state = _dropped(context)
    if not isinstance(state, dict) or "cells" not in state:
        raise LinkError("I don't have the greenhouse's state yet: give me its address, or drop its "
                        "dashboard_state.json in homestead_snapshots/.")
    link.state, link.fetched_at = state, now.isoformat(timespec="seconds")
    link.save()
    return state


# ------------------------------------------------------------------ acting on it

def keep_readings(context, link: GreenhouseLink, now: Optional[datetime] = None) -> int:
    """The node's readings into the grow lab's series (one every KEEP_MINUTES a sensor, only fresh ones); how many."""
    logger = getattr(context, "data_logger", None)
    if logger is None:
        return 0
    from core.grow_lab import series_id

    now = now or datetime.now()
    kept = 0
    for m in monitors(link.state):
        measure = _MEASURES.get(m["type"])
        if measure is None or m["stale"] or not isinstance(m["value"], (int, float)):
            continue
        series = series_id(m["cell"], measure)
        last = link.kept.get(series, "")
        if last and now - datetime.fromisoformat(last) < timedelta(minutes=KEEP_MINUTES):
            continue
        value, unit = float(m["value"]), m["unit"]
        if measure == "ec" and unit.lower() in ("us/cm", "µs/cm", "microsiemens/cm"):
            value, unit = round(value / 1000, 3), "mS/cm"
        logger.add_reading(series, value, unit, note="from the greenhouse node")
        link.kept[series] = now.isoformat(timespec="seconds")
        kept += 1
    if kept:
        link.save()
    return kept


def alert_candidates(link: GreenhouseLink) -> list:
    """The gate candidates for the node's new alerts (critical urgent, warning timely), marking each raised."""
    from core.communication_gate import TIMELY, URGENT, Candidate

    out = []
    for a in new_alerts(link.state, link.raised):
        critical = a.get("severity") == "critical"
        out.append(Candidate("greenhouse", "\U0001F6A8 Greenhouse" if critical else "\U0001F33F Greenhouse",
                             f"{a.get('source', 'the greenhouse')}: {a.get('message', '')}",
                             URGENT if critical else TIMELY, source="greenhouse",
                             level="warning" if critical else "info", fingerprint=f"greenhouse:{_alert_key(a)}"))
        link.raised.append(_alert_key(a))
    if out:
        link.save()
    return out


def take_over(context, link: GreenhouseLink, url: str = "", get: Optional[Callable[[str], bytes]] = None) -> str:
    """"Take over the greenhouse": remember the node's address (when given), read it now, and say what MIA watches
    from here on and what she can't yet."""
    if url:
        link.url = url.strip()
    link.taken_over = True
    link.save()
    try:
        state = fetch(context, link, get)
    except LinkError as problem:
        return f"I'll watch the greenhouse once I can read it. {problem}"
    found = monitors(state)
    live = [m for m in found if not m["stale"] and m["value"] is not None]
    stale = [f"{m['cell']} {m['type']}" for m in found if m["stale"] or m["value"] is None]
    cells = sorted({m["cell"] for m in found})
    said = (f"I'm watching the greenhouse now: {len(live)} sensor{'s' if len(live) != 1 else ''} across "
            f"{len(cells)} cell{'s' if len(cells) != 1 else ''} ({', '.join(cells)}). Critical alerts reach you right "
            "away, warnings when there's an opening, and the readings go into the grow lab. The node and its safety "
            "MCU still do the controlling; I watch and suggest.")
    return said + (f" Not reporting yet: {', '.join(stale)}." if stale else "")


def tick(context, link: GreenhouseLink, now: Optional[datetime] = None, get=None) -> list:
    """One check from the app's loop: when MIA has taken over and EVERY_MINUTES have passed, read the node, keep its
    readings, and return the gate candidates for its new alerts."""
    now = now or datetime.now()
    if not link.taken_over:
        return []
    if link.fetched_at and now - datetime.fromisoformat(link.fetched_at) < timedelta(minutes=EVERY_MINUTES):
        return []
    try:
        fetch(context, link, get, now)
    except LinkError as problem:
        log.info("Greenhouse not read this time: %s", problem)
        return []
    keep_readings(context, link, now)
    return alert_candidates(link)


# ------------------------------------------------------------------ talking about it

_TAKE = re.compile(r"\b(?:take over|watch|monitor|connect to|hook (?:up|into)) (?:the )?greenhouse\b")
_URL = re.compile(r"\bhttps?://[\w.\-:]+\b|\b(?:\d{1,3}\.){3}\d{1,3}(?::\d+)?\b")
_HOW = re.compile(r"\b(?:how'?s|how is|status of|check on) (?:the )?greenhouse\b|\bgreenhouse status\b")
_WHAT = re.compile(r"\bwhat (?:are you|do you) (?:watching|monitoring) in the greenhouse\b")
_LIVE = re.compile(r"\b(?:show me|open|pull up) (?:the )?greenhouse(?:'?s)? (?:live|dashboard|twin)\b|"
                   r"\bgreenhouse (?:live|dashboard)\b|\b(?:the )?greenhouse'?s digital twin\b")
FRESH_SECONDS = 60  # "how's the greenhouse?" reads the node again when the last read is older than this


def live_url(link) -> str:
    """The node's live dashboard (served read-only by its export server, homestead/viewer/serve_exports.py v0.2),
    or "" when no address is set (DEC-0150 answer 3c)."""
    url = (getattr(link, "url", "") or "").rstrip("/")
    return f"{url}/dashboard.html" if url else ""


def _fresh(context, link, get=None) -> str:
    """Reads the node again for a "how's it doing?" when the last read is over FRESH_SECONDS old; says, in front of
    the status, when it couldn't be reached (the last reading's time said with it)."""
    if not link.url:
        return ""
    if link.fetched_at and (datetime.now() - datetime.fromisoformat(link.fetched_at)).total_seconds() < FRESH_SECONDS:
        return ""
    try:
        fetch(context, link, get=get)
        link.save()
        return ""
    except LinkError:
        return f"I couldn't reach the node just now; this is from {link.fetched_at[11:16] or 'my last read'}. "


def reply(context, text: str, get=None) -> Optional[str]:
    """What MIA says, in code, to "take over the greenhouse" (with the node's address, optionally), "how's the
    greenhouse?" (read fresh from the node), "show me the greenhouse live" (its live dashboard's address) and "what
    are you watching in the greenhouse?"; None otherwise."""
    link = getattr(context, "greenhouse_link", None)
    if link is None:
        return None
    said = (text or "").lower()
    if _TAKE.search(said):
        found = _URL.search(text or "")
        url = found.group(0) if found else ""
        if url and not url.startswith("http"):
            url = f"http://{url}" + ("" if ":" in url else ":8770")
        return take_over(context, link, url)
    if _LIVE.search(said):
        url = live_url(link)
        return (f"The greenhouse's live dashboard is at {url} (the digital twin is beside it), on any device on your "
                "network. It only shows; the node keeps control." if url else
                "I don't have the node's address yet. Say \"take over the greenhouse at <its address>\" first.")
    if _HOW.search(said):
        if not link.taken_over:
            return "I'm not watching the greenhouse yet. Say \"take over the greenhouse\" when the node is running."
        return _fresh(context, link, get) + status_line(link.state)
    if _WHAT.search(said):
        found = monitors(link.state)
        if not found:
            return "Nothing yet: I haven't read the greenhouse."
        return "In the greenhouse I watch: " + "; ".join(
            f"{m['cell']} {m['type'].replace('_', ' ')}{' (stale)' if m['stale'] else ''}" for m in found) + "."
    return None


_ABOUT = re.compile(r"\b(?:greenhouse|aquaponics|node|safety mcu|probe|sensors?|dosing|relay|esp32|raspberry pi|"
                    r"the pi|pump|grow bed|fish tank)\b")
# The node's own technology: only these bring its whole module list into the turn.
_TECH = re.compile(r"\b(?:node|modules?|safety mcu|mcu|probes?|sensors?|dosing|relays?|esp32|raspberry pi|the pi|"
                   r"pumps?|hardware|parts|controllers?|connect\w*|wir(?:e|ed|ing)|technolog\w+|equipment)\b")


def context_block(context, prompt: str = "") -> str:
    """For the model's system message, on a turn about the greenhouse: that a separate node runs it and what her
    own part is, with its latest state once she's watching it; and, when the question names the technology (a
    sensor, a module, a part), what the node declares (its modules, with what each can do and whether it's
    proven; its parts). "" otherwise."""
    if not _ABOUT.search((prompt or "").lower()):
        return ""
    know = node_knowledge()
    if not know["modules"] and not know["hardware"]:
        return ""
    link = getattr(context, "greenhouse_link", None)
    now = (f" Right now: {status_line(link.state)}" if link is not None and link.taken_over and link.state
           else " You aren't watching a node right now, so you have no live readings from one.")
    if not _TECH.search((prompt or "").lower()):
        # Measured: with every module named, a question like "how do you improve yields?" was answered by
        # offering the node's modules as her own. So the list waits for a question about the technology.
        proven = sum(1 for m in know["modules"] if m["proven"])
        return ("The greenhouse is run by its own controller, the greenhouse node (MIA Homestead), which declares "
                f"{len(know['modules'])} modules of its own ({proven} with proof recorded). They are the node's, "
                "not apps or abilities of yours: never offer them as things the person can use through you."
                + now + " Your own part: you read the node's sensors, keep the readings as history, pass on its "
                "alerts and propose changes, which go through the node's approval queue with the person's OK. The "
                "node and its safety MCU do the controlling; you never switch, dose or run anything.")
    mods = "; ".join(f"{m['name']} ({'proven' if m['proven'] else 'unverified'}): {', '.join(m['does'][:3])}"
                     for m in know["modules"][:25])
    parts = "; ".join(know["hardware"][:30])
    return ("The greenhouse node (MIA Homestead) declares these modules: " + mods + ". Its parts: " + parts + "."
            " Those modules belong to the node, a separate controller: they are not apps or abilities of yours, so "
            "speak of them as the node's (\"proven\" means the node's own proof is recorded, \"unverified\" that "
            "it's declared and not shown yet)."
            + now + " The node and its safety MCU do the controlling; you watch and propose, and changes to dosing "
            "or targets go through the node's approval queue with the person's OK.")
