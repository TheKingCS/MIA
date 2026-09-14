"""
gui.memory_connections_dialog
================================

"Memory Connections" — the graph/tree visualization docs/VISION.md
flagged as real, separate UI scope, deliberately not attempted in the
2026-09-10 "Memory Palace" pass that built the underlying relation
(core.user_memory_manager.related_memories(), surfaced there only as
a one-line "Related: ..." per row in gui/user_memory_dialog.py).

Opened from that dialog's own "View Connections" button. Read-only,
same stance as the dialog it's opened from — these relations are
discovered automatically, never hand-authored.

No QTreeWidget: checked first, nothing in this codebase uses one —
every existing hierarchical screen (e.g. modules/classroom/module.py's
Subjects->Courses->Lessons) is a QStackedWidget drill-down or a flat
QListWidget. core.user_memory_manager.memory_relationship_trees()
already returns a real tree (MemoryTreeNode.children), so this dialog
renders it recursively as nested, indented cards instead of reaching
for an unprecedented widget type — the DATA is a real tree either way.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSpacerItem,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.app_context import AppContext
from core.user_memory_manager import MemoryTreeNode, memory_relationship_trees

_INDENT_PER_DEPTH = 24


class MemoryConnectionsDialog(QDialog):
    def __init__(self, context: AppContext, parent=None) -> None:
        super().__init__(parent)
        self.context = context
        self.setWindowTitle("Memory Connections")
        self.resize(480, 520)

        layout = QVBoxLayout(self)

        subtitle = QLabel(
            "Memories MIA has noticed are connected — grouped automatically, never hand-linked."
        )
        subtitle.setObjectName("SubtitleLabel")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._list_container = QWidget()
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._list_layout.setSpacing(10)
        scroll.setWidget(self._list_container)
        layout.addWidget(scroll, stretch=1)

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)

        self._refresh()

    def _refresh(self) -> None:
        all_memories = self.context.user_memories.all_memories() if self.context.user_memories is not None else []
        trees = memory_relationship_trees(all_memories)

        if not trees:
            message = (
                "No connections yet — MIA will find these automatically as it learns more about you."
                if not all_memories else
                "Nothing connects yet — these memories don't share enough in common."
            )
            empty_label = QLabel(message)
            empty_label.setObjectName("SubtitleLabel")
            empty_label.setWordWrap(True)
            self._list_layout.addWidget(empty_label)
            return

        for tree in trees:
            card = QFrame()
            card.setObjectName("DashboardCard")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(14, 10, 14, 10)
            card_layout.setSpacing(4)
            self._add_node(card_layout, tree, depth=0)
            self._list_layout.addWidget(card)

    def _add_node(self, layout: QVBoxLayout, node: MemoryTreeNode, depth: int) -> None:
        row = QHBoxLayout()
        if depth > 0:
            row.addSpacerItem(QSpacerItem(depth * _INDENT_PER_DEPTH, 1, QSizePolicy.Policy.Fixed))
        prefix = "↳ " if depth > 0 else ""  # ↳ for a child row, nothing for the root
        text_label = QLabel(f"{prefix}[{node.memory.category}]  {node.memory.text}")
        text_label.setObjectName("DashboardSectionBody" if depth == 0 else "SubtitleLabel")
        text_label.setWordWrap(True)
        row.addWidget(text_label, stretch=1)
        layout.addLayout(row)

        for child in node.children:
            self._add_node(layout, child, depth + 1)
