"""
tests.test_intent_tool
=========================

Unit tests for modules.toolbox.tools.intent_tool's pure functions,
same style as tests/test_project_tool.py (no Qt event loop, no
fixtures).
"""

from __future__ import annotations

from core.intent_manager import Intent
from modules.toolbox.tools.intent_tool import format_intent_row


def test_format_intent_row_not_primary():
    intent = Intent(intent_id="i1", name="Homestead Independence", status="Active", primary=False)
    assert format_intent_row(intent) == "Homestead Independence  (Active)"


def test_format_intent_row_primary():
    intent = Intent(intent_id="i1", name="Homestead Independence", status="Active", primary=True)
    assert format_intent_row(intent) == "Homestead Independence  (Active)  ★ Current Focus"


def test_format_intent_row_paused():
    intent = Intent(intent_id="i1", name="X", status="Paused")
    assert format_intent_row(intent) == "X  (Paused)"
