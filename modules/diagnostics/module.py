"""
modules.diagnostics.module
============================

Diagnostics: system health and the in-app log viewer.

The log viewer is the first genuinely useful piece of this module (per
docs/ROADMAP.md's v0.2 milestone 2.6) — it tails core/logger.py's
logs/mia.log so a field deployment can be debugged without pulling out
a laptop or hunting for the file on a headless Pi.

tail_lines() / filter_lines() are free functions (not methods) so they
can be unit tested without a Qt event loop — see
tests/test_diagnostics_log_viewer.py. The QWidget-building side of
get_widget() is exercised manually instead; see
docs/testing/2.6_system_logs_viewer.md.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.logger import get_logger
from modules.module_base import ModuleBase

log = get_logger(__name__)

_LOG_FILE = Path(__file__).resolve().parent.parent.parent / "logs" / "mia.log"
_MAX_DISPLAY_LINES = 1000
_LOG_LEVELS = ["ALL", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


def tail_lines(path: Path, max_lines: int) -> list[str]:
    """
    Return up to the last `max_lines` lines of `path`, oldest first.
    Returns an empty list if the file doesn't exist yet (e.g. a very
    first run before anything has logged).
    """
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    return [line.rstrip("\n") for line in lines[-max_lines:]]


def filter_lines(lines: list[str], level: str, query: str) -> list[str]:
    """
    Filter log lines by level and a case-insensitive substring query.

    Matches against the "[LEVELNAME ]" field core.logger's formatter
    (fmt="...[%(levelname)-8s]...") pads every line to — level="ALL" or
    a falsy value disables the level filter.
    """
    result = lines
    if level and level != "ALL":
        needle = f"[{level:<8}]"
        result = [line for line in result if needle in line]
    if query:
        query_lower = query.lower()
        result = [line for line in result if query_lower in line.lower()]
    return result


class DiagnosticsModule(ModuleBase):
    module_id = "diagnostics"
    display_name = "Diagnostics"
    description = "System health, logs, and hardware status."
    icon = "\U0001FA7A"  # stethoscope

    def __init__(self, context) -> None:
        super().__init__(context)
        self._log_view: QPlainTextEdit | None = None
        self._level_combo: QComboBox | None = None
        self._search_edit: QLineEdit | None = None
        self._info_label: QLabel | None = None

    def get_widget(self) -> QWidget:
        widget = QWidget()
        outer = QVBoxLayout(widget)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(12)

        header = QLabel(f"{self.icon}  {self.display_name}")
        header.setObjectName("TitleLabel")
        outer.addWidget(header)

        subtitle = QLabel(self.description)
        subtitle.setObjectName("SubtitleLabel")
        outer.addWidget(subtitle)

        toolbar = QHBoxLayout()

        toolbar.addWidget(QLabel("Level:"))
        self._level_combo = QComboBox()
        self._level_combo.addItems(_LOG_LEVELS)
        self._level_combo.currentTextChanged.connect(self._refresh)
        toolbar.addWidget(self._level_combo)

        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("Filter log text…")
        self._search_edit.textChanged.connect(self._refresh)
        toolbar.addWidget(self._search_edit, stretch=1)

        refresh_button = QPushButton("\U0001F504 Refresh")
        refresh_button.setObjectName("ModuleButton")
        refresh_button.clicked.connect(self._refresh)
        toolbar.addWidget(refresh_button)

        outer.addLayout(toolbar)

        self._info_label = QLabel("")
        self._info_label.setObjectName("SubtitleLabel")
        outer.addWidget(self._info_label)

        self._log_view = QPlainTextEdit()
        self._log_view.setObjectName("LogView")
        self._log_view.setReadOnly(True)
        self._log_view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        outer.addWidget(self._log_view, stretch=1)

        self._refresh()
        return widget

    def _refresh(self) -> None:
        if self._log_view is None:
            return

        all_lines = tail_lines(_LOG_FILE, _MAX_DISPLAY_LINES)
        level = self._level_combo.currentText() if self._level_combo else "ALL"
        query = self._search_edit.text() if self._search_edit else ""
        shown = filter_lines(all_lines, level, query)

        if not all_lines:
            self._info_label.setText(f"No log file found yet at {_LOG_FILE}.")
        else:
            self._info_label.setText(
                f"Showing {len(shown)} of {len(all_lines)} lines "
                f"(most recent {_MAX_DISPLAY_LINES} lines of {_LOG_FILE})."
            )

        self._log_view.setPlainText("\n".join(shown))
        scrollbar = self._log_view.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
