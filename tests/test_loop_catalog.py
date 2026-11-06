"""docs/LOOPS.md is the code's own list of MIA's loops (core/loop_catalog.py): generated, kept current by this test."""

from pathlib import Path

from core import loop_catalog
from core.loops import LOOPS


def test_the_list_is_current():
    kept = (Path(loop_catalog.ROOT) / "docs" / "LOOPS.md").read_text(encoding="utf-8")
    assert kept == loop_catalog.render(), "docs/LOOPS.md is out of date: python -m core.loop_catalog"


def test_every_loop_is_listed_once():
    text = loop_catalog.render()
    assert all(text.count(f"| `{loop.id}` |") == 1 for loop in LOOPS)
