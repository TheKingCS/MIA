"""
gui.main_window
================

The main M.I.A. shell: header bar, a stacked view area, and a reserved
character panel. The stacked area swaps between three kinds of screen:
the post-login Home dashboard (`gui/home_dashboard.py`, the default
landing view), the Apps grid (`_build_menu()` — every discovered
module, moved out of being the landing view itself as of the 2026-07-14
aesthetic pass part 3, see docs/ROADMAP.md), and whichever module's
widget is currently open.

This is meant to feel like the "desktop" of M.I.A.'s operating
environment, not a single-purpose app window — hence separate "Home"
and "Apps" destinations rather than a single flat menu, and a
persistent side panel reserved for the character rather than a modal
dialog.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)

from core.app_context import AppContext
from core.logger import get_logger
from core.module_manager import ModuleManager
from gui.character_panel import CharacterPanel
from gui.easter_egg import EasterEggDialog
from gui.home_dashboard import HomeDashboard
from gui.notification_center import NotificationCenterDialog
from gui.notification_toast import NotificationToast
from gui.search_dialog import SearchDialog
from gui.widgets.floating_orb_widget import FloatingOrbWidget
from gui.widgets.module_button import ModuleButton
from gui.widgets.volume_quick_control import VolumeQuickControl

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
        # docs/ROADMAP.md milestone 11.2 — Field Kit's "Browse Files"
        # device action publishes this rather than importing
        # modules.files_mod directly, same module-isolation reasoning
        # as open_module_requested above.
        self.context.events.subscribe("files.browse_path_requested", self._on_files_browse_path_requested)
        # 2026-07-16 — Settings' "Switch User" button (moved out of the
        # header bar) publishes this rather than importing gui/
        # directly, same module-isolation reasoning as open_module_requested
        # above; re-emits the existing switch_profile_requested signal so
        # core/application.py's handler needs no changes.
        self.context.events.subscribe("profile.switch_requested", self._on_profile_switch_requested)

    def _on_modules_changed(self, **kwargs) -> None:
        self._rebuild_menu()

    def _on_assistant_open_module_requested(self, module_id: str) -> None:
        self.open_module(module_id)

    def _on_profile_switch_requested(self, **kwargs) -> None:
        self.switch_profile_requested.emit()

    def _on_files_browse_path_requested(self, path: str) -> None:
        self.open_module("files")
        files_module = self.module_manager.get("files")
        if files_module is not None:
            files_module.navigate_to_path(Path(path))

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
        self._notifications_menu_action.setText(f"\U0001F514 Notifications ({count})" if count else "\U0001F514 Notifications")
        # Dynamic property, not a second object name — lets QSS give the
        # avatar button an accent color only while there's something
        # unread via "QPushButton#ProfileAvatarButton[hasUnread=true]",
        # without a style() re-polish this method would otherwise skip
        # (Qt caches QSS property-selector results per widget until
        # explicitly told to re-evaluate). Same technique the old
        # notification bell used, just moved to the new button.
        self._profile_button.setProperty("hasUnread", bool(count))
        self._profile_button.style().unpolish(self._profile_button)
        self._profile_button.style().polish(self._profile_button)

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
        self.context.events.unsubscribe("files.browse_path_requested", self._on_files_browse_path_requested)
        self.context.events.unsubscribe("profile.switch_requested", self._on_profile_switch_requested)
        if self._character_panel is not None:
            self._character_panel.unsubscribe()
        if hasattr(self, "_orb_timer"):
            self._orb_timer.stop()
        self._home_widget.unsubscribe()
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
        # Home is added first, so it's the QStackedWidget's default
        # currentWidget() — the post-login landing screen — with no
        # extra setCurrentWidget() call needed here.
        self._home_widget = HomeDashboard(self.context)
        self._home_widget.open_apps_requested.connect(self.show_main_menu)
        self._stack.addWidget(self._home_widget)
        self._menu_widget = self._build_menu()
        self._stack.addWidget(self._menu_widget)

        # 2026-07-18: the stack is wrapped in its own QScrollArea rather
        # than added to body_layout directly — a real crash was reported
        # navigating via Home/Back with no Python traceback in
        # logs/mia.log (same "no caught exception" signature as the
        # earlier documented Wayland fullscreen crash, see
        # docs/KNOWN_ISSUES.md). Best diagnosis possible without a real
        # display to reproduce against: switching QStackedWidget's
        # current widget to a module whose content's minimum size
        # exceeds the current window geometry can make Qt's layout
        # engine attempt to grow the top-level *window* to fit — while
        # already fullscreen, that's the exact same kind of buffer/
        # configured-size mismatch that already crashed the Wayland
        # connection once. A QScrollArea absorbs any module's oversized
        # minimum height into a scrollbar instead of ever pushing that
        # demand up to the window itself. Not confirmed as the fix
        # (unverified beyond this one incident, same as the earlier
        # fullscreen fix) — needs the user to confirm on the machine
        # that actually hit this.
        self._stack_scroll = QScrollArea()
        self._stack_scroll.setWidgetResizable(True)
        self._stack_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._stack_scroll.setWidget(self._stack)
        body_layout.addWidget(self._stack_scroll, stretch=3)

        # 2026-07-18: real user ask — no more "24/7 open assistant
        # screen." The sidebar is still built eagerly (it needs to keep
        # reacting to nav events/reflecting the active conversation
        # exactly like before), but hidden by default; a hidden widget
        # in a layout claims no space, so the stack area reclaims the
        # sidebar's width until the floating orb below reveals it again.
        self._character_panel: Optional[CharacterPanel] = None
        if self.context.config.get("gui.show_character_panel", True):
            self._character_panel = CharacterPanel(self.context)
            body_layout.addWidget(self._character_panel, stretch=1)
            self._character_panel.hide()

            self._orb = FloatingOrbWidget(central)
            self._orb.clicked.connect(self._toggle_character_panel)
            self._orb_timer = QTimer(self)
            self._orb_timer.timeout.connect(self._orb.update_position)
            self._orb_timer.start(50)

        root_layout.addWidget(body)

    def _toggle_character_panel(self) -> None:
        if self._character_panel is None:
            return
        self._character_panel.setVisible(not self._character_panel.isVisible())

    def _build_header(self) -> QFrame:
        header = QFrame()
        header.setObjectName("HeaderBar")
        header.setFixedHeight(68)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setSpacing(16)

        title_column = QVBoxLayout()
        title_column.setSpacing(0)

        title = QLabel("M.I.A.")
        title.setObjectName("TitleLabel")
        title_column.addWidget(title)

        active_profile = self.context.profiles.get_active_profile() if self.context.profiles else None
        user_name = active_profile.name if active_profile else ""
        greeting_text = f"Welcome back, {user_name}" if user_name else "Field System Online"
        greeting = QLabel(greeting_text)
        greeting.setObjectName("SubtitleLabel")
        title_column.addWidget(greeting)

        layout.addLayout(title_column)
        layout.addStretch()

        # 2026-07-14 aesthetic pass (docs/ROADMAP.md): every header
        # button now shares one #HeaderButton object name (styled per-
        # theme, scoped to "QFrame#HeaderBar QPushButton#HeaderButton"
        # so it can never leak onto an unrelated button elsewhere in
        # the app) instead of relying on the plain, theme-blind default
        # QPushButton look every header button had before this pass.
        self._back_button = QPushButton("\u2190 Back")
        self._back_button.setObjectName("HeaderButton")
        self._back_button.clicked.connect(self.go_back)
        self._back_button.setEnabled(False)

        self._home_button = QPushButton("\U0001F3E0 Home")
        self._home_button.setObjectName("HeaderButton")
        self._home_button.clicked.connect(self.show_home)

        # "Apps" \u2014 2026-07-14 aesthetic pass part 3: the module grid
        # itself (_build_menu()) moved out of being the landing screen
        # into its own destination, separate from the new Home
        # dashboard above. Still calls the pre-existing show_main_menu()
        # (unrenamed \u2014 it already meant exactly "show the module grid,"
        # just under a name that predates Home existing) so its
        # published "menu.shown" event and gui/character_panel.py's
        # existing reaction to it both keep working unchanged.
        self._apps_button = QPushButton("\u25A6 Apps")
        self._apps_button.setObjectName("HeaderButton")
        self._apps_button.clicked.connect(self.show_main_menu)

        # 2026-07-18: a real search *bar* (QLineEdit chrome), not a
        # button labeled "Search" — read-only so it can't half-pretend
        # to be its own live-filtering box (that's gui/search_dialog.py's
        # job, already built and tested); clicking it just opens that
        # dialog immediately, same as the button did, but it now *looks*
        # like what it is.
        self._search_bar = QLineEdit()
        self._search_bar.setObjectName("HeaderSearchBar")
        self._search_bar.setPlaceholderText("\U0001F50D  Search…")
        self._search_bar.setReadOnly(True)
        self._search_bar.setCursor(Qt.CursorShape.PointingHandCursor)
        self._search_bar.setFixedWidth(220)
        self._search_bar.mousePressEvent = lambda event: self._open_search()

        # 2026-07-18: replaces the notification bell — a circular avatar
        # showing the active profile's first initial, opening a menu with
        # Notifications (preserving that access point, just relocated),
        # a quick volume control, and a Settings shortcut. Real-time
        # notifications still pop up via NotificationToast regardless of
        # whether this menu is ever opened — this is just the "check
        # what I might have missed" access point, same role the bell had.
        initial = user_name[0].upper() if user_name else "?"
        self._profile_button = QPushButton(initial)
        self._profile_button.setObjectName("ProfileAvatarButton")
        self._profile_button.setFixedSize(40, 40)
        self._profile_button.setToolTip(user_name or "Profile")

        self._profile_menu = QMenu(self._profile_button)
        self._notifications_menu_action = self._profile_menu.addAction(
            "\U0001F514 Notifications", self._open_notification_center
        )
        self._profile_menu.addSeparator()
        self._volume_quick_control = VolumeQuickControl(self.context)
        volume_action = QWidgetAction(self._profile_menu)
        volume_action.setDefaultWidget(self._volume_quick_control)
        self._profile_menu.addAction(volume_action)
        self._profile_menu.addSeparator()
        self._profile_menu.addAction("\U00002699 Settings", lambda: self.open_module("settings"))
        self._profile_menu.aboutToShow.connect(self._volume_quick_control.refresh)
        self._profile_button.setMenu(self._profile_menu)

        layout.addWidget(self._back_button)
        layout.addWidget(self._home_button)
        layout.addWidget(self._apps_button)
        layout.addWidget(self._search_bar)
        layout.addWidget(self._profile_button)

        return header

    def _build_menu(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        grid = QGridLayout(container)
        grid.setSpacing(16)
        # 2026-07-18: real report — Apps cards "spaced very far apart."
        # `container` sits in a resizable QScrollArea (this one, plus now
        # gui/main_window.py's own outer `self._stack_scroll` wrapping
        # the whole stack) which can hand it more space than the grid's
        # content actually needs; with no alignment set, QGridLayout
        # distributes that leftover space by growing the gaps between
        # fixed-size cards rather than leaving it as blank margin. Same
        # fix as gui/home_dashboard.py's `outer.setAlignment(AlignTop)`,
        # applied at the grid level here since that's the layout with
        # the excess room.
        grid.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

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

    def show_home(self) -> None:
        """
        Go to the post-login Home dashboard. This clears history rather
        than pushing onto it — Home is a reset point, not a step back,
        same reasoning as show_main_menu() below.
        """
        self._history.clear()
        self._back_button.setEnabled(False)
        self._stack.setCurrentWidget(self._home_widget)
        self._refresh_stack_geometry()
        self.statusBar().showMessage("M.I.A. core online.")
        self.context.events.publish("home.shown")

    def show_main_menu(self) -> None:
        """
        Go to the Apps grid. This clears history rather than pushing
        onto it — Apps is a reset point, not a step back.
        """
        self._history.clear()
        self._back_button.setEnabled(False)
        self._stack.setCurrentWidget(self._menu_widget)
        self._refresh_stack_geometry()
        self.statusBar().showMessage("M.I.A. core online.")
        self.context.events.publish("menu.shown")

    def go_back(self) -> None:
        """Return to the previously viewed screen, if any."""
        if not self._history:
            return
        previous_widget = self._history.pop()
        self._stack.setCurrentWidget(previous_widget)
        self._refresh_stack_geometry()
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
        if widget is self._home_widget:
            self.context.events.publish("home.shown")
            return
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
        self._refresh_stack_geometry()

    def _refresh_stack_geometry(self) -> None:
        """
        2026-07-18: defensive follow-up to the dashboard-sizing report.
        `setCurrentWidget()` alone doesn't generate a real resize/show
        event for the newly-current page in every case, so the
        QScrollArea wrapping `self._stack` (added for the Home/Back
        crash fix) can be left holding stale geometry for it. Nudging
        both explicitly right after every page switch is cheap
        insurance against that, on top of the more targeted
        `HomeDashboard.showEvent()` fix.
        """
        self._stack.updateGeometry()
        self._stack_scroll.updateGeometry()
