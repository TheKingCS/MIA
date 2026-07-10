"""
core.application
=================

MIAApplication: the orchestrator that boots the system.

This class is the one place that knows the *order* things happen in:
create Qt app -> show splash -> init core services -> discover modules
-> decide first-run vs normal boot -> show the right window. Keeping
this sequencing in one class (rather than spread across main.py) means
main.py can stay a two-line entry point forever, which matters because
main.py is the first file every new contributor reads.

main.py should never import PySide6 widgets directly or contain any
startup logic — it only constructs and runs MIAApplication.
"""

from __future__ import annotations

import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.logger import get_logger
from core.module_manager import ModuleManager
from gui.main_window import MainWindow
from gui.setup_wizard import SetupWizard
from gui.splash_screen import SplashScreen

log = get_logger(__name__)


class MIAApplication:
    """Owns the Qt application object and the startup sequence."""

    def __init__(self) -> None:
        self.qt_app = QApplication(sys.argv)
        self.qt_app.setApplicationName("M.I.A.")

        self.config = ConfigManager()
        self.events = EventBus()
        self.context = AppContext(config=self.config, events=self.events)
        self.module_manager = ModuleManager(self.context)

        self.splash: SplashScreen | None = None
        self.main_window: MainWindow | None = None
        self.setup_wizard: SetupWizard | None = None

    def run(self) -> int:
        """Start the boot sequence and enter the Qt event loop."""
        log.info("M.I.A. starting up (version %s)", self.config.get("system.version"))

        self.splash = SplashScreen()
        self.splash.show()

        # The splash screen steps through a short sequence of boot
        # messages before handing off to the wizard or main window. Using
        # a QTimer chain (rather than time.sleep) keeps the GUI responsive
        # during startup instead of freezing.
        boot_steps = [
            ("Initializing Core...", self._noop),
            ("Loading Configuration...", self._noop),
            ("Discovering Modules...", self.module_manager.discover),
            ("Starting Interface...", self._noop),
        ]
        self._run_boot_steps(boot_steps, index=0)

        return self.qt_app.exec()

    def _run_boot_steps(self, steps: list[tuple[str, callable]], index: int) -> None:
        if index >= len(steps):
            self._finish_boot()
            return

        message, action = steps[index]
        self.splash.set_status(message)
        try:
            action()
        except Exception:
            log.exception("Error during boot step: %s", message)

        QTimer.singleShot(350, lambda: self._run_boot_steps(steps, index + 1))

    def _finish_boot(self) -> None:
        if self.config.is_first_run:
            log.info("First run detected — launching setup wizard.")
            self.setup_wizard = SetupWizard(self.context)
            self.setup_wizard.finished.connect(self._on_setup_finished)
            self.splash.close()
            self.setup_wizard.show()
        else:
            self._show_main_window()

    def _on_setup_finished(self) -> None:
        self._show_main_window()

    def _show_main_window(self) -> None:
        if self.splash is not None:
            self.splash.close()
        self.main_window = MainWindow(self.context, self.module_manager)
        self.main_window.show()

    @staticmethod
    def _noop() -> None:
        pass
