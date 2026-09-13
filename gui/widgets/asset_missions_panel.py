"""
gui.widgets.asset_missions_panel
===================================

build_asset_missions_panel() — the one shared "Related Missions" list
embedded by every real per-area module that owns a slice of
core.maintenance_manager.MaintenanceAsset (Real Estate, Garage,
Greenhouse). Built once here rather than re-implemented per module —
2026-09-13, at the user's own explicit request for real parity across
areas ("the garage, the homes, the greenhouse are like bosses with all
these missions fighting to keep it in good standing").

Reuses gui/widgets/mission_list_row.py's existing MissionListRow
verbatim (same clickable-row look the Mission Log's own list already
uses) rather than inventing a second "clickable mission row" style.
Clicking a row opens the Missions module with that exact Mission
selected via the new cross-module `record_id` mechanism
(gui/main_window.py's open_module()/ModuleBase.focus_record()) — the
same one mechanism every area's "click through to a mission" action
goes through.
"""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from core.app_context import AppContext
from gui.widgets.mission_list_row import MissionListRow


def build_asset_missions_panel(context: AppContext, asset_id: str) -> QWidget:
    panel = QWidget()
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(6)

    title = QLabel("Related Missions")
    title.setObjectName("SubtitleLabel")
    layout.addWidget(title)

    missions = context.missions.missions_for_maintenance_asset(asset_id) if context.missions is not None else []
    if not missions:
        empty = QLabel("No missions tagged to this yet.")
        empty.setObjectName("SubtitleLabel")
        layout.addWidget(empty)
        return panel

    for mission in missions:
        row = MissionListRow(mission.mission_id, mission.icon, mission.name, completed=mission.status == "completed")
        row.activated.connect(
            lambda mission_id: context.events.publish(
                "assistant.open_module_requested", module_id="missions", record_id=mission_id,
            )
        )
        layout.addWidget(row)

    return panel
