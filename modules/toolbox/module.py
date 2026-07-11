"""
modules.toolbox.module
=========================

Toolbox: the shared home for every calculator registered with
core.calculator_engine.CalculatorEngine (self.context.calculators),
per docs/ROADMAP.md's Calculator Engine shared service, plus the small
set of built-in ToolboxTools (modules/toolbox/tool_base.py) — Calendar,
Alarm, Stopwatch, and Inventory, completing the v0.3 roadmap
breakdown. Lists both, grouped into a "Tools" section and a
"Calculators" section (further grouped by category); picking one shows
its own widget. Adding a new calculator anywhere in the app never
requires touching this file — see core/calculator_engine.py. Adding a
new built-in tool means adding one line to self._tools below.

Calculators and tools share the same open/back navigation: both
expose display_name/description/build_widget(), so _open_item() below
handles either, keyed by a (kind, id) pair so a calculator_id and a
tool_id can never collide. Built widgets are cached per key (same
lazy-build-once-then-reuse pattern gui/main_window.py already uses for
module widgets), so reopening one doesn't rebuild it or lose whatever
state it already had.
"""

from __future__ import annotations

from typing import Callable

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
from modules.toolbox.tools.alarm_tool import AlarmTool
from modules.toolbox.tools.calendar_tool import CalendarTool
from modules.toolbox.tools.inventory_tool import InventoryTool
from modules.toolbox.tools.stopwatch_tool import StopwatchTool


class ToolboxModule(ModuleBase):
    module_id = "toolbox"
    display_name = "Toolbox"
    description = "Calculators, unit conversion, and other quick tools."
    icon = "\U0001F9F0"  # toolbox

    def __init__(self, context) -> None:
        super().__init__(context)
        self._stack: QStackedWidget | None = None
        self._list_page: QWidget | None = None
        self._item_pages: dict[tuple[str, str], QWidget] = {}
        self._tools = [
            CalendarTool(self.context),
            AlarmTool(self.context),
            StopwatchTool(self.context),
            InventoryTool(self.context),
        ]

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

        if self._tools:
            tools_label = QLabel("Tools")
            tools_label.setStyleSheet("font-weight: 600; margin-top: 8px;")
            list_layout.addWidget(tools_label)
            for tool in self._tools:
                list_layout.addWidget(self._build_item_row(
                    tool.display_name,
                    tool.description,
                    lambda t=tool: self._open_item("tool", t.tool_id, t.build_widget),
                ))

        by_category = self.context.calculators.by_category()
        if not by_category and not self._tools:
            empty_label = QLabel("No calculators registered yet.")
            empty_label.setObjectName("SubtitleLabel")
            list_layout.addWidget(empty_label)
        else:
            for category in sorted(by_category.keys()):
                category_label = QLabel(category)
                category_label.setStyleSheet("font-weight: 600; margin-top: 8px;")
                list_layout.addWidget(category_label)
                for calculator in by_category[category]:
                    list_layout.addWidget(self._build_item_row(
                        calculator.display_name,
                        calculator.description,
                        lambda c=calculator: self._open_item("calculator", c.calculator_id, c.build_widget),
                    ))

        scroll.setWidget(list_container)
        outer.addWidget(scroll)
        return page

    def _build_item_row(self, display_name: str, description: str, on_open: Callable[[], None]) -> QFrame:
        row = QFrame()
        row.setObjectName("CharacterPanel")  # reuse the dashed-panel style
        layout = QHBoxLayout(row)

        text_layout = QVBoxLayout()
        title = QLabel(display_name)
        title.setStyleSheet("font-weight: 600;")
        subtitle = QLabel(description)
        subtitle.setObjectName("SubtitleLabel")
        subtitle.setWordWrap(True)
        text_layout.addWidget(title)
        text_layout.addWidget(subtitle)
        layout.addLayout(text_layout, stretch=3)

        open_button = QPushButton("Open")
        open_button.setMinimumHeight(40)
        open_button.clicked.connect(lambda checked=False: on_open())
        layout.addWidget(open_button, stretch=1)

        return row

    def _open_item(self, kind: str, item_id: str, build_widget: Callable[[], QWidget]) -> None:
        if self._stack is None:
            return

        key = (kind, item_id)
        if key not in self._item_pages:
            page = QWidget()
            outer = QVBoxLayout(page)
            outer.setContentsMargins(0, 0, 0, 0)
            outer.setSpacing(0)

            back_button = QPushButton("← Back to Toolbox")
            back_button.setObjectName("ModuleButton")
            back_button.clicked.connect(self._show_list_page)
            outer.addWidget(back_button)

            outer.addWidget(build_widget())

            self._item_pages[key] = page
            self._stack.addWidget(page)

        self._stack.setCurrentWidget(self._item_pages[key])

    def _show_list_page(self) -> None:
        if self._stack is not None and self._list_page is not None:
            self._stack.setCurrentWidget(self._list_page)
