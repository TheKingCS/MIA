"""
core.inspection
=================

Universal Inspection, phases 1 and 2 (DEC-0056, docs/INSPECTION_AND_SELF_PLAN.md):
MIA investigates a subject with every relevant *authorized* method she
has, keeps each finding as evidence (what, where it came from, when, how
sure), correlates findings from different methods, says what she
couldn't determine and why, and writes a report.

- **Evidence**: one fact, its value, the method and source that gave it,
  when it was observed, a confidence level (CONFIRMED, HIGH, PROBABLE,
  POSSIBLE, UNKNOWN) and when it should be checked again.
- **Methods** (`METHODS`): each says which subjects it applies to, what it
  obtains, what it needs, whether it's available here and now, and its
  permission level: PASSIVE (reading what a device says about itself),
  AUTHORIZED (reading with permission the person gave), ACTIVE (probing,
  like a port scan: asked first, rate-limited) or DISRUPTIVE (never
  without explicit approval). Only PASSIVE methods run without asking;
  nothing here touches passwords, keys, tokens or personal files.
- **Subjects** today: `this_computer` (the computer MIA runs on) and
  `mia` (MIA herself: her code, decisions, capabilities and health, the
  self-knowledge side, DEC-0057). Cameras, the network beyond this
  computer, other devices and research come in later phases, and are
  never claimed before they exist.
- **Correlation**: two methods agreeing on a fact raise it to CONFIRMED;
  disagreeing leaves both, marked as a contradiction to look into,
  never silently resolved.

Reports are kept on this device (`data/inspections/`), the latest per
subject and a short history, so a follow-up ("can it run a bigger
model?") builds on what was found instead of starting over.
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Optional

from core.logger import get_logger

log = get_logger(__name__)

ROOT = Path(__file__).resolve().parent.parent
_DIR = ROOT / "data" / "inspections"
KEEP = 20  # past reports kept per subject

CONFIRMED, HIGH, PROBABLE, POSSIBLE, UNKNOWN = "CONFIRMED", "HIGH", "PROBABLE", "POSSIBLE", "UNKNOWN"
PASSIVE, AUTHORIZED, ACTIVE, DISRUPTIVE = "passive", "authorized", "active", "disruptive"
SUBJECTS = {"this_computer": "this computer", "mia": "MIA herself"}


@dataclass
class Evidence:
    fact: str  # "cpu.model", "os.version"...
    value: object
    method: str
    source: str  # what answered: "Windows (CIM)", "psutil", "the code"
    confidence: str = CONFIRMED
    observed_at: str = ""
    recheck_after: str = ""  # ISO: past this, the fact may be stale
    note: str = ""


@dataclass
class Gap:
    """Something that couldn't be determined, and why (never "doesn't exist")."""

    what: str
    why: str
    method: str = ""


@dataclass
class Method:
    name: str
    subjects: tuple
    obtains: str
    needs: str
    level: str
    run: Callable  # (context) -> (list[Evidence], list[Gap])
    available: Callable = lambda context: True


@dataclass
class Report:
    subject: str
    started_at: str
    finished_at: str = ""
    evidence: list = field(default_factory=list)
    gaps: list = field(default_factory=list)
    contradictions: list = field(default_factory=list)
    problems: list = field(default_factory=list)
    methods_run: list = field(default_factory=list)
    methods_skipped: list = field(default_factory=list)  # [(name, why)]


def _now() -> datetime:
    return datetime.now()


def _ev(fact: str, value, method: str, source: str, confidence: str = CONFIRMED, recheck_hours: float = 24,
        note: str = "") -> Evidence:
    now = _now()
    return Evidence(fact, value, method, source, confidence, now.isoformat(timespec="seconds"),
                    (now + timedelta(hours=recheck_hours)).isoformat(timespec="seconds"), note)


