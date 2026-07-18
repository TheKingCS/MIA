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

log = get_logger(__name__)


class _WelcomePage(QWizardPage):
    """Collects the user's name."""

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
        self.setFixedSize(480, 320)

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
        self.context.profiles.create_profile(name, make_active=True)
        config.mark_setup_complete()  # also saves

        log.info("First-time setup complete for '%s' at %s %s", name, date_str, time_str)
        self.context.events.publish("user.setup_complete", name=name)
