"""
modules.toolbox.tools.lite_captures_tool
============================================

Field Captures — a ToolboxTool for reviewing MIA Lite's pending
CaptureProposals (core/lite_capture_manager.py). Read-only transcript
+ Accept/Reject per pending capture, no editing — matches Discovery's
own "MIA proposes, you confirm, no edit step" discipline exactly. A
list, not a single-proposal view like Discovery's own tool, since
multiple field captures can genuinely queue up between review
sessions (a wearable used over a whole weekend, say), unlike
Discovery's one-active-proposal-per-profile model.

Memory extraction from an accepted capture's transcript happens
separately, in gui/home_dashboard.py (needs an async LLM call this
tool has no business owning directly — Home is the one place already
proven to keep a GenerateWorker alive long enough for a real reply,
see that module's own interview-notes extraction for the identical
reasoning, and it stays alive across module navigation so it can react
here regardless of which screen is currently visible). Accepting here
just creates the real Journal entry and fires "capture.accepted" (only
on a genuine pending->accepted transition, not on a redundant click)
so Home can pick it up.

format_capture_card_text() is a free function (not a method) —
testable without Qt.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.lite_capture_manager import CaptureProposal
from modules.toolbox.tool_base import ToolboxTool


def format_capture_card_text(proposal: CaptureProposal) -> str:
    """Pure formatting logic — testable without Qt."""
    return f"{proposal.journal_title}\n\n{proposal.transcript}"


class LiteCapturesTool(ToolboxTool):
    tool_id = "lite_captures"
    display_name = "Field Captures"
    description = "Review voice notes captured in the field before they become real Journal entries."
    icon = "\U0001F399"  # microphone

    def __init__(self, context) -> None:
        super().__init__(context)
        self._list_layout: Optional[QVBoxLayout] = None

    def build_widget(self) -> QWidget:
        widget = QWidget()
        outer = QVBoxLayout(widget)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(12)

        title = QLabel("Field Captures")
        title.setObjectName("SubtitleLabel")
        outer.addWidget(title)

        subtitle = QLabel("Voice notes captured in the field, waiting for review before they become real entries.")
        subtitle.setWordWrap(True)
        outer.addWidget(subtitle)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        self._list_layout = QVBoxLayout(content)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(12)
        scroll.setWidget(content)
        outer.addWidget(scroll, stretch=1)

        self._refresh()
        return widget

    def _clear(self) -> None:
        # hide()+setParent(None) before deleteLater() — deleteLater()
        # alone doesn't remove the widget from the screen immediately,
        # a real ghosting bug this codebase already hit once (see
        # gui/character_panel.py's _refresh_suggestions() and
        # gui/user_memory_dialog.py's own _refresh(), both fixed the
        # same way). Caught here by an actual screenshot showing old
        # and new card text superimposed, not assumed safe.
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            child = item.widget()
            if child is not None:
                child.hide()
                child.setParent(None)
                child.deleteLater()

    def _refresh(self) -> None:
        self._clear()
        if self.context.lite_captures is None:
            self._list_layout.addWidget(QLabel("Field Captures isn't available."))
            return

        pending = self.context.lite_captures.pending_proposals()
        if not pending:
            empty = QLabel("Nothing waiting for review — captures show up here once a field device syncs.")
            empty.setWordWrap(True)
            self._list_layout.addWidget(empty)
            return

        for proposal in pending:
            self._list_layout.addWidget(self._build_card(proposal))

    def _build_card(self, proposal: CaptureProposal) -> QFrame:
        card = QFrame()
        card.setObjectName("DashboardCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(6)

        text = QLabel(format_capture_card_text(proposal))
        text.setObjectName("DashboardSectionBody")
        text.setWordWrap(True)
        layout.addWidget(text)

        button_row = QHBoxLayout()
        accept_button = QPushButton("Accept")
        accept_button.clicked.connect(lambda _checked=False, pid=proposal.proposal_id: self._on_accept(pid))
        button_row.addWidget(accept_button)
        reject_button = QPushButton("Reject")
        reject_button.clicked.connect(lambda _checked=False, pid=proposal.proposal_id: self._on_reject(pid))
        button_row.addWidget(reject_button)
        layout.addLayout(button_row)

        return card

    def _on_accept(self, proposal_id: str) -> None:
        proposal = self.context.lite_captures.get_proposal(proposal_id)
        was_pending = proposal is not None and proposal.status == "pending"
        self.context.lite_captures.accept_proposal(proposal_id)
        if was_pending:
            self.context.events.publish("capture.accepted", proposal_id=proposal_id)
        self._refresh()

    def _on_reject(self, proposal_id: str) -> None:
        self.context.lite_captures.reject_proposal(proposal_id)
        self._refresh()
