"""
gui.profile_select
====================

Shown at boot when more than one profile exists (the "shared device"
case — e.g. a family using one MIA unit), and also reachable at any
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
from gui.account_dialogs import SignInDialog, show_recovery_code
from gui.add_profile_dialog import AddProfileDialog
from gui.password_dialog import prompt_for_password
from gui.onboarding_dialog import OnboardingDialog, module_names

log = get_logger(__name__)


class ProfileSelectScreen(QWidget):
    """Lets the user pick which profile to use for this session, add a new one, or delete one."""

    profile_selected = Signal()

    def __init__(self, context: AppContext) -> None:
        super().__init__()
        self.context = context
        self.setWindowTitle("MIA — Select Profile")
        self.resize(440, 520)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(14)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        title = QLabel("Who's using MIA?")
        title.setObjectName("TitleLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        self._list_container = QVBoxLayout()
        layout.addLayout(self._list_container)
        self._populate_profiles()

        sign_in_button = QPushButton("Sign in with email")
        sign_in_button.setObjectName("ModuleButton")
        sign_in_button.clicked.connect(self._on_sign_in_with_email)
        layout.addWidget(sign_in_button)

        add_button = QPushButton("+ New Profile")
        add_button.setObjectName("ModuleButton")
        add_button.clicked.connect(self._on_add_profile)
        layout.addWidget(add_button)
        layout.addStretch()

    def _populate_profiles(self) -> None:
        # Clear any existing rows before repopulating (used after
        # add/delete). hide()+setParent(None) before deleteLater() —
        # deleteLater() alone doesn't remove a widget from the screen
        # immediately, a real ghosting bug found via an actual
        # screenshot while building modules/toolbox/tools/
        # lite_captures_tool.py and fixed across this codebase's other
        # actively-re-triggered refresh methods the same day.
        while self._list_container.count():
            item = self._list_container.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
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
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()

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

    def _on_sign_in_with_email(self) -> None:
        dialog = SignInDialog(self.context, self)
        if dialog.exec() == SignInDialog.DialogCode.Accepted and dialog.profile is not None:
            self.context.profiles.set_active_profile(dialog.profile.profile_id)
            log.info("Signed in with email: %s", dialog.profile.profile_id)
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
        dialog = AddProfileDialog(self, context=self.context)
        if dialog.exec() == AddProfileDialog.DialogCode.Accepted and dialog.entered_name:
            password = dialog.entered_password or None
            profile = self.context.profiles.create_profile(
                dialog.entered_name, password=password, make_active=False, email=dialog.entered_email or None)
            # Accounts (2026-10-01): sharing a household only with its
            # member's approval (already checked in the dialog), and the
            # recovery code shown once.
            if dialog.household_choice is not None and not dialog.household_choice.apply(profile.profile_id):
                QMessageBox.warning(self, "Household", f"{profile.name} has a household of their own for now. "
                                    "They can join one later from Settings, Account & household.")
            if password:
                show_recovery_code(self.context.profiles.issue_recovery_code(profile.profile_id), self)
            # "Getting to know you" (2026-10-01, gui/onboarding_dialog.py):
            # MIA's setup questions, which replaced the checkbox interview.
            # Skipping is fine; every app keeps showing.
            OnboardingDialog(self.context, profile, module_names(getattr(self.context, "module_manager", None)),
                             self).exec()
            self._populate_profiles()