def _run(args: list[str], timeout: float = 8) -> str:
    """A read-only system command's output, or "" (never raises)."""
    try:
        out = subprocess.run(args, capture_output=True, text=True, timeout=timeout,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return (out.stdout or "").strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def _gib(n: float) -> float:
    return round(n / 1024 ** 3, 1)


# ---------------------------------------------------------------- this computer


def _os(context):
    ev = [_ev("os.name", platform.system(), "os", "the operating system"),
          _ev("os.version", platform.version(), "os", "the operating system"),
          _ev("os.release", platform.release(), "os", "the operating system"),
          _ev("os.machine", platform.machine(), "os", "the operating system"),
          _ev("computer.name", platform.node(), "os", "the operating system"),
          _ev("python.version", platform.python_version(), "os", "the running Python")]
    try:
        import psutil

        booted = datetime.fromtimestamp(psutil.boot_time())
        ev.append(_ev("os.booted", booted.isoformat(timespec="minutes"), "os", "psutil", recheck_hours=1))
    except Exception:
        pass
    return ev, []


def _cpu_memory(context):
    try:
        import psutil
    except ImportError:
        return [], [Gap("CPU and memory", "psutil isn't installed", "cpu_memory")]
    ev = [_ev("cpu.cores_physical", psutil.cpu_count(logical=False), "cpu_memory", "psutil"),
          _ev("cpu.threads", psutil.cpu_count(logical=True), "cpu_memory", "psutil"),
          _ev("cpu.use_percent", psutil.cpu_percent(interval=0.5), "cpu_memory", "psutil", recheck_hours=0.05),
          _ev("memory.total_gb", _gib(psutil.virtual_memory().total), "cpu_memory", "psutil"),
          _ev("memory.use_percent", psutil.virtual_memory().percent, "cpu_memory", "psutil", recheck_hours=0.05)]
    name = platform.processor()
    if name:
        ev.append(_ev("cpu.model", name, "cpu_memory", "the operating system", PROBABLE,
                      note="Windows' short processor name; the hardware query below gives the full one"))
    return ev, []


def _windows_hardware(context):
    """The full CPU, GPU and board names from Windows' own hardware query (read-only)."""
    query = ("$c=Get-CimInstance Win32_Processor | Select-Object -First 1 Name;"
             "$g=Get-CimInstance Win32_VideoController | Select-Object Name,AdapterRAM,DriverVersion;"
             "$b=Get-CimInstance Win32_BaseBoard | Select-Object Manufacturer,Product;"
             "$s=Get-CimInstance Win32_BIOS | Select-Object SMBIOSBIOSVersion;"
             "@{cpu=$c.Name;gpus=@($g);board=$b;bios=$s.SMBIOSBIOSVersion} | ConvertTo-Json -Depth 3 -Compress")
    raw = _run(["powershell", "-NoProfile", "-Command", query], timeout=20)
    try:
        data = json.loads(raw) if raw else None
    except ValueError:
        data = None
    if not data:
        return [], [Gap("CPU, GPU and motherboard names", "Windows' hardware query didn't answer", "windows_hardware")]
    ev = []
    if data.get("cpu"):
        ev.append(_ev("cpu.model", " ".join(str(data["cpu"]).split()), "windows_hardware", "Windows (CIM)"))
    for i, g in enumerate(data.get("gpus") or []):
        ev.append(_ev(f"gpu.{i}.name", g.get("Name"), "windows_hardware", "Windows (CIM)"))
        if g.get("DriverVersion"):
            ev.append(_ev(f"gpu.{i}.driver", g.get("DriverVersion"), "windows_hardware", "Windows (CIM)"))
    board = data.get("board") or {}
    if board.get("Product"):
        ev.append(_ev("motherboard", f"{board.get('Manufacturer', '')} {board.get('Product')}".strip(),
                      "windows_hardware", "Windows (CIM)"))
    if data.get("bios"):
        ev.append(_ev("firmware.bios_version", data["bios"], "windows_hardware", "Windows (CIM)"))
    return ev, [Gap("GPU memory", "Windows' AdapterRAM caps at 4 GB, so it isn't used; the AI runtime reports "
                                  "the real figure when a model is loaded", "windows_hardware")]


def _disks(context):
    try:
        import psutil
    except ImportError:
        return [], []
    ev, gaps = [], []
    for part in psutil.disk_partitions(all=False):
        try:
            use = psutil.disk_usage(part.mountpoint)
        except OSError:
            continue
        key = part.mountpoint.rstrip("\\/:").replace(":", "") or "root"
        ev.append(_ev(f"disk.{key}.size_gb", _gib(use.total), "disks", "psutil"))
        ev.append(_ev(f"disk.{key}.free_gb", _gib(use.free), "disks", "psutil", recheck_hours=1))
        ev.append(_ev(f"disk.{key}.use_percent", use.percent, "disks", "psutil", recheck_hours=1))
    gaps.append(Gap("Disk health (SMART)", "needs administrator rights and a SMART tool; not read", "disks"))
    return ev, gaps


def _network(context):
    try:
        import psutil
    except ImportError:
        return [], []
    import socket

    ev = []
    stats = psutil.net_if_stats()
    for name, addrs in psutil.net_if_addrs().items():
        st = stats.get(name)
        if st is None or not st.isup:
            continue
        v4 = [a.address for a in addrs if a.family == socket.AF_INET and not a.address.startswith("127.")]
        if v4:
            ev.append(_ev(f"network.{name}.ipv4", ", ".join(v4), "network", "psutil", recheck_hours=1))
            if st.speed:
                ev.append(_ev(f"network.{name}.speed_mbps", st.speed, "network", "psutil", recheck_hours=1))
    listening = sorted({c.laddr.port for c in psutil.net_connections(kind="tcp") if c.status == "LISTEN"
                        and c.laddr and c.laddr.ip not in ("127.0.0.1", "::1")}) if hasattr(psutil, "net_connections") else []
    if listening:
        ev.append(_ev("network.listening_ports", listening[:40], "network", "psutil", recheck_hours=1,
                      note="ports this computer offers to the network (local-only ones left out)"))
    return ev, [Gap("Other devices on the network", "the network map is a later phase (an active scan is asked "
                                                    "first); not looked at", "network")]


def _devices(context):
    devices = getattr(context, "devices", None)
    if devices is None:
        return [], [Gap("Connected devices", "the device framework isn't running here", "devices")]
    try:
        storage = [d.display_name for d in devices.list_block_devices()]
        serial = [d.display_name for d in devices.list_serial_devices()]
    except Exception:
        return [], [Gap("Connected devices", "the device list failed", "devices")]
    return [_ev("devices.storage", storage, "devices", "MIA's device framework", recheck_hours=0.5),
            _ev("devices.serial", serial, "devices", "MIA's device framework", recheck_hours=0.5)], \
        [Gap("USB devices that aren't storage or serial (cameras, keyboards...)", "not listed yet", "devices")]


def _security(context):
    ev, gaps = [], []
    if platform.system() == "Windows":
        raw = _run(["netsh", "advfirewall", "show", "allprofiles", "state"])
        states = [line.split()[-1] for line in raw.splitlines() if line.strip().lower().startswith("state")]
        if states:
            ev.append(_ev("security.firewall", "on for every profile" if all(s.upper() == "ON" for s in states)
                          else f"profiles: {', '.join(states)}", "security", "Windows Firewall (netsh)"))
        else:
            gaps.append(Gap("Firewall", "Windows didn't say", "security"))
        gaps.append(Gap("Disk encryption (BitLocker)", "needs administrator rights; not read", "security"))
    else:
        gaps.append(Gap("Firewall", "not read on this system yet", "security"))
    return ev, gaps


def _ai_runtime(context):
    try:
        from core.model_registry import runtime_info

        info = runtime_info(context) or {}
    except Exception:
        info = {}
    if not info.get("model"):
        return [], [Gap("The AI model", "the AI runtime didn't answer", "ai_runtime")]
    ev = [_ev("ai.model", info.get("model"), "ai_runtime", info.get("source") or "the AI runtime")]
    for key in ("parameters", "quantization", "runtime", "version", "context", "on_gpu", "vram"):
        if info.get(key) not in (None, ""):
            ev.append(_ev(f"ai.{key}", info[key], "ai_runtime", info.get("source") or "the AI runtime", recheck_hours=1))
    return ev, []


def _health(context):
    problems = []
    try:
        from core.system_health import read_system_health

        h = read_system_health(os.path.abspath(os.sep))
        temp = getattr(h, "cpu_temperature_c", None)
    except Exception:
        temp = None
    ev = []
    if temp is not None:
        ev.append(_ev("cpu.temperature_c", temp, "health", "psutil", recheck_hours=0.05))
        return ev, []
    return ev, [Gap("CPU temperature", "Windows doesn't share it without the maker's own tool" if
                    platform.system() == "Windows" else "no sensor answered", "health")]


# ---------------------------------------------------------------- MIA herself (self-knowledge, DEC-0057)


def _mia_code(context):
    import ast

    counts = {"core": 0, "modules": 0, "tests": 0, "web": 0}
    functions = 0
    for part in ("core", "modules", "tests"):
        for path in (ROOT / part).rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            counts[part] += 1
            if part == "core":
                try:
                    tree = ast.parse(path.read_text(encoding="utf-8"))
                    functions += sum(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) for n in ast.walk(tree))
                except (SyntaxError, OSError, ValueError):
                    pass
    counts["web"] = len(list((ROOT / "web").glob("*.html")))
    ev = [_ev("code.core_modules", counts["core"], "mia_code", "the code"),
          _ev("code.core_functions", functions, "mia_code", "the code"),
          _ev("code.desktop_modules", len([p for p in (ROOT / "modules").iterdir() if (p / "module.py").exists()]),
              "mia_code", "the code"),
          _ev("code.test_files", counts["tests"], "mia_code", "the code"),
          _ev("code.web_pages", counts["web"], "mia_code", "the code")]
    head = _run(["git", "-C", str(ROOT), "log", "-1", "--format=%h %cs %s"])
    if head:
        ev.append(_ev("code.latest_change", head, "mia_code", "git"))
    return ev, [Gap("Whether the full test suite passes right now", "not run during an inspection (two minutes); "
                                                                     "the last run's result isn't recorded", "mia_code")]


