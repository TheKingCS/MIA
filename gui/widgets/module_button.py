"""
gui.widgets.module_button
==========================

A single button representing one module on the main menu grid.

Pulled out as its own widget (rather than inlined in main_window.py) so
its appearance and behavior can evolve — e.g. showing a live status
badge, or a different look for disabled/unavailable modules — without
touching MainWindow's layout code.

2026-07-14 aesthetic pass (docs/ROADMAP.md): redesigned from a single
icon+name line into a richer two-line card (icon badge, bold name,
muted one-line description) with a QGraphicsDropShadowEffect for real
depth — found via actually rendering the old version that a flat grid
of identical single-line buttons read as a developer placeholder, not
a finished app.

This redesign also incidentally fixed a real, pre-existing bug found
by looking at that same rendered screenshot: the old version built its
button text as a single f-string handed straight to `QPushButton`'s
text (which treats a bare `&` as a mnemonic/accelerator marker — the
following character becomes an underlined keyboard shortcut), silently
mangling "Workshop & Electronics" into "Workshop _Electronics". This
version's `QPushButton` carries no text of its own at all (its name is
a plain `QLabel` child instead, which does not parse mnemonics), so the
bug can't recur here — nothing needs escaping.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from modules.module_base import ModuleBase

# A name this long ("Workshop & Electronics" is the longest real one
# today) wrapping to 2 lines overflowed the card's fixed height in
# testing — elided to one line with "..." instead, same trade-off as a
# native OS taskbar/tab label rather than a taller, unevenly-sized card
# just for the one or two longest module names. Deliberately
# conservative rather than measured against the real column width
# (only known after layout, not at construction time, and this app's
# default window is a fixed 1100x700 kiosk size per
# config/default_config.json, not an arbitrarily resizable desktop
# window) — found via rendering that a looser guess (220px) let Qt
# decide no eliding was needed, then the real column clipped the
# un-elided text anyway with no ellipsis shown at all.
_MAX_NAME_WIDTH_PX = 165
_MAX_DESCRIPTION_WIDTH_PX = 235  # smaller, non-bold font than the name — fits more characters at the same pixel width


class ModuleButton(QPushButton):
    """A clickable button representing a module on the main menu."""

    activated = Signal(str)  # emits the module_id when clicked

    def __init__(self, module: ModuleBase) -> None:
        super().__init__()
        self.setObjectName("ModuleButton")
        self.setToolTip(module.description or module.display_name)
        self.setMinimumHeight(72)
        self._module_id = module.module_id
        self.clicked.connect(self._on_clicked)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(14)

        icon_badge = QLabel(module.icon)
        icon_badge.setObjectName("ModuleButtonIcon")
        icon_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_badge.setFixedSize(48, 48)
        layout.addWidget(icon_badge)

        text_column = QVBoxLayout()
        text_column.setSpacing(2)

        name_label = QLabel()
        name_label.setObjectName("ModuleButtonName")
        # Elision must be measured against the QSS-applied font (bold,
        # 15px — see gui/styles.py's #ModuleButtonName rule), not the
        # widget's pre-stylesheet default font — measuring against the
        # wrong (smaller, non-bold) font under-estimated the rendered
        # width and clipped the trailing "..." off-card in testing.
        name_font = QFont(name_label.font())
        name_font.setBold(True)
        name_font.setPixelSize(15)  # QSS uses "font-size: 15px" — pixels, not points
        name_label.setText(QFontMetrics(name_font).elidedText(
            module.display_name, Qt.TextElideMode.ElideRight, _MAX_NAME_WIDTH_PX
        ))
        if name_label.text() != module.display_name:
            name_label.setToolTip(module.display_name)
        text_column.addWidget(name_label)

        if module.description:
            description_label = QLabel()
            description_label.setObjectName("ModuleButtonDescription")
            # Single elided line, not word-wrap — a 2-3 line description
            # (several modules' real descriptions run that long) made
            # cards tall enough that all 16 modules no longer fit in
            # this app's actual 1100x700 default kiosk window without
            # scrolling, a real usability regression on a kiosk device
            # found by rendering at the real default size, not just a
            # wider dev-convenience size. A one-line hint plus the full
            # text in the tooltip (already set on the button itself)
            # keeps every card the same compact height.
            description_font = QFont(description_label.font())
            description_font.setPixelSize(12)
            description_label.setText(QFontMetrics(description_font).elidedText(
                module.description, Qt.TextElideMode.ElideRight, _MAX_DESCRIPTION_WIDTH_PX
            ))
            text_column.addWidget(description_label)

        layout.addLayout(text_column, stretch=1)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(18)
        shadow.setXOffset(0)
        shadow.setYOffset(3)
        shadow.setColor(QColor(0, 0, 0, 110))
        self.setGraphicsEffect(shadow)

    def _on_clicked(self) -> None:
        self.activated.emit(self._module_id)
