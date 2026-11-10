"""
tools.ci_failures
===================

Says which tests failed in CI where anyone reading the run can see it
(2026-11-10). The Actions job log needs a sign-in, but a check run's
annotations don't, so this reads pytest's JUnit report and prints one
GitHub `::error` annotation per failed test (name and the first lines of
why), up to LIMIT (GitHub keeps 10 error annotations per step), then a
count. Run by `.github/workflows/windows.yml` after the test step fails:

    python -m tools.ci_failures pytest-report.xml
"""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

LIMIT = 10


def failures(report: Path) -> list[tuple[str, str]]:
    """Every failed or errored test in a JUnit report: (classname::name, the first lines of its message)."""
    found = []
    for case in ET.parse(report).getroot().iter("testcase"):
        for kind in ("failure", "error"):
            bad = case.find(kind)
            if bad is not None:
                why = (bad.get("message") or bad.text or "").strip().splitlines()
                found.append((f"{case.get('classname', '')}::{case.get('name', '')}", " | ".join(why[:3])[:400]))
    return found


def _escape(text: str) -> str:
    """A message made safe for a workflow command (its %, CR and LF encoded)."""
    return text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def main(argv: list[str]) -> int:
    """Prints the annotations; 0 always, so it never hides the test step's own failure."""
    report = Path(argv[0] if argv else "pytest-report.xml")
    if not report.is_file():
        print("::warning::No test report to read.")
        return 0
    found = failures(report)
    for name, why in found[:LIMIT]:
        print(f"::error title={_escape(name)[:200]}::{_escape(why)}")
    print(f"::notice::{len(found)} test(s) failed" + (f"; the first {LIMIT} are annotated." if len(found) > LIMIT else "."))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