def _mia_decisions(context):
    import re

    path = ROOT / "docs" / "DECISIONS.md"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return [], [Gap("Decisions", "docs/DECISIONS.md isn't here", "mia_decisions")]
    statuses = re.findall(r"^### (DEC-\d{4}).*?\n- Status: (\w+)", text, re.MULTILINE)
    by = {}
    for _dec, st in statuses:
        by[st] = by.get(st, 0) + 1
    waiting = [d for d, st in statuses if st == "PROPOSED"]
    return [_ev("decisions.count", len(statuses), "mia_decisions", "docs/DECISIONS.md"),
            _ev("decisions.by_status", by, "mia_decisions", "docs/DECISIONS.md"),
            _ev("decisions.waiting", waiting, "mia_decisions", "docs/DECISIONS.md")], []


def _mia_capabilities(context):
    try:
        from core.capabilities import capability_map

        apps = [a for a in capability_map(context) if a["where"] != "retired"]
    except Exception:
        return [], [Gap("Capabilities", "the capability map failed", "mia_capabilities")]
    registry = getattr(context, "assistant_actions", None)
    return [_ev("capabilities.apps", len(apps), "mia_capabilities", "the capability map"),
            _ev("capabilities.desktop_only", [a["name"] for a in apps if a["where"] == "desktop"], "mia_capabilities",
                "the capability map"),
            _ev("capabilities.tools", len(getattr(registry, "_actions", {}) or {}), "mia_capabilities",
                "the Assistant's registry", note="in this runtime (the desktop registers the most)")], []


