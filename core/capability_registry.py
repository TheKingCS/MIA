"""
core.capability_registry
==========================

The capability truth registry (WP-08, DEC-0220, REQ-SLF-003/004/005; docs/mia_os/MIA_OS_CAPABILITY_TRUTH_REGISTRY.md
and MIA_OS_CAPABILITY_STATE_MODEL.md). One record per capability (each app), joining what's said about it elsewhere:

- **owner, needs, operations, devices**: the app's manifest (apps/<id>/manifest.json, core/app_registry.py): its
  services, permissions, tools and action kinds, and the devices it runs on (with the parity decisions,
  work/parity.json);
- **verification**: the tests that cover it (a test file named after it, or naming one of its tools or action
  kinds), counted and named;
- **last success, last failure**: the turn traces (the last turn that used one of its tools) and the Fix-It Log (the
  last tool error or page error of its own);
- **limits**: core/capabilities.LIMITS;
- **state** (`STATES`), decided in code from that evidence and nothing else (`_decide`), with each piece of evidence
  cited and a confidence from how direct it is.

**Derived, never edited (REQ-SLF-004).** `records()` builds every record from its sources each time it's asked. The only
thing kept is what each state was last time, so a change can be told with its evidence (`rebuild()`, REQ-SLF-005):
capability_states.json on this device, written by `rebuild()` alone. No tool, action or page writes a state, and
nothing a model says changes one (a test checks there's no other write path).
"""

from __future__ import annotations

from core.data_root import DATA_DIR

import json
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from core.atomic_write import atomic_write_text
from core.logger import get_logger

log = get_logger(__name__)

_DATA_DIR = DATA_DIR
FILE_NAME = "capability_states.json"
TESTS_DIR = Path(__file__).resolve().parent.parent / "tests"
STATES = ("working", "partial", "degraded", "unavailable here", "malfunctioning", "unverified", "planned", "retired")
RECENT_DAYS = 30  # a use or a test this recent verifies a capability
FAILED_DAYS = 7  # a failure this recent, with no success since, is malfunctioning
KEEP_CHANGES = 500
DEVICES = ("pc", "phone", "glasses", "voice")

_lock = threading.Lock()
_tests_cache: dict = {}


def _now() -> datetime:
    """The time now, with its zone (UTC)."""
    return datetime.now(timezone.utc)


def _when(text: str) -> Optional[datetime]:
    """An ISO time as an aware datetime (UTC assumed without a zone); None when it won't read."""
    try:
        found = datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    except ValueError:
        return None
    return found if found.tzinfo else found.replace(tzinfo=timezone.utc)


def _tests_index() -> dict:
    """Each test file's name and text (cached until a test file changes): {name: text}."""
    try:
        files = sorted(TESTS_DIR.glob("test_*.py"))
        stamp = (len(files), max((f.stat().st_mtime for f in files), default=0.0))
    except OSError:
        return {}
    with _lock:
        if _tests_cache.get("stamp") != stamp:
            texts = {}
            for f in files:
                try:
                    texts[f.name] = f.read_text(encoding="utf-8")
                except OSError:
                    continue
            _tests_cache.update(stamp=stamp, texts=texts)
        return dict(_tests_cache["texts"])


def covering_tests(app_id: str, operations: list[str], index: Optional[dict] = None) -> list[str]:
    """Pure logic over the test files. The tests that cover a capability: the file named exactly after it, or one that
    names one of its tools or action kinds (in quotes, as tests call them). Never a file whose name only starts like
    it (test_home_link.py isn't the home app's)."""
    index = _tests_index() if index is None else index
    names = [f'"{op}"' for op in operations if op]
    out = []
    for name, text in index.items():
        if name in (f"test_{app_id}.py", f"test_{app_id}") or any(n in text for n in names):
            out.append(name)
    return sorted(out)


def _manifests() -> dict:
    """Every app's manifest, retired ones too ({} when the registry won't load)."""
    try:
        from core import app_registry

        return dict(app_registry.load().manifests)
    except Exception:  # noqa: BLE001 - no manifests: no records
        log.exception("The capability registry couldn't read the app manifests.")
        return {}


def _devices(manifest: dict, gaps: dict, app_id: str) -> dict:
    """Pure logic. Each device: how the manifest says it runs there, and a parity gap decided for it ("todo" said as
    planned, "none" as not there by design)."""
    runs = ((manifest.get("runtime") or {}).get("devices") or {})
    out = {}
    for device in DEVICES:
        gap = gaps.get(f"{app_id}:{device}") or {}
        if gap.get("status") == "todo":
            out[device] = "planned"
        elif gap.get("status") == "none":
            out[device] = "not there"
        else:
            value = runs.get(device)
            out[device] = ("yes" if value is True else "no" if value is False else str(value)) if value is not None else "yes"
    return out


