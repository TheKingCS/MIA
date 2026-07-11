"""
modules.module_browser.module
===============================

Backs the "Modules" button on the main menu.

Fully functional: lists every discovered module, lets you enable/
disable each one (persisted, affects the main menu live via the event
bus — no restart needed), rescan for newly-added module folders, and
now install a new module directly from a folder or a .zip file. Every
install goes through core/module_validator.py first — see
docs/MODULE_SPEC.md for the exact compatibility contract being checked.

Note: unlike other modules, this one holds a direct reference to the
real ModuleManager (self.module_manager, set externally by
gui/main_window.py's _wire_module_browser()) rather than just a static
snapshot of module metadata. That's a deliberate, narrow exception —
this module's entire purpose is managing modules.
"""

from __future__ import annotations

import shutil
import tempfile
import zipfile
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from modules.module_base import ModuleBase


class ModuleBrowserModule(ModuleBase):
    module_id = "module_browser"
    display_name = "Modules"
    description = "View, enable/disable, install, and rescan modules."
    icon = "\U0001F9E9"  # puzzle piece

    def __init__(self, context) -> None:
        super().__init__(context)
        # Populated by gui/main_window.py's _wire_module_browser().
        self.known_modules: list[ModuleBase] = []
        self.module_manager = None
        self._list_layout = None
        self._status_label = None

    def get_widget(self) -> QWidget:
        widget = QWidget()
        outer = QVBoxLayout(widget)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(12)

        header = QLabel("Loaded Modules")
        header.setObjectName("TitleLabel")
        outer.addWidget(header)

        button_row = QHBoxLayout()

        rescan_button = QPushButton("\U0001F504 Rescan")
        rescan_button.setObjectName("ModuleButton")
        rescan_button.clicked.connect(self._on_rescan_clicked)
        button_row.addWidget(rescan_button)

        add_folder_button = QPushButton("\U0001F4C1 Add Module (Folder)")
        add_folder_button.setObjectName("ModuleButton")
        add_folder_button.clicked.connect(self._on_add_module_folder_clicked)
        button_row.addWidget(add_folder_button)

        add_zip_button = QPushButton("\U0001F5DC Add Module (.zip)")
        add_zip_button.setObjectName("ModuleButton")
        add_zip_button.clicked.connect(self._on_add_module_zip_clicked)
        button_row.addWidget(add_zip_button)

        outer.addLayout(button_row)

        self._status_label = QLabel("")
        self._status_label.setObjectName("SubtitleLabel")
        self._status_label.setWordWrap(True)
        outer.addWidget(self._status_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        list_container = QWidget()
        self._list_layout = QVBoxLayout(list_container)
        self._list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._list_layout.setSpacing(8)

        scroll.setWidget(list_container)
        outer.addWidget(scroll)

        self._populate_rows()
        return widget

    # ------------------------------------------------------------------
    # Row list
    # ------------------------------------------------------------------

    def _populate_rows(self) -> None:
        if self._list_layout is None:
            return
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        modules_to_show = self.known_modules or [self]
        for module in modules_to_show:
            self._list_layout.addWidget(self._build_row(module))

    def _build_row(self, module: ModuleBase) -> QFrame:
        is_enabled = True if self.module_manager is None else self.module_manager.is_enabled(module.module_id)
        is_locked = module.module_id == "module_browser"

        row = QFrame()
        border_color = "#232b34" if is_enabled else "#5a3a3a"
        row.setStyleSheet(
            f"QFrame {{ background-color: #161b22; border: 1px solid {border_color}; border-radius: 8px; }}"
        )
        outer = QHBoxLayout(row)

        text_layout = QVBoxLayout()
        status_suffix = "" if is_enabled else "  (disabled)"
        title = QLabel(f"{module.icon}  {module.display_name}  (v{module.version}){status_suffix}")
        title.setStyleSheet("font-weight: 600;")
        subtitle = QLabel(f"id: {module.module_id} \u2014 {module.description}")
        subtitle.setObjectName("SubtitleLabel")
        subtitle.setWordWrap(True)
        text_layout.addWidget(title)
        text_layout.addWidget(subtitle)
        outer.addLayout(text_layout, stretch=3)

        toggle_button = QPushButton("Disable" if is_enabled else "Enable")
        toggle_button.setMinimumHeight(40)
        toggle_button.setEnabled(not is_locked)
        toggle_button.setToolTip("The Modules screen can't be disabled." if is_locked else "")
        toggle_button.clicked.connect(
            lambda checked=False, mid=module.module_id, en=is_enabled: self._on_toggle_clicked(mid, en)
        )
        outer.addWidget(toggle_button, stretch=1)

        return row

    def _on_toggle_clicked(self, module_id: str, currently_enabled: bool) -> None:
        if self.module_manager is None:
            return
        success = self.module_manager.set_enabled(module_id, not currently_enabled)
        self._status_label.setText("" if success else "The Modules screen can't be disabled.")
        self._populate_rows()

    def _on_rescan_clicked(self) -> None:
        if self.module_manager is None:
            return
        new_count = self.module_manager.rescan()
        self.known_modules = self.module_manager.all()
        self._status_label.setText(
            f"Found {new_count} new module(s)." if new_count else "No new modules found."
        )
        self._populate_rows()

    # ------------------------------------------------------------------
    # Installing new modules
    # ------------------------------------------------------------------

    def _on_add_module_folder_clicked(self) -> None:
        if self.module_manager is None:
            return
        folder = QFileDialog.getExistingDirectory(None, "Select Module Folder")
        if not folder:
            return
        self._install_and_report(Path(folder))

    def _on_add_module_zip_clicked(self) -> None:
        if self.module_manager is None:
            return
        zip_path, _ = QFileDialog.getOpenFileName(None, "Select Module .zip", "", "Zip files (*.zip)")
        if not zip_path:
            return

        try:
            extract_dir = Path(tempfile.mkdtemp(prefix="mia_module_install_"))
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(extract_dir)
        except Exception as exc:
            QMessageBox.warning(None, "Install Failed", f"Could not read the zip file: {exc}")
            return

        source_dir = self._resolve_module_source_dir(extract_dir)
        self._install_and_report(source_dir)

    @staticmethod
    def _resolve_module_source_dir(extracted_dir: Path) -> Path:
        """
        Zips of a module folder often contain the folder itself as a
        single top-level entry rather than its contents directly at the
        zip root. If module.py isn't at the root, but there's exactly
        one subfolder that has it, use that subfolder instead.
        """
        if (extracted_dir / "module.py").exists():
            return extracted_dir
        subdirs = [p for p in extracted_dir.iterdir() if p.is_dir()]
        if len(subdirs) == 1 and (subdirs[0] / "module.py").exists():
            return subdirs[0]
        return extracted_dir  # let the validator produce a clear error

    def _install_and_report(self, source_path: Path) -> None:
        result = self.module_manager.install_module_from_folder(source_path)

        if result.passed:
            message = f"Installed '{result.display_name}' successfully."
            if result.warnings:
                message += "\n\nWarnings:\n" + "\n".join(f"\u2022 {w}" for w in result.warnings)
            QMessageBox.information(None, "Module Installed", message)
            self.known_modules = self.module_manager.all()
            self._status_label.setText(f"Installed '{result.display_name}'.")
        else:
            message = "Could not install this module:\n\n" + "\n".join(f"\u2022 {e}" for e in result.errors)
            QMessageBox.warning(None, "Install Failed", message)
            self._status_label.setText("Install failed — see docs/MODULE_SPEC.md for requirements.")

        self._populate_rows()
