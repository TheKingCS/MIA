"""
tests.test_web_guide
======================

Start Here (core/web_guide.py) stays true: every "Try saying" phrase
reaches one of MIA's tools (or is one of the few handled in code), every
page it opens exists, and the sidebar's data carries the life areas and
favorites the grouped sidebar draws.
"""

from __future__ import annotations

import logging
from pathlib import Path

from core.web_guide import IN_CODE, NEW, TOPICS, guide

WEB = Path(__file__).resolve().parent.parent / "web"


def test_every_phrase_reaches_a_tool():
    """Each phrase the guide tells you to say attaches at least one of her tools, so trying it does something."""
    from tests.assistant_registry import build_desktop_registry

    logging.disable(logging.CRITICAL)
    try:
        registry = build_desktop_registry()
        silent = [s for t in TOPICS for s in t["say"] if s not in IN_CODE and not registry.matching_actions(s)]
    finally:
        logging.disable(logging.NOTSET)
    assert silent == []


def test_every_page_it_opens_exists():
    """Every topic's and every news item's page is a real web page, and topics have unique ids and some words."""
    pages = {t["page"] for t in TOPICS} | {n["page"] for n in NEW}
    assert all((WEB / page).is_file() for page in pages), [p for p in pages if not (WEB / p).is_file()]
    assert len({t["id"] for t in TOPICS}) == len(TOPICS) and all(t["how"] and t["say"] for t in TOPICS)
    data = guide()
    assert data["topics"][0]["title"] == "Talk to her" and data["new"][0]["page"] == "start.html"


def test_the_sidebar_is_grouped(tmp_path, monkeypatch):
    """The shell gives each app its life area, the areas in order, and the person's favorites."""
    from core.web_surfaces import GROUPS, shell
    from tests.engine_world import build_world

    world = build_world(tmp_path, monkeypatch)
    data = shell(world)
    assert data["groups"] == list(GROUPS) and isinstance(data["favorites"], list)
    browser = next(a for a in data["apps"] if a["id"] == "browser")
    assert browser["group"] in GROUPS
