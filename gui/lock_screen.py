"""
gui.lock_screen
=================

Shown at boot in the single-profile case, either because that profile
has a password set (without this screen, the single-profile fast boot
path — straight to the main menu, no selector — would make a profile
password meaningless), or because the user has explicitly turned on
"Always show login screen" (`profile.always_show_login_screen`,
toggled from the profile-avatar menu in gui/main_window.py) even
without one. Multi-profile devices don't need this screen; entering
the wrong password there just means trying a different profile button
instead, and ProfileSelectScreen handles that prompt itself, per-button.

**2026-07-18**: a password-less profile with `always_show_login_screen`
on has nothing to actually verify — this screen degrades to a plain
"Welcome back, continue?" prompt for that case (no password field, no
error state, a "Continue" button that unlocks immediately), rather
than showing a password box that would just always be blank/pointless.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.app_context import AppContext
from core.logger import get_logger
from core.profile_manager import Profile

log = get_logger(__name__)


class LockScreen(QWidget):
    unlocked = Signal()

    def __init__(self, context: AppContext, profile: Profile) -> None:
        super().__init__()
        self.context = context
        self.profile = profile
        self.setWindowTitle("MIA — Locked")
        self.resize(380, 280)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(14)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon = QLabel("\U0001F512" if self.profile.has_password else "\U0001F44B")
        icon.setStyleSheet("font-size: 40px;")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel(f"Welcome back, {self.profile.name}")
        title.setObjectName("TitleLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(icon)
        layout.addWidget(title)

        # A password-less profile here only means "Always show login
        # screen" is on (core/application.py's _finish_boot()) — there's
        # nothing to actually verify, so this degrades to a plain
        # continue prompt instead of a pointless-always-blank password
        # box. self.password_edit/self.error_label are only created in
        # the has_password branch; _try_unlock() below checks
        # has_password first, so it never touches them otherwise.
        if self.profile.has_password:
            self.password_edit = QLineEdit()
            self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self.password_edit.setPlaceholderText("Password")
            self.password_edit.returnPressed.connect(self._try_unlock)

            self.error_label = QLabel("")
            self.error_label.setStyleSheet("color: #e06666;")
            self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

            unlock_button = QPushButton("Unlock")
            unlock_button.setObjectName("ModuleButton")
            unlock_button.clicked.connect(self._try_unlock)

            layout.addWidget(self.password_edit)
            layout.addWidget(self.error_label)
            layout.addWidget(unlock_button)
        else:
            continue_button = QPushButton("Continue")
            continue_button.setObjectName("ModuleButton")
            continue_button.clicked.connect(self.unlocked.emit)
            layout.addWidget(continue_button)

    def _try_unlock(self) -> None:
        password = self.password_edit.text()
        if self.context.profiles.verify_password(self.profile.profile_id, password):
            log.info("Profile '%s' unlocked.", self.profile.profile_id)
            self.unlocked.emit()
        else:
            self.error_label.setText("Incorrect password. Try again.")
            self.password_edit.clear()
            self.password_edit.setFocus()
