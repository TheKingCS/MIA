"""
tests.test_pathway_tool
==========================

Unit tests for modules.toolbox.tools.pathway_tool's pure functions,
same style as tests/test_intent_tool.py (no Qt event loop, no
fixtures).
"""

from __future__ import annotations

from core.pathway_manager import Pathway, PathwayProgress, PathwayStep
from modules.toolbox.tools.pathway_tool import format_pathway_row, format_pathway_status


def _pathway(steps=2):
    return Pathway(
        pathway_id="p1", skill_id="carpentry", name="Test Pathway",
        steps=[PathwayStep(name=f"Step {i}") for i in range(steps)],
    )


def test_format_pathway_status_not_started():
    assert format_pathway_status(_pathway(), None) == "Not started"


def test_format_pathway_status_in_progress():
    progress = PathwayProgress(profile_id="p1", pathway_id="p1", current_step_index=1, status="active")
    assert format_pathway_status(_pathway(steps=3), progress) == "Step 2 of 3"


def test_format_pathway_status_completed():
    progress = PathwayProgress(profile_id="p1", pathway_id="p1", status="completed")
    assert format_pathway_status(_pathway(), progress) == "Completed"


def test_format_pathway_status_shows_repeat_progress_when_step_has_one():
    pathway = Pathway(
        pathway_id="p1", skill_id="cooking", name="Test Pathway",
        steps=[PathwayStep(name="Cook a New Recipe", repeat_count=3), PathwayStep(name="Step Two")],
    )
    progress = PathwayProgress(
        profile_id="p1", pathway_id="p1", current_step_index=0, current_step_repeats_done=1, status="active",
    )
    assert format_pathway_status(pathway, progress) == "Step 1 of 2 (1/3)"


def test_format_pathway_status_omits_repeat_progress_when_repeat_count_is_one():
    progress = PathwayProgress(profile_id="p1", pathway_id="p1", current_step_index=0, status="active")
    assert format_pathway_status(_pathway(steps=2), progress) == "Step 1 of 2"


def test_format_pathway_row_not_started():
    assert format_pathway_row(_pathway(), None) == "Test Pathway  [carpentry]  — Not started"


def test_format_pathway_row_in_progress():
    progress = PathwayProgress(profile_id="p1", pathway_id="p1", current_step_index=0, status="active")
    assert format_pathway_row(_pathway(steps=3), progress) == "Test Pathway  [carpentry]  — Step 1 of 3"