def _read_use(context, days: int) -> tuple[list, list]:
    """The turn traces and the Fix-It Log's events of the last `days` days, read once for every capability."""
    traces = getattr(context, "traces", None)
    book = getattr(context, "failures", None)
    try:
        recent = list(traces.recent(2000)) if traces is not None else []
    except Exception:  # noqa: BLE001 - traces that won't read say nothing
        recent = []
    try:
        events = list(book.events(days=days)) if book is not None else []
    except Exception:  # noqa: BLE001 - a log that won't read says nothing
        events = []
    return recent, events


def _use(context, operations: set, days: int, read: Optional[tuple] = None) -> tuple[Optional[str], Optional[str]]:
    """(the last turn that used one of these tools, the last tool error of one of them) in the last `days` days, from
    the turn traces and the Fix-It Log (`read`: both as `_read_use` gave them, so they're read once); None for either
    that isn't there."""
    since = _now() - timedelta(days=days)
    used = failed = None
    recent, events = read if read is not None else _read_use(context, days)
    try:
        for t in recent:
            if operations & set(t.get("tools_called") or []):
                at = _when(t.get("at", ""))
                if at and at >= since and (used is None or t["at"] > used):
                    used = t["at"]
    except Exception:  # noqa: BLE001 - traces that won't read say nothing
        used = None
    try:
        for e in events:
            at = _when(e.get("at", ""))
            if (e.get("kind") == "tool_error" and e.get("tool") in operations and at and at >= since
                    and (failed is None or e.get("at", "") > failed)):
                failed = e.get("at")
    except Exception:  # noqa: BLE001 - a log that won't read says nothing
        failed = None
    return used, failed


def _offline() -> bool:
    """Whether answers in words aren't ready now (the model server doesn't answer: core/orb_state.py's `offline`)."""
    try:
        from core import orb_state

        return orb_state.held("offline")
    except Exception:  # noqa: BLE001
        return False


def _recovered(used: Optional[str], failed: str) -> bool:
    """Pure logic. Whether a use came after a failure, rather than being the very turn that failed (a turn's trace is
    written just after its failure, with the failing tool among those it called): a use more than two minutes later."""
    a, b = _when(used or ""), _when(failed)
    return bool(a and b and (a - b).total_seconds() > 120)


def _decide(status: dict, tests: list, used: Optional[str], failed: Optional[str], has_tools: bool,
            offline: bool) -> tuple[str, list[str], str]:
    """Pure logic. A capability's state from its evidence (the state model): (state, the evidence cited, confidence).
    The app status (core/capabilities.capability_status) gives partial, unavailable here, malfunctioning and planned;
    a tool failure in the last FAILED_DAYS with no use since is malfunctioning (a use counts only from two
    minutes after the failure, so the failing turn's own trace isn't a recovery: `_recovered`); with the model offline, one used by words is
    degraded (its screens still work); built but with no test covering it and no use lately, unverified."""
    said = status.get("status", "implemented")
    evidence = [f"app status: {said} ({status.get('why', '')})"]
    if tests:
        evidence.append(f"{len(tests)} test file{'s' if len(tests) != 1 else ''} cover it")
    if used:
        evidence.append(f"used by MIA on {used[:10]}")
    if failed:
        evidence.append(f"a tool failed on {str(failed)[:10]}")
    if said == "malfunctioning" or (failed and not _recovered(used, str(failed))):
        return "malfunctioning", evidence, "inferred"
    if said in ("unavailable here", "planned"):
        return said, evidence, "verified"
    if offline and has_tools:
        return "degraded", evidence + ["the model server doesn't answer: asking in words waits, its screens work"], "verified"
    if said == "partial":
        return "partial", evidence, "verified"
    if not tests and not used:
        return "unverified", evidence + [f"no test covers it and no use in {RECENT_DAYS} days"], "low"
    return "working", evidence, "verified" if tests and used else "medium"


