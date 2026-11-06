"""No control characters in the source (2026-11-06): a `\\b` in a regex that became a real backspace on its way
through a shell still compiles, and then silently never matches."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ALLOWED = {"\t", "\n", "\r", "\f"}


def test_no_control_characters_in_the_source():
    bad = []
    for folder in ("core", "server", "gui", "modules", "tools", "tests", "web"):
        for path in (ROOT / folder).rglob("*"):
            if path.suffix not in (".py", ".js", ".html", ".css", ".json") or "__pycache__" in path.parts:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            found = sorted({hex(ord(c)) for c in text if ord(c) < 32 and c not in ALLOWED})
            if found:
                bad.append(f"{path.relative_to(ROOT)}: {', '.join(found)}")
    assert not bad, bad
