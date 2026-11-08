"""
tests.test_no_control_characters
==================================

No stray control characters in MIA's code or docs. A shell heredoc turns a
regex's \\b into a backspace byte, and the pattern then silently matches
nothing (it happened in 2026-11 twice: the turn traces' patterns, and the
check that keeps passwords out of what MIA remembers by voice).
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FOLDERS = ("core", "server", "web", "gui", "modules", "tools", "tests", "docs")
ALLOWED = {9, 10, 13}  # tab, newline, carriage return


def test_code_and_docs_hold_no_control_characters():
    """Every .py, .js, .html, .css and .md file under MIA's own folders."""
    bad = []
    for folder in FOLDERS:
        for path in (ROOT / folder).rglob("*"):
            if path.suffix not in (".py", ".js", ".html", ".css", ".md") or "__pycache__" in path.parts:
                continue
            data = path.read_bytes()
            if any(b < 32 and b not in ALLOWED for b in data):
                bad.append(str(path.relative_to(ROOT)))
    assert not bad, f"control characters (a heredoc's \\b?) in: {bad}"