def records(context=None, here: str = "pc") -> list[dict]:
    """Every capability's record, built now from its sources (never from a kept copy): {id, name, owner, needs:
    {services, permissions}, operations: {tools, actions}, devices, state, evidence, confidence, verification: {tests},
    last_success, last_failure, limits}; the turn traces and tool failures are read once for all of them (`_read_use`). Retired apps are kept as
    retired; a planned piece (a parity gap to do) is a
    record of its own."""
    from core import capabilities

    manifests = _manifests()
    gaps = capabilities._parity_gaps()
    statuses = {r["id"]: r for r in capabilities.capability_status(context, here)}
    index = _tests_index()
    offline = _offline()
    read = _read_use(context, max(RECENT_DAYS, FAILED_DAYS))  # once, not twice for every app
    out = []
    for app_id, m in sorted(manifests.items()):
        caps = m.get("capabilities") or {}
        tools, actions = list(caps.get("tools") or []), list(caps.get("actions") or [])
        record = {"id": app_id, "name": m.get("name", app_id), "owner": app_id,
                  "needs": {"services": list((m.get("components") or {}).get("services") or []),
                            "permissions": list(m.get("permissions") or [])},
                  "operations": {"tools": tools, "actions": actions},
                  "devices": _devices(m, gaps, app_id), "limits": capabilities.LIMITS.get(app_id, "")}
        if m.get("retired"):
            out.append({**record, "state": "retired", "evidence": ["its manifest says retired"], "confidence": "verified",
                        "verification": {"tests": []}, "last_success": None, "last_failure": None})
            continue
        tests = covering_tests(app_id, tools + actions, index)
        used, _ = _use(context, set(tools), RECENT_DAYS, read)
        _, failed = _use(context, set(tools), FAILED_DAYS, read)  # a failure counts for a week (FAILED_DAYS)
        state, evidence, confidence = _decide(statuses.get(app_id, {}), tests, used, failed, bool(tools), offline)
        out.append({**record, "state": state, "evidence": evidence, "confidence": confidence,
                    "verification": {"tests": tests}, "last_success": used, "last_failure": failed})
    for row in statuses.values():
        if row["status"] == "planned":
            out.append({"id": row["id"], "name": row["name"], "owner": row["id"].split(":", 1)[0], "needs": {},
                        "operations": {}, "devices": {}, "limits": "", "state": "planned",
                        "evidence": [f"a parity gap decided as to do ({row.get('why', '')})"], "confidence": "verified",
                        "verification": {"tests": []}, "last_success": None, "last_failure": None})
    return out


def _file() -> Path:
    """Where the last states are kept (this device's data folder)."""
    return Path(_DATA_DIR) / FILE_NAME


def _kept() -> dict:
    """The kept states and changes: {states: {id: state}, changes: [...]}; empty when there's none or it won't read."""
    try:
        raw = json.loads(_file().read_text(encoding="utf-8"))
        return {"states": dict(raw.get("states") or {}), "changes": list(raw.get("changes") or [])}
    except (OSError, ValueError, AttributeError):
        return {"states": {}, "changes": []}


def rebuild(context=None, here: str = "pc") -> dict:
    """Builds every record from its sources, and for each whose state differs from the last rebuild, notes the change
    with the evidence that caused it (REQ-SLF-005). Returns {records, changes (this rebuild's)}. The first rebuild
    notes no changes (there's nothing to differ from); the file is written only when a state changed. Never raises for
    a file it can't write (logged)."""
    built = records(context, here)
    with _lock:
        kept = _kept()
        first = not kept["states"]
        at = _now().isoformat(timespec="seconds")
        changes = [] if first else [
            {"at": at, "id": r["id"], "from": kept["states"].get(r["id"], "new"), "to": r["state"],
             "because": r["evidence"]}
            for r in built if kept["states"].get(r["id"]) != r["state"]]
        if first or changes:  # written only on a change: each write moves the live version, and pages re-read
            try:
                atomic_write_text(_file(), json.dumps({"states": {r["id"]: r["state"] for r in built},
                                                       "changes": (kept["changes"] + changes)[-KEEP_CHANGES:]}, indent=1))
            except OSError:
                log.exception("Couldn't keep the capability states.")
    return {"records": built, "changes": changes}


def changes(limit: int = 50) -> list[dict]:
    """The latest state changes, newest first, each with its evidence."""
    return list(reversed(_kept()["changes"]))[:limit]


def summary(context=None, here: str = "pc") -> dict:
    """For the Diagnostics page: the records rebuilt now, counted by state; those not working, each with its evidence;
    and the latest changes."""
    built = rebuild(context, here)["records"]
    counts = {s: sum(r["state"] == s for r in built) for s in STATES}
    notable = [{"id": r["id"], "name": r["name"], "state": r["state"], "evidence": r["evidence"]}
               for r in built if r["state"] not in ("working", "retired")]
    return {"counts": counts, "notable": notable, "changes": changes(10)}
