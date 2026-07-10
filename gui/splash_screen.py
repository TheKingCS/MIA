"""
gui.splash_screen
==================

The "Initializing Core" splash shown while core.application.MIAApplication
runs through its boot sequence.

This is a plain QWidget (not QSplashScreen) because we want full control
over layout — a status label and progress bar — and because a custom
widget is easier to extend later (e.g. adding the animated character
here during boot) than QSplashScreen's more limited drawing model.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QProgressBar, QVBoxLayout, QWidget

from gui.styles import DARK_FIELD_THEME


class SplashScreen(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.SplashScreen)
        self.setFixedSize(480, 260)
        self.setStyleSheet(DARK_FIELD_THEME)
        self._build_ui()
        self._center_on_screen()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(16)
        layout.addStretch()

        title = QLabel("M.I.A.")
        title.setObjectName("TitleLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("Multifunctional Intelligent Assistant")
        subtitle.setObjectName("SubtitleLabel")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._status_label = QLabel("Initializing Core...")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)  # indeterminate — number of boot
        # steps may change over time, so we don't hardcode a step count

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addStretch()
        layout.addWidget(self._status_label)
        layout.addWidget(self._progress)

    def _center_on_screen(self) -> None:
        screen = self.screen()
        if screen is None:
            return
        geometry = screen.availableGeometry()
        x = geometry.center().x() - self.width() // 2
        y = geometry.center().y() - self.height() // 2
        self.move(x, y)

    def set_status(self, message: str) -> None:
        """Update the status text shown under the M.I.A. title during boot."""
        self._status_label.setText(message)
