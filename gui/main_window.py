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
from gui.styles import DARK_FIELD_THEME
from gui.widgets.module_button import ModuleButton

log = get_logger(__name__)


class MainWindow(QMainWindow):
    def __init__(self, context: AppContext, module_manager: ModuleManager) -> None:
        super().__init__()
        self.context = context
        self.module_manager = module_manager

        # Cache of already-built module widgets, so switching back to a
        # module the user already opened doesn't rebuild it from scratch.
        self._module_widgets: dict[str, QWidget] = {}

        self.setWindowTitle("M.I.A. — Multifunctional Intelligent Assistant")
        self.setStyleSheet(DARK_FIELD_THEME)
        self.resize(
            context.config.get("gui.window_width", 1100),
            context.config.get("gui.window_height", 700),
        )

        self._wire_module_browser()
        self._build_ui()
        self._setup_kiosk_exit_shortcut()
        self.statusBar().showMessage("M.I.A. core online.")

        self._kiosk_mode = context.config.get("system.kiosk_mode", False)

    def showEvent(self, event) -> None:
        """
        Enter fullscreen on first show if kiosk_mode is enabled. Done in
        showEvent (rather than __init__) because showFullScreen() needs
        the window to already be shown/mapped by the window manager to
        behave correctly on all platforms.
        """
        super().showEvent(event)
        if getattr(self, "_kiosk_mode", False) and not self.isFullScreen():
            self.showFullScreen()

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

        if self.context.config.get("gui.show_character_panel", True):
            body_layout.addWidget(CharacterPanel(), stretch=1)

        root_layout.addWidget(body)

    def _build_header(self) -> QFrame:
        header = QFrame()
        header.setObjectName("HeaderBar")
        header.setFixedHeight(64)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 0, 20, 0)

        title = QLabel("M.I.A.")
        title.setObjectName("TitleLabel")

        user_name = self.context.config.get("user.name", "")
        greeting_text = f"Welcome back, {user_name}" if user_name else "Field System Online"
        greeting = QLabel(greeting_text)
        greeting.setObjectName("SubtitleLabel")

        self._home_button = QPushButton("\u2302 Main Menu")
        self._home_button.clicked.connect(self.show_main_menu)

        layout.addWidget(title)
        layout.addWidget(greeting)
        layout.addStretch()
        layout.addWidget(self._home_button)

        return header

    def _build_menu(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        grid = QGridLayout(container)
        grid.setSpacing(16)

        modules = self.module_manager.all()
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

        self._stack.setCurrentWidget(self._module_widgets[module_id])
        self.statusBar().showMessage(f"Viewing: {module_id}")

    def show_main_menu(self) -> None:
        self._stack.setCurrentWidget(self._menu_widget)
        self.statusBar().showMessage("M.I.A. core online.")
