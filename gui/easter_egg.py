"""
gui.easter_egg
================

A hidden credits screen, triggered by Ctrl+Shift+Z from anywhere in the
main window. Purely cosmetic — no config, no logic, nothing else in the
system depends on this file existing.

Layout note: this dialog previously used layout.setAlignment(AlignCenter)
on its top-level QVBoxLayout, which AddProfileDialog and
PasswordPromptDialog do not do — and those two dialogs render correctly.
Removing that top-level alignment (centering each label individually
instead, and using addStretch() for spacing) matches the pattern that's
actually confirmed working, rather than guessing at dialog sizing again.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout



class EasterEggDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("???")
        self.setMinimumWidth(380)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(10)
        # Deliberately no layout.setAlignment(...) here — see module
        # docstring. Each label centers its own text instead.

        icon = QLabel("\U0001F916")
        icon.setStyleSheet("font-size: 48px;")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("M.I.A.")
        title.setObjectName("TitleLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("Multifunctional Intelligent Assistant")
        subtitle.setObjectName("SubtitleLabel")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setWordWrap(True)

        credit = QLabel("Built by\nZachary Taylar Rhodes")
        credit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        credit.setWordWrap(True)
        credit.setStyleSheet("font-weight: 600; font-size: 16px; margin-top: 8px;")

        wink = QLabel("You found the secret. Stay safe out there. \U0001F6E0\uFE0F")
        wink.setObjectName("SubtitleLabel")
        wink.setAlignment(Qt.AlignmentFlag.AlignCenter)
        wink.setWordWrap(True)

        close_button = QPushButton("Nice.")
        close_button.setObjectName("ModuleButton")
        close_button.setMinimumHeight(44)
        close_button.clicked.connect(self.accept)

        layout.addWidget(icon)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(credit)
        layout.addWidget(wink)
        layout.addSpacing(6)
        layout.addWidget(close_button)
