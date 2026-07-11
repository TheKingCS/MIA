"""
modules.toolbox.module
=========================

Toolbox: the shared home for every calculator registered with
core.calculator_engine.CalculatorEngine (self.context.calculators),
per docs/ROADMAP.md's Calculator Engine shared service. Lists
registered calculators grouped by category; picking one shows its own
widget. Adding a new calculator anywhere in the app never requires
touching this file — see core/calculator_engine.py.

Built calculator widgets are cached per calculator_id (same
lazy-build-once-then-reuse pattern gui/main_window.py already uses for
module widgets), so reopening a calculator doesn't rebuild it or lose
whatever's already there — it does reset naturally today only because
opening it fresh happens to be indistinguishable, but the cache is
what avoids leaking a new QWidget into the stack every time.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from modules.module_base import ModuleBase


class ToolboxModule(ModuleBase):
    module_id = "toolbox"
    display_name = "Toolbox"
    description = "Calculators, unit conversion, and other quick tools."
    icon = "\U0001F9F0"  # toolbox

    def __init__(self, context) -> None:
        super().__init__(context)
        self._stack: QStackedWidget | None = None
        self._list_page: QWidget | None = None
        self._calculator_pages: dict[str, QWidget] = {}

    def get_widget(self) -> QWidget:
        self._stack = QStackedWidget()
        self._list_page = self._build_list_page()
        self._stack.addWidget(self._list_page)
        self._stack.setCurrentWidget(self._list_page)
        return self._stack

    def _build_list_page(self) -> QWidget:
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(12)

        header = QLabel(f"{self.icon}  {self.display_name}")
        header.setObjectName("TitleLabel")
        outer.addWidget(header)

        subtitle = QLabel(self.description)
        subtitle.setObjectName("SubtitleLabel")
        outer.addWidget(subtitle)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        list_container = QWidget()
        list_layout = QVBoxLayout(list_container)
        list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        list_layout.setSpacing(12)

        by_category = self.context.calculators.by_category()
        if not by_category:
            empty_label = QLabel("No calculators registered yet.")
            empty_label.setObjectName("SubtitleLabel")
            list_layout.addWidget(empty_label)
        else:
            for category in sorted(by_category.keys()):
                category_label = QLabel(category)
                category_label.setStyleSheet("font-weight: 600; margin-top: 8px;")
                list_layout.addWidget(category_label)
                for calculator in by_category[category]:
                    list_layout.addWidget(self._build_calculator_row(calculator))

        scroll.setWidget(list_container)
        outer.addWidget(scroll)
        return page

    def _build_calculator_row(self, calculator) -> QFrame:
        row = QFrame()
        row.setObjectName("CharacterPanel")  # reuse the dashed-panel style
        layout = QHBoxLayout(row)

        text_layout = QVBoxLayout()
        title = QLabel(calculator.display_name)
        title.setStyleSheet("font-weight: 600;")
        subtitle = QLabel(calculator.description)
        subtitle.setObjectName("SubtitleLabel")
        subtitle.setWordWrap(True)
        text_layout.addWidget(title)
        text_layout.addWidget(subtitle)
        layout.addLayout(text_layout, stretch=3)

        open_button = QPushButton("Open")
        open_button.setMinimumHeight(40)
        open_button.clicked.connect(lambda checked=False, c=calculator: self._open_calculator(c))
        layout.addWidget(open_button, stretch=1)

        return row

    def _open_calculator(self, calculator) -> None:
        if self._stack is None:
            return

        if calculator.calculator_id not in self._calculator_pages:
            page = QWidget()
            outer = QVBoxLayout(page)
            outer.setContentsMargins(0, 0, 0, 0)
            outer.setSpacing(0)

            back_button = QPushButton("← Back to Toolbox")
            back_button.setObjectName("ModuleButton")
            back_button.clicked.connect(self._show_list_page)
            outer.addWidget(back_button)

            outer.addWidget(calculator.build_widget())

            self._calculator_pages[calculator.calculator_id] = page
            self._stack.addWidget(page)

        self._stack.setCurrentWidget(self._calculator_pages[calculator.calculator_id])

    def _show_list_page(self) -> None:
        if self._stack is not None and self._list_page is not None:
            self._stack.setCurrentWidget(self._list_page)
