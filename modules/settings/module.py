"""
modules.settings.module
=========================

Settings: Backup/Restore (docs/ROADMAP.md milestone 2.7) — export/
import config + the data directory (profiles, notifications, etc.),
optionally passphrase-encrypted via core/secrets_manager.py — Update
Manager (milestone 2.8) — apply an offline update package onto the
running installation, see docs/UPDATE_PACKAGE_SPEC.md — Appearance &
Device Profile (milestone 13.1/13.2): live theme switching
(gui/theme_manager.py) and viewing/changing which edition
(Core/Pi5+HAT vs. Home/desktop, core/device_profile.py) this install is
— and Voice (2026-07-15, at the user's explicit request to "pick
through different voices for M.I.A."): a dropdown over
`core/voice_manager.py`'s `list_available_voices()` (only voices whose
model file is actually present in `voice_models/` — see
`deploy/download_voice_models.sh`), speaking a short preview line
through `core/tts_worker.py` immediately on selection so the change is
heard, not just saved silently.
User info and module toggles remain a placeholder for a future
milestone.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.backup_manager import create_backup, is_backup_encrypted, restore_backup
from core.device_profile import CORE, HOME, get_device_profile
from core.logger import get_logger
from core.tts_worker import TTSWorker
from core.update_manager import apply_update_package, peek_update_manifest
from gui.backup_dialog import BackupPassphraseDialog
from gui.password_dialog import PasswordPromptDialog
from gui.theme_manager import THEME_DISPLAY_NAMES, THEMES
from modules.module_base import ModuleBase

log = get_logger(__name__)

_PROFILE_DISPLAY_NAMES = {CORE: "Core (Pi 5 + AI HAT+ 2)", HOME: "Home (desktop workstation)"}
_VOICE_PREVIEW_TEXT = "Hi, I'm M.I.A. This is what I sound like."


class SettingsModule(ModuleBase):
    module_id = "settings"
    display_name = "Settings"
    description = "Configure M.I.A. — theme, user info, module options."
    icon = "⚙"  # gear

    def __init__(self, context) -> None:
        super().__init__(context)
        self._status_label: QLabel | None = None
        self._tts_worker: Optional[TTSWorker] = None

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

        account_section = QLabel("Account")
        account_section.setObjectName("SettingsSectionHeader")
        outer.addWidget(account_section)

        active_profile = self.context.profiles.get_active_profile() if self.context.profiles else None
        account_desc = QLabel(
            f"Signed in as {active_profile.name}." if active_profile else "No active profile."
        )
        account_desc.setObjectName("SubtitleLabel")
        outer.addWidget(account_desc)

        switch_user_button = QPushButton("⇄ Switch User")
        switch_user_button.setObjectName("ModuleButton")
        switch_user_button.clicked.connect(self._on_switch_user_clicked)
        outer.addWidget(switch_user_button)

        appearance_section = QLabel("Appearance & Device Profile")
        appearance_section.setObjectName("SettingsSectionHeader")
        outer.addWidget(appearance_section)

        theme_row = QHBoxLayout()
        theme_row.addWidget(QLabel("Theme:"))
        self._theme_combo = QComboBox()
        for theme_id in THEMES:
            self._theme_combo.addItem(THEME_DISPLAY_NAMES[theme_id], theme_id)
        current_theme = self.context.config.get("gui.theme", "dark_field")
        index = self._theme_combo.findData(current_theme)
        if index != -1:
            self._theme_combo.setCurrentIndex(index)
        self._theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        theme_row.addWidget(self._theme_combo, stretch=1)
        outer.addLayout(theme_row)

        profile_row = QHBoxLayout()
        profile_row.addWidget(QLabel("Device Profile:"))
        self._profile_combo = QComboBox()
        for profile_id, display_name in _PROFILE_DISPLAY_NAMES.items():
            self._profile_combo.addItem(display_name, profile_id)
        index = self._profile_combo.findData(get_device_profile(self.context))
        if index != -1:
            self._profile_combo.setCurrentIndex(index)
        self._profile_combo.currentIndexChanged.connect(self._on_device_profile_changed)
        profile_row.addWidget(self._profile_combo, stretch=1)
        outer.addLayout(profile_row)

        profile_desc = QLabel(
            "Core is the resource-constrained field edition (Pi 5 + AI HAT+ 2); "
            "Home is the desktop workstation edition with more storage/resources."
        )
        profile_desc.setObjectName("SubtitleLabel")
        profile_desc.setWordWrap(True)
        outer.addWidget(profile_desc)

        voice_section = QLabel("Voice")
        voice_section.setObjectName("SettingsSectionHeader")
        outer.addWidget(voice_section)

        available_voices = self.context.voice.list_available_voices() if self.context.voice else []
        if not available_voices:
            no_voices_label = QLabel(
                "No voice models found — run deploy/download_voice_models.sh to fetch some."
            )
            no_voices_label.setObjectName("SubtitleLabel")
            no_voices_label.setWordWrap(True)
            outer.addWidget(no_voices_label)
        else:
            voice_row = QHBoxLayout()
            voice_row.addWidget(QLabel("Assistant Voice:"))
            self._voice_combo = QComboBox()
            for option in available_voices:
                self._voice_combo.addItem(option.display_name, option.voice_id)
            current_voice_id = self.context.voice.current_voice_id
            index = self._voice_combo.findData(current_voice_id)
            if index != -1:
                self._voice_combo.setCurrentIndex(index)
            self._voice_combo.currentIndexChanged.connect(self._on_voice_changed)
            voice_row.addWidget(self._voice_combo, stretch=1)
            outer.addLayout(voice_row)

            self._ai_effect_checkbox = QCheckBox("✨ AI Voice Effect")
            self._ai_effect_checkbox.setToolTip(
                "Subtle digital polish on M.I.A.'s voice — ring modulation + light chorus, "
                "tuned to stay clearly intelligible. Turn off for the plain Piper voice."
            )
            self._ai_effect_checkbox.setChecked(self.context.config.get("voice.ai_voice_effect", True))
            self._ai_effect_checkbox.toggled.connect(self._on_ai_voice_effect_toggled)
            outer.addWidget(self._ai_effect_checkbox)

        backup_section = QLabel("Backup & Restore")
        backup_section.setObjectName("SettingsSectionHeader")
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
        update_section.setObjectName("SettingsSectionHeader")
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
    # Account
    # ------------------------------------------------------------------

    def _on_switch_user_clicked(self) -> None:
        """
        2026-07-16: moved out of gui/main_window.py's header bar into
        Settings, at the user's explicit request. Modules can't import
        gui/ directly (CLAUDE.md's one-directional layering), so this
        publishes an event instead — MainWindow subscribes to
        "profile.switch_requested" and re-emits its own existing
        switch_profile_requested signal, same module-isolation pattern
        as the Assistant's open_module action.
        """
        self.context.events.publish("profile.switch_requested")

    # ------------------------------------------------------------------
    # Backup
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Appearance & Device Profile
    # ------------------------------------------------------------------

    def _on_theme_changed(self) -> None:
        theme_id = self._theme_combo.currentData()
        if theme_id is None:
            return
        self.context.config.set("gui.theme", theme_id)
        self.context.config.save()
        # Re-applied live at the QApplication level by
        # core.application.MIAApplication._on_theme_changed — no
        # restart required.
        self.context.events.publish("theme.changed", theme_id=theme_id)
        self._set_status(f"Theme changed to {THEME_DISPLAY_NAMES[theme_id]}.")

    def _on_device_profile_changed(self) -> None:
        profile_id = self._profile_combo.currentData()
        if profile_id is None:
            return
        self.context.config.set("system.device_profile", profile_id)
        self.context.config.save()
        self._set_status(f"Device profile changed to {_PROFILE_DISPLAY_NAMES[profile_id]}.")

    def _on_voice_changed(self) -> None:
        voice_id = self._voice_combo.currentData()
        if voice_id is None or self.context.voice is None:
            return
        if not self.context.voice.set_voice(voice_id):
            self._set_status(f"Could not switch voice — '{voice_id}' model file is missing.")
            return
        display_name = self._voice_combo.currentText()
        self._set_status(f"Voice changed to {display_name}.")
        self._speak_preview()

    def _on_ai_voice_effect_toggled(self, checked: bool) -> None:
        self.context.config.set("voice.ai_voice_effect", checked)
        self.context.config.save()
        self._set_status("AI Voice Effect " + ("on." if checked else "off."))
        self._speak_preview()

    def _speak_preview(self) -> None:
        if self.context.voice is None or self._tts_worker is not None:
            return
        output_path = Path(tempfile.gettempdir()) / "mia_voice_preview.wav"
        self._tts_worker = TTSWorker(self.context.voice, _VOICE_PREVIEW_TEXT, output_path)
        self._tts_worker.finished.connect(self._on_tts_finished)
        self._tts_worker.start()

    def _on_tts_finished(self) -> None:
        if self._tts_worker is not None:
            self._tts_worker.deleteLater()
            self._tts_worker = None

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