def _mia_health(context):
    ev, gaps = [], []
    failures = getattr(context, "failures", None)
    if failures is not None:
        try:
            issues = failures.issues(30)
            ev.append(_ev("health.open_issues_30d", len(issues), "mia_health", "the Fix-It Log", recheck_hours=6))
            if issues:
                ev.append(_ev("health.top_issue", str(issues[0].get("title") or issues[0].get("kind") or ""),
                              "mia_health", "the Fix-It Log", recheck_hours=6))
        except Exception:
            gaps.append(Gap("Issues", "the Fix-It Log couldn't be read", "mia_health"))
    connectivity = getattr(context, "connectivity", None)
    if connectivity is not None:
        ev.append(_ev("health.internet", getattr(connectivity, "status", "unknown"), "mia_health", "connectivity",
                      recheck_hours=0.1))
    return ev, gaps


def _windows_only(context) -> bool:
    return platform.system() == "Windows"


METHODS: tuple[Method, ...] = (
    Method("os", ("this_computer",), "operating system, version, name, uptime", "nothing", PASSIVE, _os),
    Method("cpu_memory", ("this_computer",), "cores, threads, memory, current load", "psutil", PASSIVE, _cpu_memory),
    Method("windows_hardware", ("this_computer",), "full CPU, GPU, motherboard and BIOS names", "Windows",
           PASSIVE, _windows_hardware, _windows_only),
    Method("disks", ("this_computer",), "drives, size, free space", "psutil", PASSIVE, _disks),
    Method("network", ("this_computer",), "network adapters, addresses, speed, ports offered", "psutil", PASSIVE, _network),
    Method("devices", ("this_computer",), "attached storage and serial devices", "MIA's device framework", PASSIVE, _devices),
    Method("security", ("this_computer",), "firewall state", "Windows Firewall", PASSIVE, _security),
    Method("ai_runtime", ("this_computer", "mia"), "the AI model, its size, where it runs", "Ollama", PASSIVE, _ai_runtime),
    Method("health", ("this_computer",), "temperature", "a temperature sensor", PASSIVE, _health),
    Method("mia_code", ("mia",), "her code: modules, functions, apps, tests, pages, latest change", "the code", PASSIVE, _mia_code),
    Method("mia_decisions", ("mia",), "her decisions and which wait on the owner", "docs/DECISIONS.md", PASSIVE, _mia_decisions),
    Method("mia_capabilities", ("mia",), "what she can do: apps, tools, desktop-only apps", "the capability map", PASSIVE,
           _mia_capabilities),
    Method("mia_health", ("mia",), "open issues, internet", "the Fix-It Log, connectivity", PASSIVE, _mia_health),
)


