"""
modules.settings.module
=========================

Settings: Backup/Restore is the module's first real feature (see
docs/ROADMAP.md milestone 2.7) — export/import config + the data
directory (profiles, notifications, etc.), optionally
passphrase-encrypted via core/secrets_manager.py. Editing settings
live (theme, user info, module toggles — the rest of what "Settings"
implies) remains a placeholder for a future milestone.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.backup_manager import create_backup, is_backup_encrypted, restore_backup
from core.logger import get_logger
from gui.backup_dialog import BackupPassphraseDialog
from gui.password_dialog import PasswordPromptDialog
from modules.module_base import ModuleBase

log = get_logger(__name__)


class SettingsModule(ModuleBase):
    module_id = "settings"
    display_name = "Settings"
    description = "Configure M.I.A. — theme, user info, module options."
    icon = "⚙"  # gear

    def __init__(self, context) -> None:
        super().__init__(context)
        self._status_label: QLabel | None = None

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

        backup_section = QLabel("Backup & Restore")
        backup_section.setStyleSheet("font-weight: 600; margin-top: 12px;")
        outer.addWidget(backup_section)

        backup_desc = QLabel(
            "Export your configuration and data (profiles, notifications, "
            "etc.) to a single file, or restore from a previous backup."
        )
        backup_desc.setObjectName("SubtitleLabel")
        backup_desc.setWordWrap(True)
        outer.addWidget(backup_desc)

        button_row = QHBoxLayout()

        backup_button = QPushButton("\U0001F4E6 Backup Now")
        backup_button.setObjectName("ModuleButton")
        backup_button.clicked.connect(self._on_backup_clicked)
        button_row.addWidget(backup_button)

        restore_button = QPushButton("♻ Restore from Backup")
        restore_button.setObjectName("ModuleButton")
        restore_button.clicked.connect(self._on_restore_clicked)
        button_row.addWidget(restore_button)

        outer.addLayout(button_row)

        self._status_label = QLabel("")
        self._status_label.setObjectName("SubtitleLabel")
        self._status_label.setWordWrap(True)
        outer.addWidget(self._status_label)

        outer.addStretch()
        return widget

    # ------------------------------------------------------------------
    # Backup
    # ------------------------------------------------------------------

    def _on_backup_clicked(self) -> None:
        dialog = BackupPassphraseDialog(None)
        if dialog.exec() != BackupPassphraseDialog.DialogCode.Accepted:
            return
        passphrase = dialog.entered_passphrase

        default_name = "mia_backup.miabackup" if passphrase else "mia_backup.zip"
        # A bare filename (no directory) defaults QFileDialog to the
        # process's cwd — when launched via `python main.py` from the
        # repo, that's the project's own git working tree, which is
        # exactly where a backup shouldn't land by default.
        default_path = str(Path.home() / default_name)
        file_filter = "M.I.A. Backup (*.miabackup)" if passphrase else "M.I.A. Backup (*.zip)"
        destination, _ = QFileDialog.getSaveFileName(None, "Save Backup As", default_path, file_filter)
        if not destination:
            return

        result = create_backup(Path(destination), passphrase=passphrase or None)
        if result.passed:
            QMessageBox.information(None, "Backup Created", f"Backup saved to:\n{result.destination}")
            self._set_status(f"Backup created: {result.destination}")
        else:
            QMessageBox.warning(None, "Backup Failed", "\n".join(result.errors))
            self._set_status("Backup failed — see error dialog.")

    # ------------------------------------------------------------------
    # Restore
    # ------------------------------------------------------------------

    def _on_restore_clicked(self) -> None:
        source, _ = QFileDialog.getOpenFileName(
            None, "Select Backup File", "", "M.I.A. Backup (*.zip *.miabackup);;All Files (*)"
        )
        if not source:
            return
        source_path = Path(source)

        passphrase = None
        if is_backup_encrypted(source_path):
            dialog = PasswordPromptDialog("this backup", prompt="Enter the passphrase for")
            if dialog.exec() != PasswordPromptDialog.DialogCode.Accepted:
                return
            passphrase = dialog.entered_password

        confirm = QMessageBox.question(
            None,
            "Confirm Restore",
            "Restoring will overwrite your current configuration and data "
            "(profiles, notifications, etc.) with the contents of this "
            "backup. This cannot be undone.\n\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        result = restore_backup(source_path, passphrase=passphrase)
        if result.passed:
            QMessageBox.information(
                None, "Restore Complete",
                "Restore complete. Please restart M.I.A. for the changes to take effect."
            )
            self._set_status("Restore complete — restart M.I.A. to apply.")
        else:
            QMessageBox.warning(None, "Restore Failed", "\n".join(result.errors))
            self._set_status("Restore failed — see error dialog.")

    def _set_status(self, text: str) -> None:
        if self._status_label is not None:
            self._status_label.setText(text)
