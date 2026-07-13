"""
modules.field_kit.module
==========================

Field Kit's Device Manager — docs/ROADMAP.md milestone 11.2, the first
UI on top of the Connected Device Framework (11.1, core/device_framework.py).
Shows a live list of currently-attached external storage/serial
devices with a per-device actions menu.

Storage devices get two actions:
- "Browse Files" publishes `"files.browse_path_requested"` (handled in
  gui/main_window.py) rather than importing modules.files_mod directly
  — this project's module-isolation rule (cross-module reaction goes
  through the event bus, see CLAUDE.md).
- "Eject Safely" calls `core.device_framework.eject_storage_device()`
  directly (a plain function, not a GUI concern) and reports the
  result via a message box.

Serial devices only show an identification label for now — "Open
Serial Monitor" (raw read/write console) is deliberately deferred, not
forgotten: it needs a background-thread serial read loop (same
QThread-worker shape as modules/assistant/llm_worker.py's ChatWorker),
and this dev sandbox has no real serial hardware attached to verify
that loop actually works against. Shipping untested I/O-threading code
isn't worth the risk — see docs/ROADMAP.md's 11.2 writeup.

A widget-owned QTimer refreshes the list periodically by calling
`context.devices.refresh()` — same pattern as
modules/diagnostics/module.py's System Health panel. `DeviceFramework`
itself owns no timer (core/ services don't do async/threading).
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.device_framework import BlockDevice, SerialDevice, eject_storage_device
from core.logger import get_logger
from modules.module_base import ModuleBase

log = get_logger(__name__)

_REFRESH_MS = 3000


class FieldKitModule(ModuleBase):
    module_id = "field_kit"
    display_name = "Field Kit"
    description = "Detect and manage devices connected to this Pi."
    icon = "\U0001F6E0"  # hammer and wrench

    def __init__(self, context) -> None:
        super().__init__(context)
        self._device_list_layout: Optional[QVBoxLayout] = None
        self._timer: Optional[QTimer] = None

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

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        self._device_list_layout = QVBoxLayout(container)
        self._device_list_layout.setSpacing(8)
        self._device_list_layout.addStretch(1)
        scroll.setWidget(container)
        outer.addWidget(scroll, stretch=1)

        self._refresh()
        self._timer = QTimer(widget)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(_REFRESH_MS)

        return widget

    # ------------------------------------------------------------------
    # Device list
    # ------------------------------------------------------------------

    def _refresh(self) -> None:
        if self.context.devices is None or self._device_list_layout is None:
            return
        storage, serial_devices = self.context.devices.refresh()

        # Clear existing rows — everything except the trailing stretch
        # added in get_widget(), which always stays last.
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

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

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
        self._refresh()
