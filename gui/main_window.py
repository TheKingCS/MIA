"""
gui.main_window
================

The main M.I.A. shell: header bar, module menu grid, reserved character
panel, and a stacked view area that swaps between the menu and an open
module's widget.

This is meant to feel like the "desktop" of M.I.A.'s operating
environment, not a single-purpose app window — hence "Main Menu" rather
than a typical toolbar, and a persistent side panel reserved for the
character rather than a modal dialog.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from core.app_context import AppContext
from core.logger import get_logger
from core.module_manager import ModuleManager
from gui.character_panel import CharacterPanel
from gui.easter_egg import EasterEggDialog
from gui.notification_center import NotificationCenterDialog
from gui.notification_toast import NotificationToast
from gui.search_dialog import SearchDialog
from gui.styles import DARK_FIELD_THEME
from gui.widgets.module_button import ModuleButton

log = get_logger(__name__)


class MainWindow(QMainWindow):
    switch_profile_requested = Signal()

    def __init__(self, context: AppContext, module_manager: ModuleManager) -> None:
        super().__init__()
        self.context = context
        self.module_manager = module_manager

        # Cache of already-built module widgets, so switching back to a
        # module the user already opened doesn't rebuild it from scratch.
        self._module_widgets: dict[str, QWidget] = {}

        # Navigation history — a stack of previously-viewed widgets, so
        # "Back" means "go where I just was," distinct from "Main Menu"
        # which always means "go home." Both are needed once any module
        # gains sub-screens of its own (e.g. Notes -> a specific note).
        self._history: list[QWidget] = []

        self.setWindowTitle("M.I.A. — Multifunctional Intelligent Assistant")
        self.setStyleSheet(DARK_FIELD_THEME)
        self.resize(
            context.config.get("gui.window_width", 1100),
            context.config.get("gui.window_height", 700),
        )

        self._wire_module_browser()
        self._build_ui()
        self._setup_kiosk_exit_shortcut()
        self._setup_easter_egg_shortcut()
        self._setup_search_shortcut()
        self._setup_notifications()
        self._setup_module_events()
        self.statusBar().showMessage("M.I.A. core online.")

    def _setup_search_shortcut(self) -> None:
        """Ctrl+K opens search from anywhere in the app — matches the
        common command-palette convention (VS Code, Slack, etc.)."""
        shortcut = QShortcut(QKeySequence("Ctrl+K"), self)
        shortcut.activated.connect(self._open_search)

    def _open_search(self) -> None:
        dialog = SearchDialog(self.context, parent=self)
        dialog.result_activated.connect(self._on_search_result_activated)
        dialog.exec()

    def _on_search_result_activated(self, result) -> None:
        """
        Interpret a SearchResult's action_type. "switch_profile" opens
        the full profile selector rather than switching directly — that
        screen already handles password-protected profiles correctly,
        and duplicating that check here would mean two places to keep
        in sync. A future improvement could deep-link straight to that
        profile's password prompt, but reusing the proven flow is the
        safer default for now.
        """
        if result.action_type == "open_module":
            self.open_module(result.action_target)
        elif result.action_type == "switch_profile":
            self.switch_profile_requested.emit()
        else:
            log.warning("Unknown search result action_type '%s'", result.action_type)

    def _setup_module_events(self) -> None:
        """
        Subscribe so enabling/disabling a module or rescanning for new
        ones updates the main menu grid immediately, without requiring
        a restart. Bound methods stored on self so closeEvent() can
        unsubscribe the exact same callables — same reasoning as
        _setup_notifications() above.
        """
        self.context.events.subscribe("modules.enabled_changed", self._on_modules_changed)
        self.context.events.subscribe("modules.rescanned", self._on_modules_changed)
        # docs/ROADMAP.md milestone 5.5 — the Assistant's "open_module"
        # action (core/application.py's _action_open_module) publishes
        # this rather than ever touching MainWindow directly, since a
        # Qt widget must only be touched from the GUI thread and the
        # action handler can't assume it's already on it.
        self.context.events.subscribe("assistant.open_module_requested", self._on_assistant_open_module_requested)

    def _on_modules_changed(self, **kwargs) -> None:
        self._rebuild_menu()

    def _on_assistant_open_module_requested(self, module_id: str) -> None:
        self.open_module(module_id)

    def _rebuild_menu(self) -> None:
        """Rebuild the main menu grid in place, preserving which screen is currently visible."""
        was_showing_menu = self._stack.currentWidget() is self._menu_widget
        old_menu = self._menu_widget
        new_menu = self._build_menu()

        index = self._stack.indexOf(old_menu)
        self._stack.insertWidget(index, new_menu)
        self._stack.removeWidget(old_menu)
        old_menu.deleteLater()
        self._menu_widget = new_menu

        if was_showing_menu:
            self._stack.setCurrentWidget(new_menu)

    def _setup_notifications(self) -> None:
        """
        Subscribe to the notification events raised by any module via
        context.notifications.notify(). Kept as bound methods stored on
        self so closeEvent() can unsubscribe the exact same callables —
        see the comment there for why that matters.
        """
        self.context.events.subscribe("notification.created", self._on_notification_created)
        self.context.events.subscribe("notification.updated", self._on_notification_updated)
        self._update_notification_badge()

    def _on_notification_created(self, notification) -> None:
        self._update_notification_badge()
        toast = NotificationToast(self, notification)
        toast.show_in_corner()

    def _on_notification_updated(self, **kwargs) -> None:
        self._update_notification_badge()

    def _update_notification_badge(self) -> None:
        count = self.context.notifications.unread_count()
        label = f"\U0001F514 {count}" if count else "\U0001F514"
        self._notification_button.setText(label)

    def _open_notification_center(self) -> None:
        dialog = NotificationCenterDialog(self.context, parent=self)
        dialog.exec()
        self._update_notification_badge()

    def closeEvent(self, event) -> None:
        """
        Unsubscribe from the event bus before this window is destroyed.
        Without this, EventBus would keep a reference to these bound
        methods after "Switch User" rebuilds MainWindow — the next
        notification would then try to call into a deleted Qt widget.
        EventBus.publish() catches and logs that as an error rather than
        crashing, but it's still a real leak worth closing properly.
        """
        self.context.events.unsubscribe("notification.created", self._on_notification_created)
        self.context.events.unsubscribe("notification.updated", self._on_notification_updated)
        self.context.events.unsubscribe("modules.enabled_changed", self._on_modules_changed)
        self.context.events.unsubscribe("modules.rescanned", self._on_modules_changed)
        self.context.events.unsubscribe(
            "assistant.open_module_requested", self._on_assistant_open_module_requested
        )
        if self._character_panel is not None:
            self._character_panel.unsubscribe()
        super().closeEvent(event)

    def _setup_kiosk_exit_shortcut(self) -> None:
        """
        Ctrl+Shift+Q always exits fullscreen/kiosk mode, with a
        confirmation prompt so it can't happen by accident. This is the
        maintenance escape hatch — without it, a kiosk-mode device with
        no window chrome would have no way to reach a desktop for
        debugging or updates without SSH access.
        """
        shortcut = QShortcut(QKeySequence("Ctrl+Shift+Q"), self)
        shortcut.activated.connect(self._on_kiosk_exit_requested)

    def _setup_easter_egg_shortcut(self) -> None:
        """Ctrl+Shift+Z — purely for fun. See gui/easter_egg.py."""
        shortcut = QShortcut(QKeySequence("Ctrl+Shift+Z"), self)
        shortcut.activated.connect(lambda: EasterEggDialog(self).exec())

    def _on_kiosk_exit_requested(self) -> None:
        reply = QMessageBox.question(
            self,
            "Exit M.I.A.",
            "Exit M.I.A. and return to the desktop?\n\n"
            "(If running as a system service, M.I.A. will restart "
            "automatically after a few seconds.)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            log.info("Kiosk exit requested by user via Ctrl+Shift+Q.")
            self.close()

    def _wire_module_browser(self) -> None:
        """
        Hand the module_browser module a listing of all discovered
        modules. Done here (in the GUI layer, which already holds the
        ModuleManager) rather than inside modules/module_browser itself,
        to avoid that module needing to import ModuleManager directly.
        """
        browser = self.module_manager.get("module_browser")
        if browser is not None:
            browser.known_modules = self.module_manager.all()
            browser.module_manager = self.module_manager

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        root_layout.addWidget(self._build_header())

        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(20, 20, 20, 20)
        body_layout.setSpacing(20)

        self._stack = QStackedWidget()
        self._menu_widget = self._build_menu()
        self._stack.addWidget(self._menu_widget)
        body_layout.addWidget(self._stack, stretch=3)

        self._character_panel: Optional[CharacterPanel] = None
        if self.context.config.get("gui.show_character_panel", True):
            self._character_panel = CharacterPanel(self.context)
            body_layout.addWidget(self._character_panel, stretch=1)

        root_layout.addWidget(body)

    def _build_header(self) -> QFrame:
        header = QFrame()
        header.setObjectName("HeaderBar")
        header.setFixedHeight(64)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 0, 20, 0)

        title = QLabel("M.I.A.")
        title.setObjectName("TitleLabel")

        active_profile = self.context.profiles.get_active_profile() if self.context.profiles else None
        user_name = active_profile.name if active_profile else ""
        greeting_text = f"Welcome back, {user_name}" if user_name else "Field System Online"
        greeting = QLabel(greeting_text)
        greeting.setObjectName("SubtitleLabel")

        self._back_button = QPushButton("\u2190 Back")
        self._back_button.clicked.connect(self.go_back)
        self._back_button.setEnabled(False)

        self._home_button = QPushButton("\u2302 Main Menu")
        self._home_button.clicked.connect(self.show_main_menu)

        self._switch_user_button = QPushButton("\u21C4 Switch User")
        self._switch_user_button.clicked.connect(self.switch_profile_requested.emit)

        self._notification_button = QPushButton("\U0001F514")
        self._notification_button.clicked.connect(self._open_notification_center)

        self._search_button = QPushButton("\U0001F50D Search")
        self._search_button.clicked.connect(self._open_search)

        layout.addWidget(title)
        layout.addWidget(greeting)
        layout.addStretch()
        layout.addWidget(self._back_button)
        layout.addWidget(self._home_button)
        layout.addWidget(self._switch_user_button)
        layout.addWidget(self._search_button)
        layout.addWidget(self._notification_button)

        return header

    def _build_menu(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        grid = QGridLayout(container)
        grid.setSpacing(16)

        modules = self.module_manager.enabled_modules()
        columns = 3
        for index, module in enumerate(modules):
            button = ModuleButton(module)
            button.activated.connect(self.open_module)
            row, col = divmod(index, columns)
            grid.addWidget(button, row, col)

        scroll.setWidget(container)
        return scroll

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def open_module(self, module_id: str) -> None:
        """Switch the central stack to show the given module's widget."""
        if module_id not in self._module_widgets:
            module = self.module_manager.get(module_id)
            if module is None:
                log.warning("Attempted to open unknown module_id '%s'", module_id)
                return
            module.on_load()
            widget = module.get_widget()
            self._module_widgets[module_id] = widget
            self._stack.addWidget(widget)
            log.info("Opened module '%s' for the first time.", module_id)

        self._navigate_to(self._module_widgets[module_id])
        self.statusBar().showMessage(f"Viewing: {module_id}")
        # docs/ROADMAP.md milestone 6.1 — lets gui/character_panel.py (or
        # any future subscriber) react to whichever module is active
        # without MainWindow needing to know who's listening.
        self.context.events.publish("module.opened", module_id=module_id)

    def show_main_menu(self) -> None:
        """
        Go "home" to the main menu grid. This clears history rather than
        pushing onto it — Main Menu is a reset point, not a step back.
        """
        self._history.clear()
        self._back_button.setEnabled(False)
        self._stack.setCurrentWidget(self._menu_widget)
        self.statusBar().showMessage("M.I.A. core online.")
        self.context.events.publish("menu.shown")

    def go_back(self) -> None:
        """Return to the previously viewed screen, if any."""
        if not self._history:
            return
        previous_widget = self._history.pop()
        self._stack.setCurrentWidget(previous_widget)
        self._back_button.setEnabled(bool(self._history))
        self.statusBar().showMessage("M.I.A. core online." if previous_widget is self._menu_widget else "Viewing previous screen")
        self._publish_navigation_event_for_widget(previous_widget)

    def _publish_navigation_event_for_widget(self, widget: QWidget) -> None:
        """
        go_back() can land on either the menu or some previously-opened
        module's widget — figure out which and publish the matching
        event (same events open_module()/show_main_menu() publish),
        so a subscriber never needs its own copy of this widget lookup.
        """
        if widget is self._menu_widget:
            self.context.events.publish("menu.shown")
            return
        for module_id, module_widget in self._module_widgets.items():
            if module_widget is widget:
                self.context.events.publish("module.opened", module_id=module_id)
                return

    def _navigate_to(self, widget: QWidget) -> None:
        """
        Switch the stack to `widget`, pushing whatever was showing onto
        the back-history first (unless it's the same widget, to avoid
        a no-op history entry from double-clicks).
        """
        current = self._stack.currentWidget()
        if current is not None and current is not widget:
            self._history.append(current)
            self._back_button.setEnabled(True)
        self._stack.setCurrentWidget(widget)
