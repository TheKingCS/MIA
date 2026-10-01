"""
gui.account_dialogs
=====================

Accounts and households on the desktop (2026-10-01, docs/ROADMAP.md
"People and ownership"; core/profile_manager.py, core/household_manager.py):

- `RecoveryCodeDialog`: shows a new recovery code once, with Copy.
- `SignInDialog`: sign in with your email and password ("Forgot password?").
- `RecoverPasswordDialog`: a recovery code sets a new password.
- `HouseholdChoice`: "share household things with..." for a new account,
  approved by a current member typing their password.
- `AccountDialog`: your email, a new recovery code, and your household
  (who's in it, rename, join another, leave).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.profile_manager import AccountError

RECOVERY_WARNING = (
    "Write this down and keep it somewhere safe. If you forget your password, this code sets a new one. "
    "It's shown only now. It can't open your private journal: that passphrase can't be recovered by anyone."
)


def _password_field(placeholder: str) -> QLineEdit:
    field = QLineEdit()
    field.setEchoMode(QLineEdit.EchoMode.Password)
    field.setPlaceholderText(placeholder)
    return field


def _error_label() -> QLabel:
    label = QLabel("")
    label.setStyleSheet("color: #e06666;")
    label.setWordWrap(True)
    return label


class RecoveryCodeDialog(QDialog):
    def __init__(self, code: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Your recovery code")
        self.setMinimumWidth(380)
        layout = QVBoxLayout(self)
        code_label = QLabel(code)
        code_label.setObjectName("TitleLabel")
        code_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(code_label)
        warning = QLabel(RECOVERY_WARNING)
        warning.setWordWrap(True)
        layout.addWidget(warning)
        row = QHBoxLayout()
        copy = QPushButton("Copy")
        copy.clicked.connect(lambda: QGuiApplication.clipboard().setText(code))
        done = QPushButton("I've saved it")
        done.clicked.connect(self.accept)
        row.addWidget(copy)
        row.addWidget(done)
        layout.addLayout(row)


def show_recovery_code(code: Optional[str], parent=None) -> None:
    if code:
        RecoveryCodeDialog(code, parent).exec()


class RecoverPasswordDialog(QDialog):
    """Forgot your password: your email, your recovery code, a new password."""

    def __init__(self, context, identifier: str = "", parent=None) -> None:
        super().__init__(parent)
        self.context = context
        self.setWindowTitle("Forgot password")
        self.setMinimumWidth(360)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Use the recovery code you saved when you set your password."))
        self.identifier_edit = QLineEdit(identifier)
        self.identifier_edit.setPlaceholderText("Email (or name)")
        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText("Recovery code, e.g. K7QM-2XRP-9HTA-WC4E")
        self.new_edit = _password_field("New password")
        self.confirm_edit = _password_field("New password again")
        self.error_label = _error_label()
        for widget in (self.identifier_edit, self.code_edit, self.new_edit, self.confirm_edit, self.error_label):
            layout.addWidget(widget)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_accept(self) -> None:
        if not self.new_edit.text() or self.new_edit.text() != self.confirm_edit.text():
            self.error_label.setText("The new passwords don't match.")
            return
        fresh = self.context.profiles.reset_password_with_code(
            self.identifier_edit.text(), self.code_edit.text(), self.new_edit.text())
        if fresh is None:
            self.error_label.setText("That account and recovery code don't match.")
            return
        QMessageBox.information(self, "Password reset", "Your password is set. Here's your new recovery code; the old one no longer works.")
        show_recovery_code(fresh, self)
        self.accept()


class SignInDialog(QDialog):
    """Sign in with your email and password."""

    def __init__(self, context, parent=None) -> None:
        super().__init__(parent)
        self.context = context
        self.profile = None
        self.setWindowTitle("Sign in")
        self.setMinimumWidth(340)
        layout = QVBoxLayout(self)
        self.identifier_edit = QLineEdit()
        self.identifier_edit.setPlaceholderText("Email")
        self.password_edit = _password_field("Password")
        self.password_edit.returnPressed.connect(self._on_accept)
        self.error_label = _error_label()
        for widget in (self.identifier_edit, self.password_edit, self.error_label):
            layout.addWidget(widget)
        forgot = QPushButton("Forgot password?")
        forgot.setFlat(True)
        forgot.clicked.connect(self._on_forgot)
        layout.addWidget(forgot)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_accept(self) -> None:
        identifier = self.identifier_edit.text()
        found = self.context.profiles.find_for_sign_in(identifier)
        if found is not None and not found.has_password:
            self.error_label.setText(f"{found.name} has no password yet. Pick them from the list instead.")
            return
        profile = self.context.profiles.sign_in(identifier, self.password_edit.text())
        if profile is None:
            self.error_label.setText("That email and password don't match.")
            self.password_edit.clear()
            return
        self.profile = profile
        self.accept()

    def _on_forgot(self) -> None:
        RecoverPasswordDialog(self.context, self.identifier_edit.text(), self).exec()


class HouseholdChoice(QWidget):
    """For a new account: their own household (nothing shared, the default)
    or an existing one, approved by a member typing their password."""

    def __init__(self, context, parent=None) -> None:
        super().__init__(parent)
        self.context = context
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel("Share household things (calendar, kitchen, budget...) with:"))
        self.household_combo = QComboBox()
        self.household_combo.addItem("Nobody (their own household)", None)
        households = getattr(context, "households", None)
        for hid, name in (households.list_households() if households is not None else []):
            members = households.members(hid)
            if members:
                self.household_combo.addItem(f"{name} ({', '.join(p.name for p in members)})", hid)
        layout.addWidget(self.household_combo)
        self.approver_combo = QComboBox()
        self.approver_password = _password_field("Their password")
        self.approval_note = QLabel("Someone already in that household approves it:")
        for widget in (self.approval_note, self.approver_combo, self.approver_password):
            layout.addWidget(widget)
        self.household_combo.currentIndexChanged.connect(self._on_household_changed)
        self._on_household_changed()

    def _on_household_changed(self) -> None:
        hid = self.household_combo.currentData()
        self.approver_combo.clear()
        if hid:
            for member in self.context.households.members(hid):
                self.approver_combo.addItem(member.name, member.profile_id)
        for widget in (self.approval_note, self.approver_combo, self.approver_password):
            widget.setVisible(bool(hid))

    @property
    def household_id(self) -> Optional[str]:
        return self.household_combo.currentData()

    @property
    def approver_id(self) -> Optional[str]:
        return self.approver_combo.currentData()

    def approval_ok(self) -> bool:
        """Checked before the account is made, so a typo doesn't leave
        a half-made account."""
        if not self.household_id:
            return True
        return bool(self.approver_id) and self.context.profiles.verify_password(self.approver_id, self.approver_password.text())

    def apply(self, profile_id: str) -> bool:
        if not self.household_id:
            return True
        return self.context.households.join(profile_id, self.household_id, self.approver_id, self.approver_password.text())


class JoinHouseholdDialog(QDialog):
    def __init__(self, context, profile, parent=None) -> None:
        super().__init__(parent)
        self.context, self.profile = context, profile
        self.setWindowTitle("Join a household")
        self.setMinimumWidth(380)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("You'll share that household's things. Your own conversations, journal, "
                                "memories, notes and workouts stay yours."))
        self.choice = HouseholdChoice(context, self)
        own = context.households.household_of(profile.profile_id)
        index = self.choice.household_combo.findData(own)
        if index != -1:
            self.choice.household_combo.removeItem(index)
        layout.addWidget(self.choice)
        self.error_label = _error_label()
        layout.addWidget(self.error_label)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_accept(self) -> None:
        if not self.choice.household_id:
            self.reject()
            return
        if not self.choice.apply(self.profile.profile_id):
            self.error_label.setText("That password doesn't match.")
            return
        self.accept()


class AccountDialog(QDialog):
    """Your email, recovery code and household."""

    def __init__(self, context, profile, parent=None) -> None:
        super().__init__(parent)
        self.context, self.profile = context, profile
        self.setWindowTitle("Account & household")
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Email you sign in with (here and on your phone):"))
        email_row = QHBoxLayout()
        self.email_edit = QLineEdit(profile.email)
        self.email_edit.setPlaceholderText("you@example.com")
        save_email = QPushButton("Save")
        save_email.clicked.connect(self._on_save_email)
        email_row.addWidget(self.email_edit, stretch=1)
        email_row.addWidget(save_email)
        layout.addLayout(email_row)

        recovery = QPushButton("Make a new recovery code")
        recovery.setToolTip("Sets a new password if you forget yours. Any older code stops working.")
        recovery.clicked.connect(self._on_new_recovery_code)
        layout.addWidget(recovery)

        self.household_label = QLabel()
        self.household_label.setWordWrap(True)
        layout.addWidget(self.household_label)
        household_row = QHBoxLayout()
        rename = QPushButton("Rename household")
        rename.clicked.connect(self._on_rename_household)
        join = QPushButton("Join a household...")
        join.clicked.connect(self._on_join)
        self.leave_button = QPushButton("Leave this household")
        self.leave_button.clicked.connect(self._on_leave)
        for button in (rename, join, self.leave_button):
            household_row.addWidget(button)
        layout.addLayout(household_row)
        # Your data is yours (core/account_data.py).
        data_row = QHBoxLayout()
        export = QPushButton("Export my data...")
        export.clicked.connect(self._on_export)
        delete = QPushButton("Delete my account...")
        delete.clicked.connect(self._on_delete)
        data_row.addWidget(export)
        data_row.addWidget(delete)
        layout.addLayout(data_row)
        self.message_label = QLabel("")
        self.message_label.setWordWrap(True)
        layout.addWidget(self.message_label)
        close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close.rejected.connect(self.reject)
        layout.addWidget(close)
        self._show_household()

    def _show_household(self) -> None:
        households = self.context.households
        hid = households.household_of(self.profile.profile_id)
        others = households.shares_with(self.profile.profile_id)
        sharing = (f"You share it with {', '.join(p.name for p in others)}." if others
                   else "You don't share household things with anyone.")
        self.household_label.setText(f"Household: {households.name(hid)}. {sharing}")
        self.leave_button.setEnabled(bool(others))

    def _confirm_password(self) -> bool:
        if not self.profile.has_password:
            return True
        from gui.password_dialog import prompt_for_password

        cancelled, password = prompt_for_password(self.profile, parent=self, prompt="Enter your password,")
        if cancelled:
            return False
        if not self.context.profiles.verify_password(self.profile.profile_id, password):
            QMessageBox.warning(self, "Incorrect password", "That password doesn't match.")
            return False
        return True

    def _on_save_email(self) -> None:
        try:
            self.context.profiles.set_email(self.profile.profile_id, self.email_edit.text())
        except AccountError as exc:
            self.message_label.setText(str(exc))
            return
        self.message_label.setText("Saved. You can sign in with it.")

    def _on_new_recovery_code(self) -> None:
        if not self.profile.has_password:
            self.message_label.setText("Set a password first (Settings, Change Password); the code resets it.")
            return
        if self._confirm_password():
            show_recovery_code(self.context.profiles.issue_recovery_code(self.profile.profile_id), self)

    def _on_export(self) -> None:
        from PySide6.QtWidgets import QFileDialog

        from core.account_data import export_account

        folder = QFileDialog.getExistingDirectory(self, "Where should the export go?")
        if not folder:
            return
        shared = bool(self.context.households.shares_with(self.profile.profile_id))
        include = QMessageBox.question(
            self, "Export", "Include the household's shared things too (calendar, kitchen, budget...)?"
            + (" Others in your household will be in it too." if shared else "")
        ) == QMessageBox.StandardButton.Yes
        path = export_account(self.context, self.profile.profile_id, Path(folder), include_household=include)
        self.message_label.setText(f"Saved: {path}")

    def _on_delete(self) -> None:
        from PySide6.QtWidgets import QCheckBox, QInputDialog

        from core.account_data import delete_account

        if len(self.context.profiles.list_profiles()) <= 1:
            self.message_label.setText("This is the only account on this MIA, so it can't be deleted. "
                                       "You can still export your data.")
            return
        box = QMessageBox(self)
        box.setWindowTitle("Delete my account")
        box.setText(f"Delete {self.profile.name}'s account? Your conversations, memories, journal, notes and "
                    "settings go with it. Things you share with a household stay with the household.")
        erase = QCheckBox("Erase my data for good (otherwise it's archived on this device)")
        box.setCheckBox(erase)
        box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
        if box.exec() != QMessageBox.StandardButton.Yes:
            return
        password = ""
        if self.profile.has_password:
            password, ok = QInputDialog.getText(self, "Confirm", "Your password:", QLineEdit.EchoMode.Password)
            if not ok:
                return
        if not delete_account(self.context, self.profile.profile_id, password, erase=erase.isChecked()):
            self.message_label.setText("That password doesn't match.")
            return
        self.accept()
        self.context.events.publish("profile.switch_requested")

    def _on_rename_household(self) -> None:
        from PySide6.QtWidgets import QInputDialog

        households = self.context.households
        hid = households.household_of(self.profile.profile_id)
        name, ok = QInputDialog.getText(self, "Rename household", "Household name:", text=households.name(hid))
        if ok and households.rename(hid, name):
            self._show_household()

    def _on_join(self) -> None:
        if JoinHouseholdDialog(self.context, self.profile, self).exec() == QDialog.DialogCode.Accepted:
            self.message_label.setText("Joined. Your screens now show the household's things.")
            self._show_household()

    def _on_leave(self) -> None:
        confirm = QMessageBox.question(
            self, "Leave household",
            "Start a household of your own? The shared things (calendar, kitchen, budget...) stay with "
            "this household; your own things come with you.")
        if confirm != QMessageBox.StandardButton.Yes or not self._confirm_password():
            return
        if self.context.households.leave(self.profile.profile_id):
            self.message_label.setText("You have a household of your own now.")
            self._show_household()
