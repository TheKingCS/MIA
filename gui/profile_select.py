"""
gui.profile_select
====================

Shown at boot when more than one profile exists (the "shared device"
case — e.g. a family using one M.I.A. unit), and also reachable at any
time via the "Switch User" button in the main window header — that
path always shows this screen regardless of profile count, since it's
also how a second profile gets added in the first place.

Password-protected profiles are gated here: clicking one prompts for
its password before activating it, rather than trusting the button
click alone.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.app_context import AppContext
from core.logger import get_logger
from gui.add_profile_dialog import AddProfileDialog
from gui.password_dialog import prompt_for_password

log = get_logger(__name__)


class ProfileSelectScreen(QWidget):
    """Lets the user pick which profile to use for this session, add a new one, or delete one."""

    profile_selected = Signal()

    def __init__(self, context: AppContext) -> None:
        super().__init__()
        self.context = context
        self.setWindowTitle("M.I.A. — Select Profile")
        self.resize(440, 520)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(14)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        title = QLabel("Who's using M.I.A.?")
        title.setObjectName("TitleLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        self._list_container = QVBoxLayout()
        layout.addLayout(self._list_container)
        self._populate_profiles()

        add_button = QPushButton("+ New Profile")
        add_button.setObjectName("ModuleButton")
        add_button.clicked.connect(self._on_add_profile)
        layout.addWidget(add_button)
        layout.addStretch()

    def _populate_profiles(self) -> None:
        # Clear any existing rows before repopulating (used after add/delete).
        while self._list_container.count():
            item = self._list_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

        all_profiles = self.context.profiles.list_profiles()
        only_one_left = len(all_profiles) <= 1

        for profile in all_profiles:
            row = QHBoxLayout()

            label = "\U0001F464 \U0001F512 " if profile.has_password else "\U0001F464   "
            select_button = QPushButton(f"{label}{profile.name}")
            select_button.setObjectName("ModuleButton")
            select_button.setMinimumHeight(60)
            select_button.clicked.connect(lambda checked=False, p=profile: self._on_profile_chosen(p))
            row.addWidget(select_button, stretch=3)

            delete_button = QPushButton("\U0001F5D1 Delete")
            delete_button.setToolTip(
                "Can't delete the only remaining profile" if only_one_left else f"Delete {profile.name}"
            )
            delete_button.setEnabled(not only_one_left)
            delete_button.setMinimumHeight(60)
            delete_button.clicked.connect(lambda checked=False, p=profile: self._on_delete_requested(p))
            row.addWidget(delete_button, stretch=2)

            self._list_container.addLayout(row)

    @staticmethod
    def _clear_layout(layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _on_profile_chosen(self, profile) -> None:
        if profile.has_password:
            cancelled, password = prompt_for_password(profile, parent=self)
            if cancelled:
                return
            if not self.context.profiles.verify_password(profile.profile_id, password):
                QMessageBox.warning(self, "Incorrect Password", f"That password doesn't match {profile.name}.")
                return

        self.context.profiles.set_active_profile(profile.profile_id)
        log.info("Profile selected: %s", profile.profile_id)
        self.profile_selected.emit()

    def _on_delete_requested(self, profile) -> None:
        confirm = QMessageBox.question(
            self,
            "Delete Profile",
            f"Delete the profile '{profile.name}'?\n\n"
            "Its data will be archived, not permanently erased.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        password = None
        if profile.has_password:
            cancelled, entered = prompt_for_password(profile, parent=self, prompt="Enter password to delete")
            if cancelled:
                return
            password = entered

        success = self.context.profiles.delete_profile(profile.profile_id, password=password)
        if not success:
            QMessageBox.warning(
                self,
                "Couldn't Delete Profile",
                "That profile couldn't be deleted — either the password was "
                "incorrect, or it's the only remaining profile on this device.",
            )
            return

        self._populate_profiles()

    def _on_add_profile(self) -> None:
        dialog = AddProfileDialog(self)
        if dialog.exec() == AddProfileDialog.DialogCode.Accepted and dialog.entered_name:
            password = dialog.entered_password or None
            self.context.profiles.create_profile(dialog.entered_name, password=password, make_active=False)
            self._populate_profiles()
