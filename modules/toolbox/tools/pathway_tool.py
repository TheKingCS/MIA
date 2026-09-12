"""
modules.toolbox.tools.pathway_tool
=====================================

Pathways — a ToolboxTool (modules/toolbox/tool_base.py) for
core.pathway_manager's Mission Pathways. Single-panel, flat list of
every defined Pathway (no per-skill grouping this pass — a small
enough seed set that it isn't needed yet), each row showing its name,
the skill it trains, and the active profile's real status for it, with
a "Start" button.

format_pathway_row()/format_pathway_status() are free functions (not
methods) — testable without Qt, see tests/test_pathway_tool.py.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.pathway_manager import Pathway, PathwayProgress
from modules.toolbox.tool_base import ToolboxTool


def format_pathway_status(pathway: Pathway, progress: Optional[PathwayProgress]) -> str:
    """Pure formatting logic — testable without Qt. Shows the repeat
    count only for a step that actually has one (repeat_count > 1) —
    "Step 1 of 3 (2/3)" — silent otherwise, matching this codebase's
    "don't decorate a non-event" restraint elsewhere (e.g. Mission's
    abandon_reason "(none)" convention)."""
    if progress is None:
        return "Not started"
    if progress.status == "completed":
        return "Completed"
    base = f"Step {progress.current_step_index + 1} of {len(pathway.steps)}"
    current_step = pathway.steps[progress.current_step_index]
    if current_step.repeat_count > 1:
        base += f" ({progress.current_step_repeats_done}/{current_step.repeat_count})"
    return base


def format_pathway_row(pathway: Pathway, progress: Optional[PathwayProgress]) -> str:
    """Pure formatting logic — testable without Qt."""
    status = format_pathway_status(pathway, progress)
    return f"{pathway.name}  [{pathway.skill_id}]  — {status}"


class PathwayTool(ToolboxTool):
    tool_id = "pathways"
    display_name = "Pathways"
    description = "Guided mission sequences that build out a skill."
    icon = "\U0001F5FA️"  # world map

    def __init__(self, context) -> None:
        super().__init__(context)
        self._pathway_list: Optional[QListWidget] = None

    def build_widget(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("Pathways")
        title.setObjectName("SubtitleLabel")
        layout.addWidget(title)

        self._pathway_list = QListWidget()
        layout.addWidget(self._pathway_list, stretch=1)

        buttons = QHBoxLayout()
        start_button = QPushButton("Start Selected")
        start_button.clicked.connect(self._on_start_pathway)
        buttons.addWidget(start_button)
        layout.addLayout(buttons)

        self._refresh_pathway_list()
        return widget

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def _active_profile_id(self) -> Optional[str]:
        if self.context.profiles is None:
            return None
        active = self.context.profiles.get_active_profile()
        return active.profile_id if active else None

    def _refresh_pathway_list(self) -> None:
        previously_selected = self._selected_pathway_id()
        self._pathway_list.clear()
        if self.context.pathways is None:
            return

        profile_id = self._active_profile_id()
        for pathway in self.context.pathways.all_pathways():
            progress = self.context.pathways.status_for(profile_id, pathway.pathway_id) if profile_id else None
            item = QListWidgetItem(format_pathway_row(pathway, progress))
            item.setData(Qt.ItemDataRole.UserRole, pathway.pathway_id)
            self._pathway_list.addItem(item)

        if previously_selected is not None:
            for row in range(self._pathway_list.count()):
                item = self._pathway_list.item(row)
                if item.data(Qt.ItemDataRole.UserRole) == previously_selected:
                    self._pathway_list.setCurrentItem(item)
                    break

    def _selected_pathway_id(self) -> Optional[str]:
        item = self._pathway_list.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_start_pathway(self) -> None:
        pathway_id = self._selected_pathway_id()
        if pathway_id is None:
            QMessageBox.information(None, "No Pathway Selected", "Select a pathway to start.")
            return

        profile_id = self._active_profile_id()
        if profile_id is None:
            QMessageBox.information(None, "No Active Profile", "Log in to a profile to start a pathway.")
            return

        mission = self.context.pathways.start_pathway(profile_id, pathway_id)
        if mission is None:
            QMessageBox.information(
                None, "Already In Progress", "You already have this pathway in progress — check Missions."
            )
            return

        self._refresh_pathway_list()
