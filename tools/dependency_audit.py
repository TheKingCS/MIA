"""
tools.dependency_audit
========================

Known vulnerabilities in the packages MIA runs on (docs/SECURITY.md step 5). Lists every Python package installed
where MIA runs (name and version) and asks OSV (https://osv.dev, the open vulnerability database Google runs; the
same data pip-audit uses) which have published advisories, then says each one plainly with the version that fixes it.
Only package names and versions are sent: nothing about the person.

    python -m tools.dependency_audit           # the findings, one per line; exit code 1 when there are any
    python -m tools.dependency_audit --json    # the same as JSON
    python -m tools.dependency_audit --save    # saved for MIA's weekly check (core/dependency_audit.py)

`findings()` is pure logic over OSV's answer, so it's tested without the network.
"""

from __future__ import annotations

import json
import sys
import urllib.request
from importlib import metadata
from typing import Optional

OSV_BATCH = "https://api.osv.dev/v1/querybatch"
OSV_VULN = "https://api.osv.dev/v1/vulns/"
TIMEOUT = 30


def installed() -> list[tuple[str, str]]:
    """Every installed Python package as (name, version), sorted, each once."""
    seen = {}
    for dist in metadata.distributions():
        name = (dist.metadata.get("Name") or "").strip()
        if name and name.lower() not in seen:
            seen[name.lower()] = (name, dist.version)
    return sorted(seen.values(), key=lambda p: p[0].lower())


def _post(url: str, body: dict) -> dict:
    """A JSON POST to OSV."""
    request = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"),
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return json.loads(response.read().decode("utf-8"))


def _get(url: str) -> dict:
    """A JSON GET from OSV."""
    with urllib.request.urlopen(url, timeout=TIMEOUT) as response:
        return json.loads(response.read().decode("utf-8"))


def fixed_in(vuln: dict, package: str) -> str:
    """Pure logic. The lowest version an advisory says fixes it for this package, or "" when none is published."""
    versions = []
    for affected in vuln.get("affected", []):
        if (affected.get("package", {}).get("name") or "").lower() != package.lower():
            continue
        for rng in affected.get("ranges", []):
            versions += [e["fixed"] for e in rng.get("events", []) if "fixed" in e]
    return versions[0] if versions else ""


def findings(packages: list[tuple[str, str]], batch: dict, details: dict) -> list[dict]:
    """Pure logic. One finding per package and advisory from OSV's batch answer (in the packages' order) and each
    advisory's details: the package, its version, the advisory's id, a one-line summary and the fixing version."""
    out = []
    for (name, version), result in zip(packages, batch.get("results", [])):
        for vuln in result.get("vulns", []) or []:
            info = details.get(vuln["id"], {})
            out.append({"package": name, "version": version, "id": vuln["id"],
                        "summary": (info.get("summary") or info.get("details") or "").split("\n")[0][:160],
                        "fixed_in": fixed_in(info, name)})
    return out


def audit(packages: Optional[list[tuple[str, str]]] = None) -> list[dict]:
    """Asks OSV about the packages (the installed ones by default) and returns the findings."""
    packages = packages or installed()
    queries = [{"package": {"name": n, "ecosystem": "PyPI"}, "version": v} for n, v in packages]
    batch = _post(OSV_BATCH, {"queries": queries})
    ids = {v["id"] for r in batch.get("results", []) for v in (r.get("vulns") or [])}
    details = {i: _get(OSV_VULN + i) for i in sorted(ids)}
    return findings(packages, batch, details)


def main(argv: Optional[list] = None) -> int:
    """Prints the findings; exit code 1 when there are any, 2 when OSV couldn't be reached."""
    args = argv if argv is not None else sys.argv[1:]
    as_json = "--json" in args
    try:
        found = audit()
    except OSError as problem:
        print(f"Couldn't reach OSV ({problem}); nothing checked.")
        return 2
    if "--save" in args:
        from core import dependency_audit

        dependency_audit.save(found)
    if as_json:
        print(json.dumps(found, indent=1))
    elif not found:
        print(f"No known vulnerabilities in {len(installed())} packages.")
    else:
        for f in found:
            fix = f"; fixed in {f['fixed_in']}" if f["fixed_in"] else "; no fixed version yet"
            print(f"{f['package']} {f['version']}: {f['id']}: {f['summary']}{fix}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