# ---------------------------------------------------------------- correlation and problems (pure)


def correlate(evidence: list[Evidence]) -> tuple[list[Evidence], list[dict]]:
    """Pure logic. Facts two methods agree on become CONFIRMED (the extra
    copy kept as support); a disagreement is kept, both sides, as a
    contradiction to look into."""
    by_fact: dict[str, list[Evidence]] = {}
    for e in evidence:
        by_fact.setdefault(e.fact, []).append(e)
    out, contradictions = [], []
    for fact, items in by_fact.items():
        values = {json.dumps(i.value, sort_keys=True, default=str).lower() for i in items}
        if len(items) > 1 and len(values) == 1 and len({i.method for i in items}) > 1:
            best = items[0]
            best.confidence, best.note = CONFIRMED, (best.note + " " if best.note else "") + \
                f"agreed by {', '.join(sorted({i.source for i in items}))}"
            out.append(best)
        elif len(items) > 1 and len(values) > 1:
            confirmed = [i for i in items if i.confidence == CONFIRMED]
            out.extend(items)
            if not confirmed or len({json.dumps(i.value, default=str) for i in confirmed}) > 1:
                contradictions.append({"fact": fact, "values": [(i.source, i.value) for i in items]})
        else:
            out.extend(items)
    return out, contradictions


def problems(evidence: list[Evidence]) -> list[str]:
    """Pure logic. What's worth the person's attention, from the evidence."""
    out = []
    for e in evidence:
        if e.fact.endswith(".use_percent") and e.fact.startswith("disk.") and isinstance(e.value, (int, float)) and e.value >= 90:
            out.append(f"Drive {e.fact.split('.')[1]} is {e.value:g}% full.")
        if e.fact == "memory.use_percent" and isinstance(e.value, (int, float)) and e.value >= 90:
            out.append(f"Memory is {e.value:g}% used.")
        if e.fact == "security.firewall" and e.value != "on for every profile":
            out.append(f"The firewall isn't on everywhere ({e.value}).")
        if e.fact == "decisions.waiting" and e.value:
            out.append(f"{len(e.value)} decision{'s' if len(e.value) != 1 else ''} wait on the owner: {', '.join(e.value)}.")
    return out


# ---------------------------------------------------------------- running and keeping reports


def inspect(context, subject: str) -> Report:
    """Every PASSIVE method that applies to `subject` and is available now.
    Methods at higher levels never run from here (they'd be asked first)."""
    if subject not in SUBJECTS:
        raise ValueError(f"I can inspect {', '.join(SUBJECTS.values())} so far.")
    report = Report(subject, _now().isoformat(timespec="seconds"))
    evidence: list[Evidence] = []
    for m in METHODS:
        if subject not in m.subjects:
            continue
        if m.level != PASSIVE:
            report.methods_skipped.append((m.name, f"{m.level}: asked first"))
            continue
        try:
            if not m.available(context):
                report.methods_skipped.append((m.name, f"not available here (needs {m.needs})"))
                continue
            started = time.monotonic()
            found, gaps = m.run(context)
            evidence.extend(found)
            report.gaps.extend(gaps)
            report.methods_run.append((m.name, round(time.monotonic() - started, 2)))
        except Exception as exc:
            log.exception("Inspection method %s failed", m.name)
            report.gaps.append(Gap(m.obtains, f"the {m.name} method failed ({type(exc).__name__})", m.name))
    report.evidence, report.contradictions = correlate(evidence)
    report.problems = problems(report.evidence)
    report.finished_at = _now().isoformat(timespec="seconds")
    save(report)
    return report


def save(report: Report) -> Path:
    _DIR.mkdir(parents=True, exist_ok=True)
    stamp = report.started_at.replace(":", "").replace("-", "")
    path = _DIR / f"{report.subject}-{stamp}.json"
    path.write_text(json.dumps(asdict(report), indent=1, default=str), encoding="utf-8")
    old = sorted(_DIR.glob(f"{report.subject}-*.json"))[:-KEEP]
    for p in old:
        try:
            p.unlink()
        except OSError:
            pass
    return path


