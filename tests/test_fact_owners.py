"""One owner per fact (DEC-0052): a retired copy of a fact never comes
back, and every owner named in core/fact_owners.py exists."""

from pathlib import Path

from core.fact_owners import OWNERS, RETIRED

ROOT = Path(__file__).resolve().parent.parent
SEARCHED = ("core", "modules", "gui", "server", "web")


def test_no_retired_copy_comes_back():
    """Read the fact from its owner (core/fact_owners.OWNERS) instead of
    keeping a copy. The listed files may still name it: the one-time move."""
    found = []
    for folder in SEARCHED:
        for path in (ROOT / folder).rglob("*"):
            if path.suffix not in (".py", ".js", ".html") or "__pycache__" in path.parts:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            rel = path.relative_to(ROOT).as_posix()
            found += [(key, rel) for key, allowed in RETIRED.items() if key in text and rel not in allowed]
    assert found == []


def test_every_owner_is_real():
    assert all((ROOT / o.store).exists() for o in OWNERS)
