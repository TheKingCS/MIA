"""
modules.field_kit.module
==========================

Field Kit — docs/ROADMAP.md milestones 11.2 (Device Manager), 11.4
(Useful Scripts), and 11.5 (Security/Network Toolkit). Three tabs in
one module (docs/MODULE_SPEC.md allows exactly one `ModuleBase`
subclass per module folder, so multiple sub-features share tabs rather
than becoming separate modules — the first module in this app to need
a `QTabWidget` for that reason).

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
`core/chat_worker.py`'s `ChatWorker` — a script can run
indefinitely, so reading its output on the GUI thread would freeze the
whole app). No sandboxing when a script runs — these are the user's
own trusted scripts, same stance this project already takes for
module installation.

**Security tab** — recon tools that need no external system binary and
no root: a hash format identifier (`core/hash_identifier.py`), a
password strength estimator (`core/password_strength.py`), a subnet/
CIDR calculator (`core/subnet_calculator.py`), and a TCP connect-scan
port scanner (`core/port_scanner.py`, run via
`modules/field_kit/port_scan_worker.py`'s `PortScanWorker` — same
scoped-`QThread` reasoning as the Scripts tab, since scanning even the
short common-ports default can block for several seconds). **Wi-Fi/
network analyzer and active tooling (hash cracking via John/Hashcat,
packet crafting via scapy, exploit-framework launching) are
deliberately not implemented**: none of those underlying tools are
installed in this dev sandbox, and none can be added without root —
confirmed blocked, not just deferred, same "no sudo" wall as Ollama's
portable-binary workaround and Media/Music's missing `libpulse`. See
docs/KNOWN_ISSUES.md.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
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
from core.device_profile import is_home_profile
from core.expedition_sync import export_expedition_data, find_export_bundles, import_expedition_data
from core.hash_identifier import identify_hash
from core.logger import get_logger
from core.password_strength import assess_password
from core.port_scanner import PortScanResult
from core.script_library_manager import Script
from core.subnet_calculator import calculate_subnet
from gui.add_edit_script_dialog import AddEditScriptDialog
from gui.delete_confirm_dialog import DeleteConfirmDialog
from modules.field_kit.port_scan_worker import PortScanWorker
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
        # docs/ROADMAP.md milestone v0.19 (Home Dock auto-launch
        # Dashboard) — disk names of storage devices already
        # auto-import-checked this "dock", so a still-connected device
        # doesn't re-trigger on every 3s poll tick. Pruned to currently-
        # connected names each refresh (see _refresh_devices()), so
        # unplugging and re-docking the same device is treated as new.
        self._auto_imported_devices: set[str] = set()

        self._script_list: Optional[QListWidget] = None
        self._script_filter_edit: Optional[QLineEdit] = None
        self._script_output: Optional[QPlainTextEdit] = None
        self._run_button: Optional[QPushButton] = None
        self._stop_button: Optional[QPushButton] = None
        self._script_worker: Optional[ScriptWorker] = None

        self._hash_input: Optional[QLineEdit] = None
        self._hash_result_label: Optional[QLabel] = None
        self._password_input: Optional[QLineEdit] = None
        self._password_result_label: Optional[QLabel] = None
        self._subnet_input: Optional[QLineEdit] = None
        self._subnet_result_label: Optional[QLabel] = None
        self._scan_host_input: Optional[QLineEdit] = None
        self._scan_button: Optional[QPushButton] = None
        self._scan_result_label: Optional[QLabel] = None
        self._scan_worker: Optional[PortScanWorker] = None

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
        tabs.addTab(self._build_security_tab(), "Security")
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

        # Forget any device that's no longer connected, so unplugging
        # and re-docking the same disk name is treated as a fresh dock
        # (see _check_for_docked_core()'s docstring).
        self._auto_imported_devices &= {device.name for device in storage}
        for device in storage:
            self._check_for_docked_core(device)

        # Clear existing rows — everything except the trailing stretch
        # added in _build_devices_tab(), which always stays last.
        # hide()+setParent(None) before deleteLater() — deleteLater()
        # alone doesn't remove a widget from the screen immediately, a
        # real ghosting bug found via an actual screenshot (see
        # modules/toolbox/tools/lite_captures_tool.py) and fixed across
        # this codebase's other actively-re-triggered refresh methods
        # the same day.
        while self._device_list_layout.count() > 1:
            item = self._device_list_layout.takeAt(0)
            row_widget = item.widget()
            if row_widget is not None:
                row_widget.hide()
                row_widget.setParent(None)
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

        export_button = QPushButton("Export Expedition Data Here")
        export_button.clicked.connect(lambda: self._on_export_expedition_data_clicked(device))
        layout.addWidget(export_button)

        import_button = QPushButton("Import Expedition Data From Here")
        import_button.clicked.connect(lambda: self._on_import_expedition_data_clicked(device))
        layout.addWidget(import_button)

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

    def _on_export_expedition_data_clicked(self, device: BlockDevice) -> None:
        if not device.mountpoint:
            QMessageBox.information(
                None, "Not mounted", f"'{device.display_name}' has no mounted filesystem to export to."
            )
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        destination = Path(device.mountpoint) / f"mia_expedition_export_{timestamp}.zip"
        result = export_expedition_data(destination)
        if result.passed:
            QMessageBox.information(None, "Export Complete", f"Expedition data exported to:\n{result.destination}")
        else:
            QMessageBox.warning(None, "Export Failed", "\n".join(result.errors))

    def _on_import_expedition_data_clicked(self, device: BlockDevice) -> None:
        if not device.mountpoint:
            QMessageBox.information(
                None, "Not mounted", f"'{device.display_name}' has no mounted filesystem to import from."
            )
            return

        source, _ = QFileDialog.getOpenFileName(
            None, "Select Expedition Data Export", device.mountpoint, "MIA Expedition Export (*.zip)"
        )
        if not source:
            return

        result = import_expedition_data(Path(source))
        if result.passed:
            self._reload_expedition_managers()
            summary = "\n".join(f"{name}: +{count}" for name, count in result.counts.items() if count)
            if not summary:
                summary = "No new records or photos — everything in this export was already present."
            # A per-file merge error (2026-09-14 stabilization pass) —
            # e.g. a corrupted live trips.json — doesn't fail the whole
            # import, but must still reach the user: silently showing
            # "Import Complete" while one file was actually skipped
            # would hide a real problem.
            if result.errors:
                summary += "\n\nWarnings:\n" + "\n".join(f"• {e}" for e in result.errors)
            QMessageBox.information(None, "Import Complete", summary)
        else:
            QMessageBox.warning(None, "Import Failed", "\n".join(result.errors))

    def _reload_expedition_managers(self) -> None:
        """
        Re-reads every manager import_expedition_data() can touch, so
        newly-merged records show up immediately — docs/ROADMAP.md
        milestone v0.19 removed the previous "restart MIA to see
        imported data" limitation for both the manual Import button
        above and the auto-import path below, once reload() existed on
        each manager anyway (core/expedition_manager.py's docstring).
        """
        for manager in (
            self.context.expeditions, self.context.trips, self.context.waypoints,
            self.context.journal, self.context.inventory,
        ):
            if manager is not None:
                manager.reload()

    def _check_for_docked_core(self, device: BlockDevice) -> None:
        """
        Auto-import + auto-navigate half of docs/ROADMAP.md milestone
        v0.19 (Home Dock auto-launch Dashboard) — Home-profile only
        (a Core docking to another Core was never part of the vision).
        Detection is `find_export_bundles()` (core/expedition_sync.py)
        finding one or more `mia_expedition_export_*.zip` files at the
        device's mount root — files only the Export button above ever
        creates, so this works regardless of the still-unverified real
        Pi 5 USB gadget-mode mount layout (docs/HARDWARE.md). Only the
        in-app "already running, auto-navigate" half is built here —
        launching MIA itself from a cold, not-yet-running state via a
        Windows background watcher (pywin32/WMI USB-arrival events) is a
        separate, deliberately deferred follow-up: genuinely untestable
        in this Linux dev sandbox, same category as 11.3b/11.6.
        """
        if not is_home_profile(self.context):
            return
        if not device.mountpoint or device.name in self._auto_imported_devices:
            return

        bundles = find_export_bundles(Path(device.mountpoint))
        if not bundles:
            return
        self._auto_imported_devices.add(device.name)

        total_counts: dict[str, int] = {}
        any_failed = False
        for bundle_path in bundles:
            result = import_expedition_data(bundle_path)
            if not result.passed:
                any_failed = True
                log.warning("Auto-import failed for '%s': %s", bundle_path, "; ".join(result.errors))
                continue
            if result.errors:
                # A partial success (2026-09-14 stabilization pass) —
                # e.g. a corrupted live trips.json skipped this one
                # file's merge — still counts as "failed" for this
                # unattended flow's own summary note, even though
                # result.passed is True: there's no dialog here to show
                # the detail in, so the log is the only place it's
                # visible, and the summary note is what tells the user
                # to go look.
                any_failed = True
                log.warning("Auto-import partially failed for '%s': %s", bundle_path, "; ".join(result.errors))
            for key, count in result.counts.items():
                total_counts[key] = total_counts.get(key, 0) + count

        self._reload_expedition_managers()

        summary_lines = [f"{name}: +{count}" for name, count in total_counts.items() if count]
        summary = "\n".join(summary_lines) if summary_lines else "No new records — everything was already present."
        if any_failed:
            summary += "\n(Some bundles could not be imported — see the log.)"

        if self.context.notifications is not None:
            self.context.notifications.notify(
                title=f"Core docked: {device.display_name}",
                message=summary,
                source="field_kit",
            )
        # Reuses the existing open_module_requested event/handler
        # (gui/main_window.py) rather than inventing a new one —
        # navigating to a module by id is exactly what this already
        # does, whether the request came from the Assistant or here.
        self.context.events.publish("assistant.open_module_requested", module_id="dashboard")
        log.info("Auto-imported Expedition data from docked Core '%s': %s", device.display_name, total_counts)

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

    # ------------------------------------------------------------------
    # Security tab
    # ------------------------------------------------------------------

    def _build_security_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        layout.addWidget(self._section_label("Hash Identifier"))
        hash_row = QHBoxLayout()
        self._hash_input = QLineEdit()
        self._hash_input.setPlaceholderText("Paste a hash, e.g. a bcrypt or SHA-256 digest...")
        hash_row.addWidget(self._hash_input, stretch=1)
        identify_button = QPushButton("Identify")
        identify_button.clicked.connect(self._on_identify_hash)
        hash_row.addWidget(identify_button)
        layout.addLayout(hash_row)
        self._hash_result_label = QLabel("")
        self._hash_result_label.setObjectName("ReadoutLabel")
        layout.addWidget(self._hash_result_label)

        layout.addWidget(self._section_label("Password Strength"))
        self._password_input = QLineEdit()
        self._password_input.setPlaceholderText("Type a password to check its strength...")
        self._password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._password_input.textChanged.connect(self._on_password_changed)
        layout.addWidget(self._password_input)
        self._password_result_label = QLabel("")
        self._password_result_label.setObjectName("ReadoutLabel")
        self._password_result_label.setWordWrap(True)
        layout.addWidget(self._password_result_label)

        layout.addWidget(self._section_label("Subnet Calculator"))
        subnet_row = QHBoxLayout()
        self._subnet_input = QLineEdit()
        self._subnet_input.setPlaceholderText("e.g. 192.168.1.0/24")
        subnet_row.addWidget(self._subnet_input, stretch=1)
        calculate_button = QPushButton("Calculate")
        calculate_button.clicked.connect(self._on_calculate_subnet)
        subnet_row.addWidget(calculate_button)
        layout.addLayout(subnet_row)
        self._subnet_result_label = QLabel("")
        self._subnet_result_label.setObjectName("ReadoutLabel")
        self._subnet_result_label.setWordWrap(True)
        layout.addWidget(self._subnet_result_label)

        layout.addWidget(self._section_label("Port Scanner (TCP connect scan, common ports)"))
        scan_row = QHBoxLayout()
        self._scan_host_input = QLineEdit()
        self._scan_host_input.setPlaceholderText("Host or IP, e.g. 192.168.1.1")
        scan_row.addWidget(self._scan_host_input, stretch=1)
        self._scan_button = QPushButton("Scan")
        self._scan_button.clicked.connect(self._on_scan_ports)
        scan_row.addWidget(self._scan_button)
        layout.addLayout(scan_row)
        self._scan_result_label = QLabel("")
        self._scan_result_label.setObjectName("ReadoutLabel")
        self._scan_result_label.setWordWrap(True)
        layout.addWidget(self._scan_result_label)

        blocked_note = QLabel(
            "Wi-Fi/network analyzer and active tooling (hash cracking, packet "
            "crafting, exploit-framework launching) aren't available in this "
            "environment — the underlying tools (aircrack-ng, John/Hashcat, "
            "scapy, Metasploit) aren't installed and can't be added without "
            "root. See docs/KNOWN_ISSUES.md."
        )
        blocked_note.setObjectName("SubtitleLabel")
        blocked_note.setWordWrap(True)
        layout.addWidget(blocked_note)

        layout.addStretch()
        return tab

    @staticmethod
    def _section_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet("font-weight: 600; margin-top: 12px;")
        return label

    def _on_identify_hash(self) -> None:
        value = self._hash_input.text().strip()
        if not value:
            self._hash_result_label.setText("Enter a hash to identify.")
            return
        candidates = identify_hash(value)
        if not candidates:
            self._hash_result_label.setText("No known hash format matched.")
        else:
            self._hash_result_label.setText("Possible: " + ", ".join(candidates))

    def _on_password_changed(self, text: str) -> None:
        if not text:
            self._password_result_label.setText("")
            return
        result = assess_password(text)
        lines = [f"Strength: {result.rating} ({result.entropy_bits:.1f} bits)"]
        lines.extend(result.warnings)
        self._password_result_label.setText("\n".join(lines))

    def _on_calculate_subnet(self) -> None:
        cidr = self._subnet_input.text().strip()
        if not cidr:
            self._subnet_result_label.setText("Enter a CIDR, e.g. 192.168.1.0/24.")
            return
        try:
            info = calculate_subnet(cidr)
        except ValueError as exc:
            self._subnet_result_label.setText(f"Invalid CIDR: {exc}")
            return
        lines = [
            f"Network: {info.network_address}/{info.prefix_length}",
            f"Broadcast: {info.broadcast_address}",
            f"Netmask: {info.netmask}",
            f"Total addresses: {info.total_addresses}",
            f"Usable hosts: {info.usable_host_count}",
        ]
        if info.first_usable:
            lines.append(f"Usable range: {info.first_usable} - {info.last_usable}")
        self._subnet_result_label.setText("\n".join(lines))

    def _on_scan_ports(self) -> None:
        if self._scan_worker is not None:
            return
        host = self._scan_host_input.text().strip()
        if not host:
            self._scan_result_label.setText("Enter a host or IP to scan.")
            return

        self._scan_result_label.setText("Scanning...")
        self._scan_button.setEnabled(False)
        self._scan_worker = PortScanWorker(host)
        self._scan_worker.result_ready.connect(self._on_scan_finished)
        self._scan_worker.start()

    def _on_scan_finished(self, result: PortScanResult) -> None:
        if result.error:
            self._scan_result_label.setText(result.error)
        elif not result.open_ports:
            self._scan_result_label.setText(f"No open ports found among {result.scanned_count} scanned.")
        else:
            ports_text = ", ".join(str(p) for p in result.open_ports)
            self._scan_result_label.setText(f"Open ports: {ports_text} (of {result.scanned_count} scanned)")

        self._scan_button.setEnabled(True)
        if self._scan_worker is not None:
            self._scan_worker.deleteLater()
            self._scan_worker = None
