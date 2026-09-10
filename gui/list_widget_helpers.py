"""
gui.list_widget_helpers
=========================

Small, shared QListWidget helpers reused across every module that
builds a filterable list of records (Budget's bills/income/expenses,
Real Estate's properties, Music's library/playlists, ...) — same
"modules import a plain helper from gui/" precedent already used
throughout this app for dialog classes.
"""

from __future__ import annotations

from typing import Any, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListWidget, QListWidgetItem


def add_empty_state_item(list_widget: QListWidget, message: str) -> None:
    """A single, non-selectable, disabled placeholder row — call only
    when the list is genuinely empty, so a first-time user sees real
    guidance instead of a blank void. Being non-selectable/disabled
    means it can never be mistaken for a real record by a
    selected_item_data() caller."""
    item = QListWidgetItem(message)
    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable & ~Qt.ItemFlag.ItemIsEnabled)
    list_widget.addItem(item)


def selected_item_data(list_widget: QListWidget) -> Optional[Any]:
    """None unless the current item is genuinely selected — Qt's
    default ExtendedSelection mode keeps currentItem() set even after
    a Ctrl+click deselects that row (clearSelection() doesn't clear
    currentItem()), so checking currentItem() alone can silently act
    on a row that looks unselected. The real fix for every "Edit
    Selected"/"Delete Selected"-style button in this app."""
    item = list_widget.currentItem()
    if item is None or not item.isSelected():
        return None
    return item.data(Qt.ItemDataRole.UserRole)
