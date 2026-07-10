"""
gui.character_panel
====================

Placeholder for M.I.A.'s future animated character.

This widget is deliberately isolated in its own file with a narrow,
stable interface: it's constructed with no arguments and produces a
single QFrame. When the real animated character is built, it should
be implemented as a drop-in replacement for CharacterPanel (same class
name and construction signature, ideally, or a swap of the one line
in gui/main_window.py that instantiates it) — nothing else in the GUI
or core should need to change.

Likely future implementation notes (not built yet, intentionally):
    - Probably a QLabel with an animated QMovie, or a small QOpenGLWidget
      / QML view if the character needs more complex animation.
    - Should subscribe to core.event_bus events (e.g. "user.setup_complete",
      module open/close events) to react expressively, via the AppContext
      passed in at construction — so plan to accept `context` as a
      constructor argument once real behavior is added.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


class CharacterPanel(QFrame):
    """
    Static placeholder panel reserved for the future animated character.

    Kept visually distinct (dashed border) so it's obvious in the UI
    that this is a reserved slot, not a finished feature.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("CharacterPanel")
        self.setMinimumWidth(220)
        self.setFrameShape(QFrame.Shape.StyledPanel)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon = QLabel("\U0001F916")  # robot emoji placeholder
        icon.setStyleSheet("font-size: 48px;")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        text = QLabel("M.I.A. Character\n(coming soon)")
        text.setObjectName("CharacterPlaceholderText")
        text.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(icon)
        layout.addWidget(text)
