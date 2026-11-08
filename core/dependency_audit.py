"""
core.dependency_audit
=======================

The weekly check for known vulnerabilities in the packages MIA runs on (docs/SECURITY.md step 5). The check itself is
tools/dependency_audit.py (it asks OSV over the internet, a few seconds' work); this is the part MIA's daily checks
use: whether a check is `due` (none in the last CHECK_DAYS), `launch` it in a process of its own with no window, and
`offer`, from the saved result, what to tell the person: each package with an advisory and the version that fixes
it. That message goes through the communication gate like any other unprompted one, once per set of findings.

The result lives in data/dev/dependency_audit.json (`DEV_DATA`): package names, versions and advisory ids, nothing
about the person.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
DEV_DATA = ROOT / "data" / "dev"
CHECK_DAYS = 7


def result_file() -> Path:
    """Where the last check's result is saved."""
    return DEV_DATA / "dependency_audit.json"


def last_result() -> Optional[dict]:
    """The last check's result ({"checked": iso, "findings": [...]}), or None when there's none or it doesn't read."""
    try:
        return json.loads(result_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def save(findings: list[dict], now: Optional[datetime] = None) -> None:
    """Saves a check's findings with when it ran."""
    DEV_DATA.mkdir(parents=True, exist_ok=True)
    result_file().write_text(json.dumps({"checked": (now or datetime.now()).isoformat(timespec="seconds"),
                                         "findings": findings}, indent=1), encoding="utf-8")


def due(now: datetime) -> bool:
    """Whether a check is due: none saved, or the last one older than CHECK_DAYS."""
    result = last_result()
    try:
        return result is None or now - datetime.fromisoformat(result["checked"]) > timedelta(days=CHECK_DAYS)
    except (KeyError, ValueError):
        return True


def launch() -> None:
    """Runs the check in a process of its own with no window (core.dev_lab.quiet_job_flags); never from a test."""
    import os
    import subprocess

    if os.environ.get("PYTEST_CURRENT_TEST"):
        return
    from core.dev_lab import _python, quiet_job_flags

    subprocess.Popen([_python(), "-m", "tools.dependency_audit", "--save"], cwd=str(ROOT), stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=quiet_job_flags())


def offer(result: Optional[dict]) -> Optional[tuple[str, str, str]]:
    """Pure logic. What to tell the person about a check's findings: (title, message, fingerprint), or None when there
    are none. The fingerprint is the advisories' ids, so the same findings are said once."""
    found = (result or {}).get("findings") or []
    if not found:
        return None
    lines = [f"{f['package']} {f['version']} ({f['id']})" + (f": update to {f['fixed_in']}" if f.get("fixed_in") else "")
             for f in found[:6]]
    more = f" and {len(found) - 6} more" if len(found) > 6 else ""
    message = ("A package MIA runs on has a known security problem: " if len(found) == 1 else
               f"{len(found)} known security problems in packages MIA runs on: ") + "; ".join(lines) + more + \
              ". Ask Claude to update them (pip install --upgrade), then run the tests."
    return "Security updates for MIA", message, "dependency_audit:" + ",".join(sorted(f["id"] for f in found))
