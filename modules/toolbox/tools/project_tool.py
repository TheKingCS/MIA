"""
modules.toolbox.tools.project_tool
=====================================

Project Manager — a ToolboxTool (modules/toolbox/tool_base.py), the
v1.0+-bucket "Project Manager" slice from docs/ROADMAP.md, buildable
with zero real hardware. Two-level CRUD, same shape as
modules/expeditions/module.py: Projects (core.project_manager.Project)
at the top, and the selected Project's Tasks (core.task_manager.Task)
below it, with a "Toggle Done" button instead of a separate detail
dialog — a task has no sub-structure worth a whole screen the way a
Trip's route/gear/journal does.

format_project_row()/format_task_row() are free functions (not
methods) — testable without Qt, see tests/test_project_tool.py.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.project_manager import Project
from core.task_manager import Task
from gui.add_edit_project_dialog import AddEditProjectDialog
from gui.add_edit_task_dialog import AddEditTaskDialog
from gui.delete_confirm_dialog import DeleteConfirmDialog
from gui.manage_project_skills_dialog import ManageProjectSkillsDialog
from modules.toolbox.tool_base import ToolboxTool


def format_project_row(project: Project) -> str:
    """Pure formatting logic — testable without Qt (see tests/test_project_tool.py)."""
    due = f"  [due {project.due_date}]" if project.due_date else ""
    return f"{project.name}  ({project.status}){due}"


def format_task_row(task: Task) -> str:
    """Pure formatting logic — testable without Qt (see tests/test_project_tool.py)."""
    mark = "[x]" if task.done else "[ ]"
    due = f"  (due {task.due_date})" if task.due_date else ""
    return f"{mark} {task.title}{due}"


class ProjectTool(ToolboxTool):
    tool_id = "projects"
    display_name = "Project Manager"
    description = "Track projects and their tasks."
    icon = "🗂️"  # card index dividers

    def __init__(self, context) -> None:
        super().__init__(context)
        self._project_list: Optional[QListWidget] = None
        self._task_list: Optional[QListWidget] = None

    def build_widget(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        project_title = QLabel("Projects")
        project_title.setObjectName("SubtitleLabel")
        layout.addWidget(project_title)

        self._project_list = QListWidget()
        self._project_list.currentItemChanged.connect(self._on_project_selected)
        layout.addWidget(self._project_list, stretch=1)

        project_buttons = QHBoxLayout()
        add_project_button = QPushButton("Add Project")
        add_project_button.clicked.connect(self._on_add_project)
        project_buttons.addWidget(add_project_button)

        edit_project_button = QPushButton("Edit Selected")
        edit_project_button.clicked.connect(self._on_edit_project)
        project_buttons.addWidget(edit_project_button)

        delete_project_button = QPushButton("Delete Selected")
        delete_project_button.clicked.connect(self._on_delete_project)
        project_buttons.addWidget(delete_project_button)

        manage_skills_button = QPushButton("Manage Skills")
        manage_skills_button.clicked.connect(self._on_manage_skills)
        project_buttons.addWidget(manage_skills_button)
        layout.addLayout(project_buttons)

        task_title = QLabel("Tasks in selected Project")
        task_title.setObjectName("SubtitleLabel")
        layout.addWidget(task_title)

        self._task_list = QListWidget()
        layout.addWidget(self._task_list, stretch=1)

        task_buttons = QHBoxLayout()
        add_task_button = QPushButton("Add Task")
        add_task_button.clicked.connect(self._on_add_task)
        task_buttons.addWidget(add_task_button)

        edit_task_button = QPushButton("Edit Selected")
        edit_task_button.clicked.connect(self._on_edit_task)
        task_buttons.addWidget(edit_task_button)

        toggle_task_button = QPushButton("Toggle Done")
        toggle_task_button.clicked.connect(self._on_toggle_task)
        task_buttons.addWidget(toggle_task_button)

        delete_task_button = QPushButton("Delete Selected")
        delete_task_button.clicked.connect(self._on_delete_task)
        task_buttons.addWidget(delete_task_button)
        layout.addLayout(task_buttons)

        self._refresh_project_list()
        return widget

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def _refresh_project_list(self) -> None:
        previously_selected = self._selected_project_id()

        self._project_list.clear()
        for project in self.context.projects.all_projects():
            item = QListWidgetItem(format_project_row(project))
            item.setData(Qt.ItemDataRole.UserRole, project.project_id)
            self._project_list.addItem(item)

        if previously_selected is not None:
            for row in range(self._project_list.count()):
                item = self._project_list.item(row)
                if item.data(Qt.ItemDataRole.UserRole) == previously_selected:
                    self._project_list.setCurrentItem(item)
                    break
        self._refresh_task_list()

    def _refresh_task_list(self) -> None:
        self._task_list.clear()
        project_id = self._selected_project_id()
        if project_id is None:
            return
        for task in self.context.tasks.tasks_for_project(project_id):
            item = QListWidgetItem(format_task_row(task))
            item.setData(Qt.ItemDataRole.UserRole, task.task_id)
            self._task_list.addItem(item)

    def _on_project_selected(self) -> None:
        self._refresh_task_list()

    # ------------------------------------------------------------------
    # Selection helpers
    # ------------------------------------------------------------------

    def _selected_project_id(self) -> Optional[str]:
        item = self._project_list.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _selected_task_id(self) -> Optional[str]:
        item = self._task_list.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    # ------------------------------------------------------------------
    # Project actions
    # ------------------------------------------------------------------

    def _on_add_project(self) -> None:
        dialog = AddEditProjectDialog(self.context)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.projects.add_project(
            name=dialog.entered_name,
            status=dialog.entered_status,
            due_date=dialog.entered_due_date,
            description=dialog.entered_description,
            intent_id=dialog.entered_intent_id,
        )
        self._refresh_project_list()

    def _on_edit_project(self) -> None:
        project_id = self._selected_project_id()
        if project_id is None:
            QMessageBox.information(None, "No Project Selected", "Select a project to edit.")
            return

        project = self.context.projects.get_project(project_id)
        dialog = AddEditProjectDialog(self.context, project=project)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.projects.update_project(
            project_id,
            name=dialog.entered_name,
            status=dialog.entered_status,
            due_date=dialog.entered_due_date,
            description=dialog.entered_description,
            intent_id=dialog.entered_intent_id,
        )
        self._refresh_project_list()

    def _on_delete_project(self) -> None:
        project_id = self._selected_project_id()
        if project_id is None:
            QMessageBox.information(None, "No Project Selected", "Select a project to delete.")
            return

        project = self.context.projects.get_project(project_id)
        task_count = len(self.context.tasks.tasks_for_project(project_id))
        if task_count:
            proceed = QMessageBox.question(
                None,
                "Project Has Tasks",
                f"'{project.name}' has {task_count} task(s) under it. Deleting the "
                "project does not delete those tasks — they'll just no longer be "
                "grouped under it. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if proceed != QMessageBox.StandardButton.Yes:
                return

        dialog = DeleteConfirmDialog(project.name, is_directory=False)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.projects.delete_project(project_id)
        self._refresh_project_list()

    def _on_manage_skills(self) -> None:
        project_id = self._selected_project_id()
        if project_id is None:
            QMessageBox.information(None, "No Project Selected", "Select a project to manage skills for.")
            return

        project = self.context.projects.get_project(project_id)
        dialog = ManageProjectSkillsDialog(self.context, project)
        dialog.exec()
        self._refresh_project_list()

    # ------------------------------------------------------------------
    # Task actions
    # ------------------------------------------------------------------

    def _on_add_task(self) -> None:
        project_id = self._selected_project_id()
        if project_id is None:
            QMessageBox.information(None, "No Project Selected", "Select a project to add a task to.")
            return

        dialog = AddEditTaskDialog()
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.tasks.add_task(
            project_id=project_id,
            title=dialog.entered_title,
            due_date=dialog.entered_due_date,
            notes=dialog.entered_notes,
        )
        if dialog.entered_done:
            # add_task() has no `done` param (a brand-new task defaults
            # to not-done) — a one-off toggle covers the rare case of
            # adding a task that's already complete (e.g. backfilling).
            added = self.context.tasks.tasks_for_project(project_id)[-1]
            self.context.tasks.toggle_done(added.task_id)
        self._refresh_task_list()

    def _on_edit_task(self) -> None:
        task_id = self._selected_task_id()
        if task_id is None:
            QMessageBox.information(None, "No Task Selected", "Select a task to edit.")
            return

        task = self.context.tasks.get_task(task_id)
        dialog = AddEditTaskDialog(task=task)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.tasks.update_task(
            task_id,
            title=dialog.entered_title,
            done=dialog.entered_done,
            due_date=dialog.entered_due_date,
            notes=dialog.entered_notes,
        )
        self._refresh_task_list()

    def _on_toggle_task(self) -> None:
        task_id = self._selected_task_id()
        if task_id is None:
            QMessageBox.information(None, "No Task Selected", "Select a task to toggle.")
            return

        self.context.tasks.toggle_done(task_id)
        self._refresh_task_list()

    def _on_delete_task(self) -> None:
        task_id = self._selected_task_id()
        if task_id is None:
            QMessageBox.information(None, "No Task Selected", "Select a task to delete.")
            return

        task = self.context.tasks.get_task(task_id)
        dialog = DeleteConfirmDialog(task.title, is_directory=False)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.tasks.delete_task(task_id)
        self._refresh_task_list()