def latest(subject: str) -> Optional[dict]:
    files = sorted(_DIR.glob(f"{subject}-*.json")) if _DIR.exists() else []
    try:
        return json.loads(files[-1].read_text(encoding="utf-8")) if files else None
    except (OSError, ValueError):
        return None


def stale(report: dict, now: Optional[datetime] = None) -> list[str]:
    """Pure logic. Facts past their recheck time."""
    now = now or _now()
    out = []
    for e in report.get("evidence") or []:
        try:
            if e.get("recheck_after") and datetime.fromisoformat(e["recheck_after"]) < now:
                out.append(e["fact"])
        except ValueError:
            continue
    return out


# ---------------------------------------------------------------- saying it


_NAMES = {"os.name": "Operating system", "os.release": "Release", "os.version": "Version", "cpu.model": "Processor",
          "cpu.cores_physical": "Cores", "cpu.threads": "Threads", "memory.total_gb": "Memory (GB)",
          "motherboard": "Motherboard", "ai.model": "AI model", "computer.name": "Computer name",
          "code.core_modules": "Core files", "code.desktop_modules": "Desktop modules", "code.test_files": "Test files",
          "capabilities.apps": "Apps",
          "capabilities.tools": "Tools", "decisions.count": "Decisions", "health.open_issues_30d": "Open issues (30 days)"}


def summary(report) -> str:
    """A few plain sentences: what it is, what stands out, what's unknown."""
    r = asdict(report) if isinstance(report, Report) else report
    facts = {e["fact"]: e["value"] for e in r["evidence"]}
    if r["subject"] == "this_computer":
        gpus = [v for k, v in facts.items() if k.startswith("gpu.") and k.endswith(".name")]
        parts = [f"This is {facts.get('computer.name', 'this computer')}, running {facts.get('os.name', '')} "
                 f"{facts.get('os.release', '')}".strip() + "."]
        if facts.get("cpu.model"):
            parts.append(f"Processor: {facts['cpu.model']} ({facts.get('cpu.cores_physical')} cores, "
                         f"{facts.get('cpu.threads')} threads); memory {facts.get('memory.total_gb')} GB.")
        if gpus:
            parts.append("Graphics: " + ", ".join(str(g) for g in gpus) + ".")
        if facts.get("ai.model"):
            parts.append(f"My AI model here is {facts['ai.model']}.")
    else:
        parts = [f"I have {facts.get('capabilities.apps')} apps and {facts.get('capabilities.tools')} tools here, "
                 f"{facts.get('code.core_modules')} core files and {facts.get('code.test_files')} test files; "
                 f"{facts.get('decisions.count')} decisions on record."]
        if facts.get("ai.model"):
            parts.append(f"I'm thinking with {facts['ai.model']}.")
        if facts.get("code.latest_change"):
            parts.append(f"My latest change: {facts['code.latest_change']}.")
    if r["problems"]:
        parts.append("Worth a look: " + " ".join(r["problems"]))
    if r["contradictions"]:
        parts.append(f"{len(r['contradictions'])} thing{'s' if len(r['contradictions']) != 1 else ''} didn't agree "
                     "between sources; I've kept both.")
    if r["gaps"]:
        parts.append("I couldn't determine: " + "; ".join(g["what"] + " (" + g["why"] + ")" for g in r["gaps"][:4]) + ".")
    return " ".join(parts)


def report_text(report) -> str:
    """The whole report, sectioned, each fact with its confidence and source."""
    r = asdict(report) if isinstance(report, Report) else report
    lines = [f"Inspection of {SUBJECTS.get(r['subject'], r['subject'])}, {r['started_at']}", "", summary(r), ""]
    groups: dict[str, list] = {}
    for e in r["evidence"]:
        groups.setdefault(e["fact"].split(".", 1)[0], []).append(e)
    for group, items in groups.items():
        lines.append(group.upper())
        for e in items:
            lines.append(f"  [{e['confidence']}] {_NAMES.get(e['fact'], e['fact'])}: {e['value']}  ({e['source']})")
    if r["gaps"]:
        lines += ["", "UNKNOWN (not determined, which doesn't mean absent)"]
        lines += [f"  {g['what']}: {g['why']}" for g in r["gaps"]]
    if r["methods_skipped"]:
        lines += ["", "NOT RUN"] + [f"  {name}: {why}" for name, why in r["methods_skipped"]]
    return "\n".join(lines)
