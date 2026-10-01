"""
gui.setup_wizard
=================

First-time setup wizard: collects the user's name and confirms the
system date/time, then saves them via ConfigManager.

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
from gui.widgets.interview_form import InterviewForm

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


class _InterviewPage(QWizardPage):
    """Profile-creation interview (2026-09-14) — see
    gui/widgets/interview_form.py's own docstring for the full design.
    Wired here, not just in the later "Add Profile" flow, since a
    first-run profile is created right when this wizard finishes —
    same moment, no separate second dialog needed for the very first
    profile."""

    def __init__(self, context: AppContext) -> None:
        super().__init__()
        self.setTitle("Tell MIA About You")
        self.setSubTitle("Optional — helps MIA suggest things that actually fit your life.")
        layout = QVBoxLayout(self)
        self.form = InterviewForm(context)
        layout.addWidget(self.form)

    def initializePage(self) -> None:  # noqa: N802 (Qt override signature)
        # Re-reads the name field once this page is actually shown, so
        # the greeting uses the real name typed on the earlier Welcome
        # page rather than "" at construction time (this page is built
        # before the user has typed anything).
        self.form.set_profile_name(self.field("user_name") or "")


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
        self._interview_page = _InterviewPage(context)

        self.addPage(self._welcome_page)
        self.addPage(self._datetime_page)
        self.addPage(self._interview_page)

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
        # Profile-creation interview (2026-09-14) — optional, so an
        # empty interests list / blank notes is a real, valid answer
        # ("skipped"), not an error; still saved so downstream code
        # never has to guess "never asked" vs. "asked, said nothing."
        self.context.profiles.set_interview_answers(
            profile.profile_id, self._interview_page.form.selected_interests(), self._interview_page.form.entered_notes(),
        )
        config.mark_setup_complete()  # also saves

        log.info("First-time setup complete for '%s' at %s %s", name, date_str, time_str)
        self.context.events.publish("user.setup_complete", name=name)
