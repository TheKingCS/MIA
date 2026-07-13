"""
gui.splash_screen
==================

The boot splash shown while core.application.MIAApplication runs
through its boot sequence — status text plus a pulsing "core" graphic
(gui/boot_core_widget.py), the first piece of the "Jarvis-style" boot
animation captured in docs/ROADMAP.md milestone 2.9.

This is a plain QWidget (not QSplashScreen) because we want full
control over layout — a status label, the core animation, and a
progress bar — and because a custom widget is easier to extend later
(e.g. adding the animated character here during boot) than
QSplashScreen's more limited drawing model.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QProgressBar, QVBoxLayout, QWidget

from gui.boot_core_widget import PulsingCoreWidget


class SplashScreen(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.SplashScreen)
        # A resizable default size, not setFixedSize() — MIAApplication
        # now routes this through _display(), which calls
        # showFullScreen() in kiosk mode. A hard fixed size would cap
        # the window at 480x380 even in fullscreen state, leaving most
        # of the screen blank instead of actually filling it.
        self.resize(480, 380)
        self._build_ui()
        self._center_on_screen()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 32, 40, 32)
        layout.setSpacing(12)
        layout.addStretch()

        # "M.I.A." itself is rendered inside the core graphic (see
        # gui/boot_core_widget.py) rather than as a separate label here.
        subtitle = QLabel("Multifunctional Intelligent Assistant")
        subtitle.setObjectName("BootSubtitleLabel")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._core = PulsingCoreWidget()

        self._status_label = QLabel("INITIALIZING CORE SYSTEMS...")
        self._status_label.setObjectName("BootStatusLabel")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)  # indeterminate — number of boot
        # steps may change over time, so we don't hardcode a step count
        self._progress.setFixedHeight(8)
        self._progress.setFixedWidth(360)  # a full-screen-width bar would look odd
        self._progress.setTextVisible(False)

        layout.addWidget(subtitle)
        layout.addStretch()
        layout.addWidget(self._core, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()
        layout.addWidget(self._status_label)
        layout.addWidget(self._progress, alignment=Qt.AlignmentFlag.AlignCenter)

    def _center_on_screen(self) -> None:
        screen = self.screen()
        if screen is None:
            return
        geometry = screen.availableGeometry()
        x = geometry.center().x() - self.width() // 2
        y = geometry.center().y() - self.height() // 2
        self.move(x, y)

    def set_status(self, message: str) -> None:
        """Update the status text shown under the core animation during boot."""
        self._status_label.setText(message)

    def closeEvent(self, event) -> None:
        self._core.stop()
        super().closeEvent(event)
