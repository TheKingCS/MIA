"""
tests.test_project_tool
==========================

Unit tests for modules.toolbox.tools.project_tool's pure functions,
same style as tests/test_expeditions_module.py (no Qt event loop, no
fixtures).
"""

from __future__ import annotations

from core.project_manager import Project
from core.task_manager import Task
from modules.toolbox.tools.project_tool import format_project_row, format_task_row


def test_format_project_row_with_due_date():
    project = Project(project_id="p1", name="Garage Rewire", status="Active", due_date="2026-08-14")
    assert format_project_row(project) == "Garage Rewire  (Active)  [due 2026-08-14]"


def test_format_project_row_no_due_date():
    project = Project(project_id="p1", name="Someday Project", status="Planning")
    assert format_project_row(project) == "Someday Project  (Planning)"


def test_format_task_row_not_done_with_due_date():
    task = Task(task_id="t1", project_id="p1", title="Buy fuse box", due_date="2026-08-14")
    assert format_task_row(task) == "[ ] Buy fuse box  (due 2026-08-14)"


def test_format_task_row_done_no_due_date():
    task = Task(task_id="t1", project_id="p1", title="Buy fuse box", done=True)
    assert format_task_row(task) == "[x] Buy fuse box"
