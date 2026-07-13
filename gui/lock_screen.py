"""
gui.lock_screen
=================

Shown at boot only in one specific case: exactly one profile exists
AND it has a password set. Without this screen, the single-profile
fast boot path (straight to the main menu, no selector) would make a
profile password meaningless — there'd be no point in the boot flow
where it's ever actually checked. Multi-profile devices don't need
this screen; entering the wrong password there just means trying a
different profile button instead, and ProfileSelectScreen handles that
prompt itself, per-button.
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
        self.setWindowTitle("M.I.A. — Locked")
        self.resize(380, 280)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(14)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon = QLabel("\U0001F512")
        icon.setStyleSheet("font-size: 40px;")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel(f"Welcome back, {self.profile.name}")
        title.setObjectName("TitleLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

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

        layout.addWidget(icon)
        layout.addWidget(title)
        layout.addWidget(self.password_edit)
        layout.addWidget(self.error_label)
        layout.addWidget(unlock_button)

    def _try_unlock(self) -> None:
        password = self.password_edit.text()
        if self.context.profiles.verify_password(self.profile.profile_id, password):
            log.info("Profile '%s' unlocked.", self.profile.profile_id)
            self.unlocked.emit()
        else:
            self.error_label.setText("Incorrect password. Try again.")
            self.password_edit.clear()
            self.password_edit.setFocus()
