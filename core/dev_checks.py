"""
core.dev_checks
=================

The development checks that need a real run (build plan step 2, DEC-0094):
the measures behind the loops `dev.suite`, `dev.suite_time`, `dev.reverts`,
`dev.vulnerable` and `dev.outdated` in core/loops.py.

- **The suite on the committed code** (`suite()`): the full test suite in a
  clean copy of the latest commit (the lab's `_base-<commit>` worktree, so
  uncommitted work on this PC never counts), against `work/known_failures.json`:
  each test known to fail, and why. A failure not on that list is unexpected;
  a known one that passes again is stale and should come off it. Once per
  commit: the result is kept for the loops that read it.
- **Reverts per merge** (`reverts()`): from the history, merges Zac approved
  and the ones the lab undid after.
- **Dependencies** (`vulnerable()`, `outdated()`): every installed package
  checked against the OSV database (osv.dev: package names and versions
  only, nothing else leaves the PC), and the packages `requirements.txt`
  names checked against PyPI's latest release.

These are "heavy" loops: they run from Night School and `tools.work loops
--run`, never inside the app's five-minute check. This file is on the lab's
protected list.
"""

from __future__ import annotations

import json
import re
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Optional

ROOT = Path(__file__).resolve().parent.parent
KNOWN = ROOT / "work" / "known_failures.json"
OSV = "https://api.osv.dev/v1/querybatch"
PYPI = "https://pypi.org/pypi/{name}/json"
_SUITES: dict[str, dict] = {}  # commit -> its result, for this process


# ------------------------------------------------------------------ the suite

def known(path: Path = KNOWN) -> dict[str, str]:
    """test id -> why it's known to fail."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {k: str(v.get("why", "")) if isinstance(v, dict) else str(v) for k, v in (data.get("tests") or {}).items()}


def compare(failed: list[str], known_ones: dict[str, str]) -> dict:
    """Pure logic. A suite's failures against the known ones."""
    failed = sorted(set(failed))
    return {"unexpected": [t for t in failed if t not in known_ones],
            "still_known": [t for t in failed if t in known_ones],
            "stale": sorted(t for t in known_ones if t not in failed)}


def _seconds(summary: str) -> Optional[float]:
    """Pure logic. How long a pytest run took, from its summary line, or None."""
    m = re.search(r"in ([\d.]+)s", summary or "")
    return float(m.group(1)) if m else None


def suite(run: Optional[Callable[[Path], dict]] = None, head: Optional[str] = None) -> dict:
    """The full suite on the latest commit, compared with the known failures. Once per commit."""
    from core import dev_lab

    head = head or dev_lab._git("rev-parse", "HEAD")
    if head in _SUITES:
        return _SUITES[head]
    where = dev_lab.LAB_ROOT / f"_base-{head[:10]}"
    if run is None:
        if not where.exists():
            dev_lab.LAB_ROOT.mkdir(parents=True, exist_ok=True)
            dev_lab._git("worktree", "add", "--detach", str(where), head)
        run = dev_lab.run_suite
    started = time.monotonic()
    result = run(where)
    out = {"commit": head[:10], "summary": result.get("summary", ""), "finished": result.get("finished", True),
           "seconds": _seconds(result.get("summary", "")) or round(time.monotonic() - started, 1),
           **compare(result.get("failed") or [], known())}
    _SUITES[head] = out
    return out


# ------------------------------------------------------------------ reverts

def reverts(events: list[dict], days: int = 30, now: Optional[datetime] = None) -> dict:
    """Pure logic. Of Zac's approvals in the last `days`: merges that held, and the ones the lab undid."""
    since = ((now or datetime.now(timezone.utc)) - timedelta(days=days)).isoformat()
    held, undone = [], []
    for e in events:
        if e.get("action") != "approve" or str(e.get("at", "")) < since:
            continue
        detail = str(e.get("detail") or "")
        if detail.startswith("merged"):
            held.append(e.get("task", ""))
        elif detail.startswith("reverted"):
            undone.append(e.get("task", ""))
    merges = len(held) + len(undone)
    return {"merges": merges, "reverts": len(undone), "rate": round(len(undone) / merges, 2) if merges else None,
            "reverted": sorted(set(undone))}


# ------------------------------------------------------------------ dependencies

def _post(url: str, body: dict, timeout: float = 30) -> dict:
    """Posts JSON to a URL and returns the JSON answer."""
    request = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"),
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as answer:
        return json.loads(answer.read())


def _get(url: str, timeout: float = 20) -> dict:
    """Gets a URL's JSON."""
    with urllib.request.urlopen(url, timeout=timeout) as answer:
        return json.loads(answer.read())


def installed() -> dict[str, str]:
    """Every package installed where MIA runs: name -> version."""
    from importlib import metadata

    out = {}
    for d in metadata.distributions():
        name = (d.metadata["Name"] or "").strip()
        if name:
            out[name.lower()] = d.version
    return dict(sorted(out.items()))


PHONE_BUILD = ROOT / "android-phone" / "app" / "build"


def phone_packages(build: Path = PHONE_BUILD) -> dict[str, str]:
    """The Python packages the phone app bundles (Chaquopy installs them into its build): name -> version, read
    from the installed packages' folder names. Empty when the phone app hasn't been built on this PC."""
    out = {}
    for found in build.rglob("*.dist-info") if build.exists() else []:
        name, _, version = found.name[:-len(".dist-info")].rpartition("-")
        if name and version and found.is_dir():
            out[name.lower().replace("_", "-")] = version
    out.pop("pip", None)  # the installer Chaquopy brings, not something the app runs
    return dict(sorted(out.items()))


def vulnerable(packages: Optional[dict[str, str]] = None, post: Callable[[str, dict], dict] = _post) -> dict:
    """Installed packages with a known vulnerability (OSV): {"checked", "packages": {name: [ids]}}."""
    packages = installed() if packages is None else packages
    names = list(packages)
    found: dict[str, list[str]] = {}
    for start in range(0, len(names), 500):  # the batch limit is 1,000
        chunk = names[start:start + 500]
        said = post(OSV, {"queries": [{"package": {"name": n, "ecosystem": "PyPI"}, "version": packages[n]}
                                      for n in chunk]})
        for name, result in zip(chunk, said.get("results") or []):
            ids = [v.get("id", "") for v in (result or {}).get("vulns") or []]
            if ids:
                found[name] = ids
    return {"checked": len(names), "packages": found}


def required(path: Path = ROOT / "requirements.txt") -> list[str]:
    """The packages requirements.txt names (lowercase, comments skipped)."""
    names = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\s*([A-Za-z0-9_.-]+)", line)
        if m and not line.lstrip().startswith("#"):
            names.append(m.group(1).lower())
    return names


def _newer(latest: str, have: str) -> bool:
    """Whether one version is newer than another (by the version rules; by inequality when it can't tell)."""
    try:
        from packaging.version import Version

        return Version(latest) > Version(have)
    except Exception:
        return latest != have


def outdated(names: Optional[list[str]] = None, versions: Optional[dict[str, str]] = None,
             get: Callable[[str], dict] = _get) -> dict:
    """The packages requirements.txt names that have a newer release: {"checked", "behind": {name: (have, latest)}}."""
    names = required() if names is None else names
    versions = installed() if versions is None else versions
    behind, checked = {}, 0
    for name in names:
        have = versions.get(name)
        if not have:
            continue
        try:
            latest = str(get(PYPI.format(name=name)).get("info", {}).get("version", ""))
        except (OSError, ValueError):
            continue
        checked += 1
        if latest and _newer(latest, have):
            behind[name] = (have, latest)
    return {"checked": checked, "behind": behind}
