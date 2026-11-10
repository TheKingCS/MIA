"""
Every program MIA starts is started with no window.

The desktop runs under pythonw, which has no console, so on Windows each
child process started without `creationflags` opens a terminal window of
its own that closes a moment later (a check that runs git a hundred times
flashes a hundred of them). This reads the code, it starts nothing: every
`subprocess.run/Popen/...` call in MIA's own packages must pass
`creationflags` (CREATE_NO_WINDOW, or `dev_lab.quiet_job_flags()` for a job
that outlives her).
"""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGES = ("core", "server", "gui", "modules")
STARTERS = {"run", "Popen", "check_output", "call", "check_call"}


def _calls_without_flags() -> list[str]:
    """`file:line` for each subprocess call in MIA's packages that doesn't say how its window is handled."""
    found = []
    for package in PACKAGES:
        for path in sorted((ROOT / package).rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                if not (isinstance(func, ast.Attribute) and func.attr in STARTERS
                        and isinstance(func.value, ast.Name) and func.value.id == "subprocess"):
                    continue
                keywords = {keyword.arg for keyword in node.keywords}
                if "creationflags" not in keywords and None not in keywords:  # None: **kwargs, decided by the caller
                    found.append(f"{path.relative_to(ROOT).as_posix()}:{node.lineno}")
    return found


def test_every_program_mia_starts_is_started_with_no_window():
    assert _calls_without_flags() == [], "pass creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)"
