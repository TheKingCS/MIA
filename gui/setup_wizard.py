"""
gui.setup_wizard
=================

First-time setup wizard: collects the user's name (and optionally the
email and password they sign in with) and confirms the system
date/time, then saves them via ConfigManager. MIA's setup questions
follow as a conversation (gui/onboarding_dialog.py).

Implemented as a QWizard (rather than a sequence of ad-hoc dialogs)
because QWizard gives us Back/Next/Finish flow, page validation, and a
consistent look for free — and because future versions will likely add
more first-run pages (e.g. choosing which modules to enable, or initial
storage location for data/) which QWizard accommodates without a
redesign.
"""

from __future__ import annotations

from PySide6.QtCore import QDate, QTime
from PySide6.QtWidgets import (
    QDateEdit,
    QLabel,
    QLineEdit,
    QTimeEdit,
    QVBoxLayout,
    QWizard,
    QWizardPage,
)

from core.app_context import AppContext
from core.logger import get_logger
from core.profile_manager import looks_like_email

log = get_logger(__name__)


class _WelcomePage(QWizardPage):
    """Collects the user's name, and optionally the email and password they
    sign in with (accounts, 2026-10-01)."""

    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Welcome to MIA")
        self.setSubTitle("Let's set up your system for the first time.")

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("What should MIA call you?"))

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Your name")
        layout.addWidget(self.name_edit)

        # Registering the field makes its value available via
        # wizard.field("user_name") from any page, and QWizard will
        # enforce that it's non-empty before allowing "Next".
        self.registerField("user_name*", self.name_edit)

        layout.addWidget(QLabel("Email to sign in with (optional):"))
        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("you@example.com")
        layout.addWidget(self.email_edit)
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setPlaceholderText("Password (optional without an email)")
        layout.addWidget(self.password_edit)
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #e06666;")
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)

    def validatePage(self) -> bool:  # noqa: N802 (Qt override signature)
        email = self.email_edit.text().strip()
        if email and not looks_like_email(email):
            self.error_label.setText("That doesn't look like an email address.")
            return False
        if email and not self.password_edit.text():
            self.error_label.setText("Signing in with an email needs a password too.")
            return False
        self.error_label.setText("")
        return True


class _DateTimePage(QWizardPage):
    """Confirms the system date and time to store alongside setup."""

    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Confirm Date & Time")
        self.setSubTitle("MIA uses this to timestamp your setup. Adjust if needed.")

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Date:"))
        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        layout.addWidget(self.date_edit)

        layout.addWidget(QLabel("Time:"))
        self.time_edit = QTimeEdit(QTime.currentTime())
        layout.addWidget(self.time_edit)


class SetupWizard(QWizard):
    """
    First-run wizard. On completion, writes user.name, user.setup_date,
    and user.setup_time into config and marks system.setup_complete.
    """

    def __init__(self, context: AppContext) -> None:
        super().__init__()
        self.context = context
        self.setWindowTitle("MIA — First-Time Setup")
        self.setFixedSize(520, 460)

        self._welcome_page = _WelcomePage()
        self._datetime_page = _DateTimePage()

        self.addPage(self._welcome_page)
        self.addPage(self._datetime_page)

        self.accepted.connect(self._save_setup)

    def _save_setup(self) -> None:
        name = self.field("user_name")
        date_str = self._datetime_page.date_edit.date().toString("yyyy-MM-dd")
        time_str = self._datetime_page.time_edit.time().toString("HH:mm")

        config = self.context.config
        config.set("system.setup_date", date_str)
        config.set("system.setup_time", time_str)

        # Creating the first profile also activates it and saves config,
        # so no separate config.save() call is needed here — see
        # core/profile_manager.py's create_profile().
        email = self._welcome_page.email_edit.text().strip()
        password = self._welcome_page.password_edit.text()
        profile = self.context.profiles.create_profile(
            name, password=password or None, make_active=True, email=email or None)
        if password:
            # Accounts (2026-10-01): the recovery code, shown once.
            from gui.account_dialogs import show_recovery_code

            show_recovery_code(self.context.profiles.issue_recovery_code(profile.profile_id), self)
        config.mark_setup_complete()  # also saves
        # "Getting to know you" (2026-10-01): MIA's setup questions, which
        # replaced the checkbox interview page; they fill in the interview
        # answers and pick which apps come first (gui/onboarding_dialog.py).
        from gui.onboarding_dialog import OnboardingDialog, module_names

        OnboardingDialog(self.context, profile, module_names(getattr(self.context, "module_manager", None)), self).exec()

        log.info("First-time setup complete for '%s' at %s %s", name, date_str, time_str)
        self.context.events.publish("user.setup_complete", name=name)
