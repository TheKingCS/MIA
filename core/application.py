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
from datetime import datetime

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from core.alarm_manager import AlarmManager
from core.app_context import AppContext
from core.calendar_manager import CalendarManager
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.inventory_manager import InventoryManager
from core.journal_manager import JournalManager
from core.logger import get_logger
from core.module_manager import ModuleManager
from core.notification_manager import NotificationManager
from core.profile_manager import ProfileManager
from core.reference_library_manager import ReferenceLibraryManager
from core.search_manager import SearchManager, SearchResult
from gui.lock_screen import LockScreen
from gui.main_window import MainWindow
from gui.profile_select import ProfileSelectScreen
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
        # ProfileManager needs the context to already exist (it reads/
        # writes config through it), so it's attached right after
        # construction rather than passed into AppContext's constructor.
        # Its __init__ also runs the legacy-user migration — see
        # core/profile_manager.py.
        self.context.profiles = ProfileManager(self.context)
        self.context.notifications = NotificationManager(self.context)
        self.context.calendar = CalendarManager(self.context)
        self.context.alarms = AlarmManager(self.context)
        self.context.journal = JournalManager(self.context)
        self.context.inventory = InventoryManager(self.context)
        self.context.reference_library = ReferenceLibraryManager(self.context)
        self.module_manager = ModuleManager(self.context)
        self.context.search = SearchManager(self.context)
        self._register_search_providers()
        self._register_calculators()

        self.splash: SplashScreen | None = None
        self.main_window: MainWindow | None = None
        self.setup_wizard: SetupWizard | None = None
        self.profile_select: ProfileSelectScreen | None = None
        self.lock_screen: LockScreen | None = None

        # Alarms need to fire regardless of which module is currently on
        # screen, so this timer lives here (the one place that's always
        # alive for the whole app session) rather than inside the Alarm
        # tool's widget, which only exists while that screen is open.
        # 20s is frequent enough that no HH:MM minute window is ever
        # skipped between polls.
        self._alarm_check_timer = QTimer()
        self._alarm_check_timer.timeout.connect(self._check_alarms)
        self._alarm_check_timer.start(20_000)

    def _check_alarms(self) -> None:
        self.context.alarms.check_due(datetime.now())

    def _display(self, widget) -> None:
        """
        Show a top-level screen, going fullscreen if kiosk_mode is on.

        This is the single place kiosk-mode display behavior lives.
        Previously, only MainWindow applied fullscreen (in its own
        showEvent), which meant kiosk mode silently dropped the moment
        you left MainWindow — the lock screen, profile selector, and
        setup wizard all just called plain .show(). Routing every
        screen transition through this one method is what makes
        fullscreen actually persist across the whole boot/switch flow,
        not just within MainWindow.
        """
        if self.config.get("system.kiosk_mode", False):
            widget.showFullScreen()
        else:
            widget.show()

    def _register_search_providers(self) -> None:
        """
        Register the two search providers available from day one:
        modules (so typing "map" finds and opens the Maps module) and
        profiles (so typing a name finds that profile to switch to).
        Both are registered here, in the orchestrator, rather than
        inside ModuleManager/ProfileManager themselves — those services
        shouldn't need to know search exists at all; this is the one
        place that wires independent core services together.
        """
        self.context.search.register_provider("modules", self._search_modules)
        self.context.search.register_provider("profiles", self._search_profiles)

    def _register_calculators(self) -> None:
        """
        Register the general-purpose calculators that ship with core
        (Unit Converter, Ohm's Law) — they have no single obvious
        module home, so they're registered here rather than inside a
        specific module's on_load(). A domain-specific module (e.g. a
        future Electronics module) can register its own calculators
        into the same self.context.calculators from its own on_load()
        without needing any change here.
        """
        from modules.toolbox.calculators.ohms_law import OhmsLawCalculator
        from modules.toolbox.calculators.unit_converter import UnitConverterCalculator

        self.context.calculators.register(UnitConverterCalculator())
        self.context.calculators.register(OhmsLawCalculator())

    def _search_modules(self, query: str) -> list[SearchResult]:
        query_lower = query.lower()
        results = []
        for module in self.module_manager.all():
            haystack = f"{module.display_name} {module.description} {module.module_id}".lower()
            if query_lower in haystack:
                results.append(SearchResult(
                    title=module.display_name,
                    description=module.description or "Open this module",
                    source="Modules",
                    action_type="open_module",
                    action_target=module.module_id,
                ))
        return results

    def _search_profiles(self, query: str) -> list[SearchResult]:
        query_lower = query.lower()
        results = []
        for profile in self.context.profiles.list_profiles():
            if query_lower in profile.name.lower():
                results.append(SearchResult(
                    title=profile.name,
                    description="Switch to this profile",
                    source="Profiles",
                    action_type="switch_profile",
                    action_target=profile.profile_id,
                ))
        return results

    def run(self) -> int:
        """Start the boot sequence and enter the Qt event loop."""
        log.info("M.I.A. starting up (version %s)", self.config.get("system.version"))

        self.splash = SplashScreen()
        self._display(self.splash)

        # The splash screen steps through a short sequence of boot
        # messages before handing off to the wizard or main window. Using
        # a QTimer chain (rather than time.sleep) keeps the GUI responsive
        # during startup instead of freezing.
        boot_steps = [
            ("INITIALIZING CORE SYSTEMS...", self._noop),
            ("SYNCING CONFIGURATION MATRIX...", self._noop),
            ("SCANNING MODULE ARRAY...", self.module_manager.discover),
            ("ENGAGING INTERFACE...", self._noop),
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

        # 1400ms/step (5.6s total for the 4 steps below) — gives the
        # splash's pulsing core (gui/boot_core_widget.py) a couple of
        # full breathing cycles per step; the original 350ms made the
        # animation flash by too fast to register.
        QTimer.singleShot(1400, lambda: self._run_boot_steps(steps, index + 1))

    def _finish_boot(self) -> None:
        if self.config.is_first_run:
            log.info("First run detected — launching setup wizard.")
            self.setup_wizard = SetupWizard(self.context)
            self.setup_wizard.finished.connect(self._on_setup_finished)
            self.splash.close()
            self._display(self.setup_wizard)
            return

        profiles = self.context.profiles
        if not profiles.has_any_profiles():
            # Edge case: setup was previously marked complete but no
            # profile exists (e.g. manual config editing). Fall back to
            # the wizard rather than booting into a nameless main window.
            log.warning("setup_complete is set but no profiles exist — re-running setup wizard.")
            self.setup_wizard = SetupWizard(self.context)
            self.setup_wizard.finished.connect(self._on_setup_finished)
            self.splash.close()
            self._display(self.setup_wizard)
            return

        if profiles.needs_profile_selection():
            log.info("Multiple profiles found — showing profile selector.")
            self.profile_select = ProfileSelectScreen(self.context)
            self.profile_select.profile_selected.connect(self._on_profile_selected)
            self.splash.close()
            self._display(self.profile_select)
            return

        # Exactly one profile — auto-activate it if it isn't already
        # (e.g. right after the legacy-user migration ran). This is the
        # common single-user case, and it should never be interrupted
        # by the profile *selector* screen. But if this one profile has
        # a password, we still need to gate entry — otherwise setting a
        # password on a single-profile device would do nothing at all,
        # since the selector (where passwords are normally checked)
        # would never appear.
        if profiles.get_active_profile() is None:
            only_profile = profiles.list_profiles()[0]
            profiles.set_active_profile(only_profile.profile_id)

        active_profile = profiles.get_active_profile()
        if active_profile is not None and active_profile.has_password:
            log.info("Single profile is password-protected — showing lock screen.")
            self.lock_screen = LockScreen(self.context, active_profile)
            self.lock_screen.unlocked.connect(self._on_lock_screen_unlocked)
            self.splash.close()
            self._display(self.lock_screen)
            return

        self._show_main_window()

    def _on_setup_finished(self) -> None:
        self._show_main_window()

    def _on_profile_selected(self) -> None:
        if self.profile_select is not None:
            self.profile_select.close()
        self._show_main_window()

    def _on_lock_screen_unlocked(self) -> None:
        if self.lock_screen is not None:
            self.lock_screen.close()
        self._show_main_window()

    def _on_switch_profile_requested(self) -> None:
        """
        Triggered by the "Switch User" button in MainWindow's header.
        Unlike the boot-time flow, this always shows the profile
        selector regardless of how many profiles exist — it's also the
        entry point for adding a second profile to a previously
        single-profile device.
        """
        log.info("Switch User requested.")
        if self.main_window is not None:
            self.main_window.close()
            self.main_window.deleteLater()
            self.main_window = None

        self.profile_select = ProfileSelectScreen(self.context)
        self.profile_select.profile_selected.connect(self._on_profile_selected)
        self._display(self.profile_select)

    def _show_main_window(self) -> None:
        if self.splash is not None:
            self.splash.close()
        self.main_window = MainWindow(self.context, self.module_manager)
        self.main_window.switch_profile_requested.connect(self._on_switch_profile_requested)
        self._display(self.main_window)

    @staticmethod
    def _noop() -> None:
        pass
