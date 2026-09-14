"""
tests.test_lite_captures_tool
================================

Unit tests for modules.toolbox.tools.lite_captures_tool's pure
format_capture_card_text(), same style as tests/test_discovery_tool.py
(no Qt event loop, no fixtures).
"""

from __future__ import annotations

from core.lite_capture_manager import CaptureProposal
from modules.toolbox.tools.lite_captures_tool import format_capture_card_text


def _proposal(**overrides) -> CaptureProposal:
    defaults = dict(
        proposal_id="cap1",
        journal_title="Field Note — Sep 14, 2026 2:32 PM",
        transcript="Need to check the mower's oil level before next use.",
    )
    defaults.update(overrides)
    return CaptureProposal(**defaults)


def test_format_capture_card_text_includes_title_and_transcript():
    text = format_capture_card_text(_proposal())

    assert "Field Note — Sep 14, 2026 2:32 PM" in text
    assert "Need to check the mower's oil level before next use." in text
