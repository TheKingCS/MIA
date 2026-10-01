"""
gui.starter_dialog
====================

Settings → My Apps → "Add a Starter Set..." (core/starter_templates.py):
pick a set, untick the parts that don't fit ("we don't have a well"),
and add it. Safe to repeat; the Assistant's "undo that" takes it back.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLayout,
    QPushButton,
    QVBoxLayout,
)

from core import starter_templates
from core.starter_templates import STARTERS, Upkeep


def part_summary(part) -> str:
    """Pure formatting. The things in one part, for its checkbox."""
    names = []
    for item in part.items:
        names += [t for t, _days in item.tasks] if isinstance(item, Upkeep) else [item.name]
    shown: list[str] = []
    for name in names:  # one line: as many as fit, then "and N more"
        if shown and len(", ".join(shown + [name])) > 70:
            break
        shown.append(name)
    rest = len(names) - len(shown)
    return ", ".join(shown) + (f" and {rest} more" if rest else "")


class StarterDialog(QDialog):
    def __init__(self, context, parent=None, starter_id: Optional[str] = None) -> None:
        super().__init__(parent)
        self.context = context
        self.result_text = ""
        self.setWindowTitle("Add a Starter Set")
        self.setMinimumWidth(600)
        layout = QVBoxLayout(self)
        layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)  # grows with wrapped text
        intro = QLabel("Fill MIA in with the usual things for your kind of life, so there's something to check off "
                       "on day one. Untick anything that doesn't fit. Rename or delete anything later.")
        intro.setWordWrap(True)
        layout.addWidget(intro)
        self.starter_combo = QComboBox()
        for starter in STARTERS.values():
            self.starter_combo.addItem(f"{starter.name}: {starter.description}", starter.starter_id)
        if starter_id:
            self.starter_combo.setCurrentIndex(max(0, self.starter_combo.findData(starter_id)))
        layout.addWidget(self.starter_combo)
        # A plain layout (not a container widget), so wrapped lines make the dialog taller.
        self._parts_layout = QVBoxLayout()
        self._parts_layout.setContentsMargins(12, 0, 0, 0)
        layout.addLayout(self._parts_layout)
        self.message_label = QLabel("")
        self.message_label.setWordWrap(True)
        layout.addWidget(self.message_label)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self.add_button = QPushButton("Add")
        self.add_button.clicked.connect(self._on_add)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        buttons.addWidget(self.add_button)
        buttons.addWidget(close)
        layout.addLayout(buttons)
        self.part_checks: dict[str, QCheckBox] = {}
        self.starter_combo.currentIndexChanged.connect(self._show_parts)
        self._show_parts()

    def _show_parts(self) -> None:
        while self._parts_layout.count():
            widget = self._parts_layout.takeAt(0).widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        self.part_checks = {}
        for part in STARTERS[self.starter_combo.currentData()].parts:
            check = QCheckBox(part.label)
            check.setChecked(True)
            self.part_checks[part.part_id] = check
            self._parts_layout.addWidget(check)
            contents = QLabel(part_summary(part))
            contents.setObjectName("SubtitleLabel")
            contents.setWordWrap(True)
            contents.setIndent(24)
            self._parts_layout.addWidget(contents)
        self.message_label.setText("")

    def _on_add(self) -> None:
        chosen = [pid for pid, check in self.part_checks.items() if check.isChecked()]
        if not chosen:
            self.message_label.setText("Tick at least one part.")
            return
        result = starter_templates.apply(self.context, self.starter_combo.currentData(), chosen)
        self.result_text = result.describe()
        self.message_label.setText(self.result_text + (" Ask MIA to \"undo that\" to take it back."
                                                       if result.added else ""))
