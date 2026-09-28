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
through different voices for MIA"): a dropdown over
`core/voice_manager.py`'s `list_available_voices()` (only voices whose
model file is actually present in `voice_models/` — see
`deploy/download_voice_models.sh`), speaking a short preview line
through `core/tts_worker.py` immediately on selection so the change is
heard, not just saved silently.

Module toggles live on the Modules screen instead
(modules/module_browser/module.py, via ModuleManager.set_enabled()) —
not duplicated here. Account (2026-09-10) closes the "user info is a
placeholder" gap that remained: Rename Profile
(core.profile_manager.rename_profile()) and Change Password reuse
gui/password_dialog.py's prompt_for_password()/verify_password() to
confirm the CURRENT password first (same two-call pattern
gui/profile_select.py's own profile-switch login flow already uses)
before ever showing a "set a new one" field — core/profile_manager.py's
existing set_password() (no verification of its own — it's also the
raw primitive create_profile() uses, where there's no old password to
check) does the actual set/remove.
"""

from __future__ import annotations

import tempfile
import time
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.backup_manager import create_backup, is_backup_encrypted, restore_backup
from core.device_profile import CORE, HOME, get_device_profile
from core.logger import get_logger
from core.phone_server import DEFAULT_PORT, describe_status, serve_command, tailscale_info
from core.tts_worker import TTSWorker
from core.voice_manager import DEFAULT_PLAYBACK_VOLUME, MAX_PLAYBACK_VOLUME, MIN_PLAYBACK_VOLUME
from core.update_manager import apply_update_package, peek_update_manifest
from gui.backup_dialog import BackupPassphraseDialog
from gui.password_dialog import PasswordPromptDialog, prompt_for_password
from gui.rename_profile_dialog import RenameProfileDialog
from gui.set_password_dialog import SetPasswordDialog
from gui.theme_manager import THEME_DISPLAY_NAMES, THEMES
from modules.module_base import ModuleBase

log = get_logger(__name__)

_PROFILE_DISPLAY_NAMES = {CORE: "Core (Pi 5 + AI HAT+ 2)", HOME: "Home (desktop workstation)"}
_VOICE_PREVIEW_TEXT = "Hi, I'm MIA This is what I sound like."


class SettingsModule(ModuleBase):
    module_id = "settings"
    display_name = "Settings"
    description = "Configure MIA — theme, user info, module options."
    icon = "⚙"  # gear

    def __init__(self, context) -> None:
        super().__init__(context)
        self._status_label: QLabel | None = None
        self._tts_worker: Optional[TTSWorker] = None
        self._account_desc_label: Optional[QLabel] = None

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
        self._account_desc_label = QLabel(
            f"Signed in as {active_profile.name}." if active_profile else "No active profile."
        )
        self._account_desc_label.setObjectName("SubtitleLabel")
        outer.addWidget(self._account_desc_label)

        switch_user_button = QPushButton("⇄ Switch User")
        switch_user_button.setObjectName("ModuleButton")
        switch_user_button.clicked.connect(self._on_switch_user_clicked)
        outer.addWidget(switch_user_button)

        rename_profile_button = QPushButton("Rename Profile")
        rename_profile_button.setObjectName("ModuleButton")
        rename_profile_button.clicked.connect(self._on_rename_profile_clicked)
        outer.addWidget(rename_profile_button)

        change_password_button = QPushButton("Change Password")
        change_password_button.setObjectName("ModuleButton")
        change_password_button.clicked.connect(self._on_change_password_clicked)
        outer.addWidget(change_password_button)

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
                "Subtle digital polish on MIA's voice — ring modulation + light chorus, "
                "tuned to stay clearly intelligible. Turn off for the plain Piper voice."
            )
            self._ai_effect_checkbox.setChecked(self.context.config.get("voice.ai_voice_effect", True))
            self._ai_effect_checkbox.toggled.connect(self._on_ai_voice_effect_toggled)
            outer.addWidget(self._ai_effect_checkbox)

            volume_row = QHBoxLayout()
            volume_row.addWidget(QLabel("Assistant Volume:"))
            self._volume_slider = QSlider(Qt.Orientation.Horizontal)
            self._volume_slider.setRange(int(MIN_PLAYBACK_VOLUME * 100), int(MAX_PLAYBACK_VOLUME * 100))
            current_volume = self.context.config.get("voice.playback_volume", DEFAULT_PLAYBACK_VOLUME)
            self._volume_slider.setValue(round(current_volume * 100))
            self._volume_slider.setToolTip("How loud MIA's spoken replies play — a plain playback gain, separate from system volume.")
            self._volume_slider.valueChanged.connect(self._on_volume_slider_moved)
            self._volume_slider.sliderReleased.connect(self._on_volume_slider_released)
            volume_row.addWidget(self._volume_slider, stretch=1)
            self._volume_value_label = QLabel(f"{self._volume_slider.value()}%")
            volume_row.addWidget(self._volume_value_label)
            outer.addLayout(volume_row)

        # Cognitive Extension slice A: the safety floor (core/safety_floor.py)
        # always gives 988 and 911; this adds a person of the owner's choosing.
        support_section = QLabel("Support & Safety")
        support_section.setObjectName("SettingsSectionHeader")
        outer.addWidget(support_section)
        support_desc = QLabel(
            "If you ever tell MIA you're thinking of hurting yourself or you're in danger, she gives you "
            "988 (call or text) and 911. Add someone you trust and she'll name them too."
        )
        support_desc.setObjectName("SubtitleLabel")
        support_desc.setWordWrap(True)
        outer.addWidget(support_desc)
        contact_row = QHBoxLayout()
        contact_row.addWidget(QLabel("Trusted person:"))
        self._trusted_contact_edit = QLineEdit(self.context.config.get("assistant.safety.trusted_contact", "") or "")
        self._trusted_contact_edit.setPlaceholderText("e.g. my brother Josh, 555-0142")
        self._trusted_contact_edit.editingFinished.connect(self._on_trusted_contact_changed)
        contact_row.addWidget(self._trusted_contact_edit, stretch=1)
        outer.addLayout(contact_row)

        # Cognitive Extension slice C: how often MIA speaks up on her own
        # (core/communication_gate.py).
        speak_section = QLabel("When MIA Speaks Up")
        speak_section.setObjectName("SettingsSectionHeader")
        outer.addWidget(speak_section)
        speak_desc = QLabel(
            "Her own messages (calendar, budget, check-ins, suggestions) are combined and limited per day. "
            "Urgent things, alarms you set and answers to you don't count. Ask her \"what didn't you tell me "
            "today?\" to see what she held back."
        )
        speak_desc.setObjectName("SubtitleLabel")
        speak_desc.setWordWrap(True)
        outer.addWidget(speak_desc)
        speak_row = QHBoxLayout()
        speak_row.addWidget(QLabel("Messages per day, at most:"))
        self._daily_budget_spin = QSpinBox()
        self._daily_budget_spin.setRange(1, 20)
        self._daily_budget_spin.setValue(int(self.context.config.get("communication.daily_budget", 5)))
        self._daily_budget_spin.valueChanged.connect(self._on_daily_budget_changed)
        speak_row.addWidget(self._daily_budget_spin)
        speak_row.addStretch(1)
        outer.addLayout(speak_row)

        self._build_phone_section(outer)

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
            "This modifies MIA's own application files directly — "
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

    def _on_rename_profile_clicked(self) -> None:
        profile = self.context.profiles.get_active_profile() if self.context.profiles else None
        if profile is None:
            QMessageBox.information(None, "No Active Profile", "There's no active profile to rename.")
            return

        dialog = RenameProfileDialog(current_name=profile.name)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.context.profiles.rename_profile(profile.profile_id, dialog.entered_name)
        self._account_desc_label.setText(f"Signed in as {dialog.entered_name}.")

    def _on_change_password_clicked(self) -> None:
        """Verifies the CURRENT password first (same two-call
        prompt_for_password()/verify_password() pattern
        gui/profile_select.py's own profile-switch login flow already
        uses) before ever showing SetPasswordDialog — a wrong current
        password never reaches the "set a new one" step."""
        profile = self.context.profiles.get_active_profile() if self.context.profiles else None
        if profile is None:
            QMessageBox.information(None, "No Active Profile", "There's no active profile to update.")
            return

        current_password = ""
        if profile.has_password:
            cancelled, current_password = prompt_for_password(profile, prompt="Enter current password for")
            if cancelled:
                return
            if not self.context.profiles.verify_password(profile.profile_id, current_password):
                QMessageBox.warning(None, "Incorrect Password", "That password doesn't match your current one.")
                return

        dialog = SetPasswordDialog(has_password=profile.has_password)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        if not dialog.entered_wants_password:
            if profile.has_password:
                self.context.profiles.set_password(profile.profile_id, None)
                QMessageBox.information(None, "Password Removed", "Password protection removed.")
            return

        new_password = dialog.entered_new_password or current_password
        self.context.profiles.set_password(profile.profile_id, new_password)
        QMessageBox.information(None, "Password Updated", "Password updated.")

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

    # ------------------------------------------------------------------
    # Phone access (core/phone_server.py)
    # ------------------------------------------------------------------

    def _build_phone_section(self, outer: QVBoxLayout) -> None:
        phone_section = QLabel("Phone Access")
        phone_section.setObjectName("SettingsSectionHeader")
        outer.addWidget(phone_section)
        phone_desc = QLabel(
            "Talk to MIA from your phone (the phone web app or the Android app) through Tailscale. "
            "Full steps: docs/PHONE_VOICE_SETUP.md."
        )
        phone_desc.setObjectName("SubtitleLabel")
        phone_desc.setWordWrap(True)
        outer.addWidget(phone_desc)
        self._phone_checkbox = QCheckBox("Let my phone reach MIA")
        server = self.context.phone_server
        self._phone_checkbox.setChecked(bool(server and server.enabled))
        self._phone_checkbox.setEnabled(server is not None)
        self._phone_checkbox.toggled.connect(self._on_phone_toggled)
        outer.addWidget(self._phone_checkbox)
        self._phone_status_label = QLabel("")
        self._phone_status_label.setWordWrap(True)
        self._phone_status_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        outer.addWidget(self._phone_status_label)
        phone_buttons = QHBoxLayout()
        check_button = QPushButton("Check Again")
        check_button.clicked.connect(self._refresh_phone_status)
        phone_buttons.addWidget(check_button)
        self._copy_serve_button = QPushButton("Copy Tailscale Command")
        self._copy_serve_button.setToolTip("Copies the one-time command that lets Tailscale forward your phone to MIA.")
        self._copy_serve_button.clicked.connect(self._on_copy_serve_command)
        phone_buttons.addWidget(self._copy_serve_button)
        phone_buttons.addStretch(1)
        outer.addLayout(phone_buttons)
        self._refresh_phone_status()

    def _on_phone_toggled(self, checked: bool) -> None:
        server = self.context.phone_server
        if server is None:
            return
        self._phone_status_label.setText("Starting…" if checked else "Stopping…")
        QApplication.processEvents()
        server.set_enabled(checked)
        self._refresh_phone_status()

    def _refresh_phone_status(self) -> None:
        server = self.context.phone_server
        if server is None:
            self._phone_status_label.setText("Phone access isn't available in this mode.")
            self._copy_serve_button.setVisible(False)
            return
        status = server.status()
        tailscale = tailscale_info(status.port) if status.enabled else None
        self._phone_status_label.setText("\n".join(describe_status(status, tailscale, time.time())))
        self._copy_serve_button.setVisible(bool(tailscale and tailscale.running and not tailscale.serving_mia))

    def _on_copy_serve_command(self) -> None:
        server = self.context.phone_server
        port = server.port if server is not None else DEFAULT_PORT
        QApplication.clipboard().setText(serve_command(port))
        self._phone_status_label.setText(
            self._phone_status_label.text() + "\nCopied. Paste it into a terminal, then press Check Again."
        )

    def _on_daily_budget_changed(self, value: int) -> None:
        self.context.config.set("communication.daily_budget", int(value))
        self.context.config.save()

    def _on_trusted_contact_changed(self) -> None:
        self.context.config.set("assistant.safety.trusted_contact", self._trusted_contact_edit.text().strip())
        self.context.config.save()

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

    def _on_volume_slider_moved(self, value: int) -> None:
        # Just updates the live "N%" label while dragging — the actual
        # save + spoken preview only happens on release (see below), so
        # dragging the slider doesn't re-synthesize/replay on every tick.
        self._volume_value_label.setText(f"{value}%")

    def _on_volume_slider_released(self) -> None:
        volume = self._volume_slider.value() / 100.0
        self.context.config.set("voice.playback_volume", volume)
        self.context.config.save()
        self._set_status(f"Assistant volume set to {self._volume_slider.value()}%.")
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
        file_filter = "MIA Backup (*.miabackup)" if passphrase else "MIA Backup (*.zip)"
        destination, _ = QFileDialog.getSaveFileName(None, "Save Backup As", default_path, file_filter)
        if not destination:
            return

        result = create_backup(Path(destination), passphrase=passphrase or None, config=self.context.config)
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
            None, "Select Backup File", "", "MIA Backup (*.zip *.miabackup);;All Files (*)"
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
            "(profiles, notifications, trip photos, trail maps, field "
            "captures, etc.) with the contents of this backup. This "
            "cannot be undone.\n\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        result = restore_backup(source_path, passphrase=passphrase, config=self.context.config)
        if result.passed:
            QMessageBox.information(
                None, "Restore Complete",
                "Restore complete. Please restart MIA for the changes to take effect."
            )
            self._set_status("Restore complete — restart MIA to apply.")
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
            None, "Select Update Package", "", "MIA Update Package (*.zip);;All Files (*)"
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
            "Applying this update will overwrite MIA's own application "
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
                "Please restart MIA for the changes to take effect."
            )
            self._set_status(f"Update applied ({len(result.applied_files)} file(s)) — restart MIA to apply.")
        else:
            QMessageBox.warning(None, "Update Failed", "\n".join(result.errors))
            self._set_status("Update failed — see error dialog.")
