"""
modules.field_kit.module
==========================

Field Kit — docs/ROADMAP.md milestones 11.2 (Device Manager) and 11.4
(Useful Scripts). Two tabs in one module (docs/MODULE_SPEC.md allows
exactly one `ModuleBase` subclass per module folder, so multiple
sub-features share tabs rather than becoming separate modules — the
first module in this app to need a `QTabWidget` for that reason).

**Devices tab** — a live list of currently-attached external
storage/serial devices with a per-device actions menu, sourced from
`core/device_framework.py` (milestone 11.1):
- "Browse Files" publishes `"files.browse_path_requested"` (handled in
  gui/main_window.py) rather than importing modules.files_mod directly
  — this project's module-isolation rule (cross-module reaction goes
  through the event bus, see CLAUDE.md).
- "Eject Safely" calls `core.device_framework.eject_storage_device()`
  directly (a plain function, not a GUI concern) and reports the
  result via a message box.
Serial devices only show an identification label for now — "Open
Serial Monitor" is deliberately deferred, see this module's git history
and docs/ROADMAP.md's 11.2 writeup for why (needs real serial hardware
this dev sandbox doesn't have, to verify a background read-thread
against).

A widget-owned QTimer refreshes the device list periodically by
calling `context.devices.refresh()` — same pattern as
modules/diagnostics/module.py's System Health panel. `DeviceFramework`
itself owns no timer (core/ services don't do async/threading).

**Scripts tab** — a categorized library of user-authored shell/Python
scripts (`core/script_library_manager.py`), with Add/Edit/Delete (same
CRUD shape as Notes/Inventory/Waypoints) plus Run/Stop, streaming live
output via `modules/field_kit/script_worker.py`'s `ScriptWorker`
(`QThread`, same scoped-worker pattern as
`modules/assistant/llm_worker.py`'s `ChatWorker` — a script can run
indefinitely, so reading its output on the GUI thread would freeze the
whole app). No sandboxing when a script runs — these are the user's
own trusted scripts, same stance this project already takes for
module installation.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.device_framework import BlockDevice, SerialDevice, eject_storage_device
from core.logger import get_logger
from core.script_library_manager import Script
from gui.add_edit_script_dialog import AddEditScriptDialog
from gui.delete_confirm_dialog import DeleteConfirmDialog
from modules.field_kit.script_worker import ScriptWorker
from modules.module_base import ModuleBase

log = get_logger(__name__)

_DEVICE_REFRESH_MS = 3000


def format_script_row(script: Script) -> str:
    """Pure formatting logic — testable without Qt (see tests/test_field_kit_module.py)."""
    category_part = f"[{script.category}]  " if script.category else ""
    return f"{category_part}{script.name}  ({script.interpreter})"


class FieldKitModule(ModuleBase):
    module_id = "field_kit"
    display_name = "Field Kit"
    description = "Detect and manage connected devices; run your own scripts."
    icon = "\U0001F6E0"  # hammer and wrench

    def __init__(self, context) -> None:
        super().__init__(context)
        self._device_list_layout: Optional[QVBoxLayout] = None
        self._device_timer: Optional[QTimer] = None

        self._script_list: Optional[QListWidget] = None
        self._script_filter_edit: Optional[QLineEdit] = None
        self._script_output: Optional[QPlainTextEdit] = None
        self._run_button: Optional[QPushButton] = None
        self._stop_button: Optional[QPushButton] = None
        self._script_worker: Optional[ScriptWorker] = None

    def get_widget(self) -> QWidget:
        widget = QWidget()
        outer = QVBoxLayout(widget)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(12)

        header = QLabel(f"{self.icon}  {self.display_name}")
        header.setObjectName("TitleLabel")
        outer.addWidget(header)

        subtitle = QLabel(self.description)
        subtitle.setObjectName("SubtitleLabel")
        outer.addWidget(subtitle)

        tabs = QTabWidget()
        tabs.addTab(self._build_devices_tab(), "Devices")
        tabs.addTab(self._build_scripts_tab(), "Scripts")
        outer.addWidget(tabs, stretch=1)

        return widget

    # ------------------------------------------------------------------
    # Devices tab
    # ------------------------------------------------------------------

    def _build_devices_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        self._device_list_layout = QVBoxLayout(container)
        self._device_list_layout.setSpacing(8)
        self._device_list_layout.addStretch(1)
        scroll.setWidget(container)
        layout.addWidget(scroll, stretch=1)

        self._refresh_devices()
        self._device_timer = QTimer(tab)
        self._device_timer.timeout.connect(self._refresh_devices)
        self._device_timer.start(_DEVICE_REFRESH_MS)

        return tab

    def _refresh_devices(self) -> None:
        if self.context.devices is None or self._device_list_layout is None:
            return
        storage, serial_devices = self.context.devices.refresh()

        # Clear existing rows — everything except the trailing stretch
        # added in _build_devices_tab(), which always stays last.
        while self._device_list_layout.count() > 1:
            item = self._device_list_layout.takeAt(0)
            row_widget = item.widget()
            if row_widget is not None:
                row_widget.deleteLater()

        if not storage and not serial_devices:
            empty_label = QLabel("No external devices connected.")
            empty_label.setObjectName("SubtitleLabel")
            self._device_list_layout.insertWidget(0, empty_label)
            return

        row_index = 0
        for device in storage:
            self._device_list_layout.insertWidget(row_index, self._build_storage_row(device))
            row_index += 1
        for device in serial_devices:
            self._device_list_layout.insertWidget(row_index, self._build_serial_row(device))
            row_index += 1

    def _build_storage_row(self, device: BlockDevice) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)

        label = QLabel(f"\U0001F4BE  {device.display_name}")
        layout.addWidget(label, stretch=1)

        browse_button = QPushButton("Browse Files")
        browse_button.clicked.connect(lambda: self._on_browse_clicked(device))
        layout.addWidget(browse_button)

        eject_button = QPushButton("Eject Safely")
        eject_button.clicked.connect(lambda: self._on_eject_clicked(device))
        layout.addWidget(eject_button)

        return row

    def _build_serial_row(self, device: SerialDevice) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)

        label = QLabel(f"\U0001F50C  {device.display_name}")
        layout.addWidget(label, stretch=1)
        layout.addWidget(QLabel("(Serial Monitor coming soon)"))

        return row

    def _on_browse_clicked(self, device: BlockDevice) -> None:
        if not device.mountpoint:
            QMessageBox.information(
                None, "Not mounted", f"'{device.display_name}' has no mounted filesystem to browse."
            )
            return
        self.context.events.publish("files.browse_path_requested", path=device.mountpoint)

    def _on_eject_clicked(self, device: BlockDevice) -> None:
        success, message = eject_storage_device(device.name)
        if success:
            QMessageBox.information(None, "Ejected", message)
        else:
            QMessageBox.warning(None, "Eject failed", message)
        self._refresh_devices()

    # ------------------------------------------------------------------
    # Scripts tab
    # ------------------------------------------------------------------

    def _build_scripts_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self._script_filter_edit = QLineEdit()
        self._script_filter_edit.setPlaceholderText("Filter scripts by name, category, or content…")
        self._script_filter_edit.textChanged.connect(lambda _text: self._refresh_scripts())
        layout.addWidget(self._script_filter_edit)

        self._script_list = QListWidget()
        layout.addWidget(self._script_list, stretch=1)

        button_row = QHBoxLayout()
        add_button = QPushButton("New Script")
        add_button.clicked.connect(self._on_add_script)
        button_row.addWidget(add_button)

        edit_button = QPushButton("Edit Selected")
        edit_button.clicked.connect(self._on_edit_script)
        button_row.addWidget(edit_button)

        delete_button = QPushButton("Delete Selected")
        delete_button.clicked.connect(self._on_delete_script)
        button_row.addWidget(delete_button)

        self._run_button = QPushButton("Run")
        self._run_button.clicked.connect(self._on_run_script)
        button_row.addWidget(self._run_button)

        self._stop_button = QPushButton("Stop")
        self._stop_button.setEnabled(False)
        self._stop_button.clicked.connect(self._on_stop_script)
        button_row.addWidget(self._stop_button)

        layout.addLayout(button_row)

        self._script_output = QPlainTextEdit()
        self._script_output.setObjectName("ChatLog")
        self._script_output.setReadOnly(True)
        layout.addWidget(self._script_output, stretch=1)

        self._refresh_scripts()
        return tab

    def _refresh_scripts(self) -> None:
        if self.context.scripts is None or self._script_list is None:
            return
        query = self._script_filter_edit.text().strip()
        scripts = self.context.scripts.search(query) if query else self.context.scripts.all_scripts()

        self._script_list.clear()
        for script in scripts:
            item = QListWidgetItem(format_script_row(script))
            item.setData(Qt.ItemDataRole.UserRole, script.script_id)
            self._script_list.addItem(item)

    def _selected_script_id(self) -> Optional[str]:
        item = self._script_list.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _on_add_script(self) -> None:
        dialog = AddEditScriptDialog()
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.context.scripts.add_script(
            name=dialog.entered_name,
            interpreter=dialog.entered_interpreter,
            content=dialog.entered_content,
            category=dialog.entered_category,
        )
        self._refresh_scripts()

    def _on_edit_script(self) -> None:
        script_id = self._selected_script_id()
        if script_id is None:
            QMessageBox.information(None, "No Script Selected", "Select a script to edit.")
            return
        script = self.context.scripts.get_script(script_id)
        dialog = AddEditScriptDialog(script=script)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.context.scripts.update_script(
            script_id,
            name=dialog.entered_name,
            interpreter=dialog.entered_interpreter,
            content=dialog.entered_content,
            category=dialog.entered_category,
        )
        self._refresh_scripts()

    def _on_delete_script(self) -> None:
        script_id = self._selected_script_id()
        if script_id is None:
            QMessageBox.information(None, "No Script Selected", "Select a script to delete.")
            return
        script = self.context.scripts.get_script(script_id)
        dialog = DeleteConfirmDialog(script.name, is_directory=False, parent=None)
        if dialog.exec() != DeleteConfirmDialog.DialogCode.Accepted:
            return
        self.context.scripts.delete_script(script_id)
        self._refresh_scripts()

    def _on_run_script(self) -> None:
        if self._script_worker is not None:
            return
        script_id = self._selected_script_id()
        if script_id is None:
            QMessageBox.information(None, "No Script Selected", "Select a script to run.")
            return
        script = self.context.scripts.get_script(script_id)

        self._script_output.clear()
        self._script_output.appendPlainText(f"$ Running '{script.name}' ({script.interpreter})...")
        self._run_button.setEnabled(False)
        self._stop_button.setEnabled(True)

        self._script_worker = ScriptWorker(script.interpreter, script.content)
        self._script_worker.output_line.connect(self._script_output.appendPlainText)
        self._script_worker.finished_with_code.connect(self._on_script_finished)
        self._script_worker.start()

    def _on_stop_script(self) -> None:
        if self._script_worker is not None:
            self._script_worker.stop()

    def _on_script_finished(self, returncode: int) -> None:
        self._script_output.appendPlainText(f"$ Exited with code {returncode}.")
        self._run_button.setEnabled(True)
        self._stop_button.setEnabled(False)
        if self._script_worker is not None:
            self._script_worker.deleteLater()
            self._script_worker = None
