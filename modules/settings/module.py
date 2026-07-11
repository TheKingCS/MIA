"""
modules.settings.module
=========================

Settings: Backup/Restore (docs/ROADMAP.md milestone 2.7) — export/
import config + the data directory (profiles, notifications, etc.),
optionally passphrase-encrypted via core/secrets_manager.py — and
Update Manager (milestone 2.8) — apply an offline update package onto
the running installation, see docs/UPDATE_PACKAGE_SPEC.md. Editing
settings live (theme, user info, module toggles — the rest of what
"Settings" implies) remains a placeholder for a future milestone.
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
from core.update_manager import apply_update_package, peek_update_manifest
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

        update_section = QLabel("Update Manager")
        update_section.setStyleSheet("font-weight: 600; margin-top: 12px;")
        outer.addWidget(update_section)

        update_desc = QLabel(
            "Apply an offline update package (e.g. from a USB drive). "
            "This modifies M.I.A.'s own application files directly — "
            "see docs/UPDATE_PACKAGE_SPEC.md before building one."
        )
        update_desc.setObjectName("SubtitleLabel")
        update_desc.setWordWrap(True)
        outer.addWidget(update_desc)

        update_button = QPushButton("⬆ Apply Update Package...")
        update_button.setObjectName("ModuleButton")
        update_button.clicked.connect(self._on_apply_update_clicked)
        outer.addWidget(update_button)

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

    # ------------------------------------------------------------------
    # Update Manager
    # ------------------------------------------------------------------

    def _on_apply_update_clicked(self) -> None:
        source, _ = QFileDialog.getOpenFileName(
            None, "Select Update Package", "", "M.I.A. Update Package (*.zip);;All Files (*)"
        )
        if not source:
            return
        source_path = Path(source)

        manifest = peek_update_manifest(source_path)
        if manifest is not None:
            details = f"Target version: {manifest.target_version}\n\n{manifest.description}".strip()
        else:
            details = "(Could not read update details — proceeding will attempt full validation.)"

        confirm = QMessageBox.warning(
            None,
            "Confirm Update",
            f"{details}\n\n"
            "Applying this update will overwrite M.I.A.'s own application "
            "files — including core system files — with no code review "
            "performed. Only proceed if you built this package yourself "
            "or have reviewed and trust it.\n\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        result = apply_update_package(source_path)
        if result.passed:
            rollback_note = (
                "A git commit was created for easy rollback (git revert)."
                if result.committed
                else f"No automatic rollback commit was created: {result.warnings[0] if result.warnings else 'unknown reason'}"
            )
            QMessageBox.information(
                None, "Update Applied",
                f"Applied {len(result.applied_files)} file(s).\n\n{rollback_note}\n\n"
                "Please restart M.I.A. for the changes to take effect."
            )
            self._set_status(f"Update applied ({len(result.applied_files)} file(s)) — restart M.I.A. to apply.")
        else:
            QMessageBox.warning(None, "Update Failed", "\n".join(result.errors))
            self._set_status("Update failed — see error dialog.")
