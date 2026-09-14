"""
modules.toolbox.tools.discovery_tool
========================================

Discovery — a ToolboxTool (same shape as PathwayTool) for
core.discovery_manager's AI-generated Mission proposals. Single-panel:
if the active profile has a pending proposal, render it with Accept/
Reject buttons; otherwise show a "Propose a Mission" button.

Generation runs off the GUI thread via core.generate_worker.GenerateWorker
(same pattern core/assistant_chat.py's memory extraction/title generation
already use) — clicking Propose never blocks the UI, and an unreachable
LLM (GenerateWorker emits None) is treated as a normal, expected outcome,
not an error: the fallback message just invites another try.

format_proposal_card_text() is a free function (not a method) — testable
without Qt, see tests/test_discovery_tool.py.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.discovery_manager import MissionProposal
from core.generate_worker import GenerateWorker
from modules.toolbox.tool_base import ToolboxTool


def format_proposal_card_text(proposal: MissionProposal) -> str:
    """Pure formatting logic — testable without Qt."""
    skills_text = ", ".join(f"{w.skill_id} +{w.xp} XP" for w in proposal.skill_rewards)
    return (
        f"{proposal.name}\n\n"
        f"{proposal.summary}\n\n"
        f"Difficulty: {proposal.difficulty}\n"
        f"Skills trained: {skills_text}\n"
        f"Reward: {proposal.reward_xp} XP, {proposal.reward_credits} credits\n\n"
        f"Why MIA suggested this: {proposal.rationale}"
    )


class DiscoveryTool(ToolboxTool):
    tool_id = "discovery"
    display_name = "Discovery"
    description = "MIA proposes a new mission based on what you've actually done."
    icon = "\U0001F9ED"  # compass

    def __init__(self, context) -> None:
        super().__init__(context)
        self._content_layout: Optional[QVBoxLayout] = None
        self._worker: Optional[GenerateWorker] = None

    def build_widget(self) -> QWidget:
        widget = QWidget()
        outer = QVBoxLayout(widget)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(12)

        title = QLabel("Discovery")
        title.setObjectName("SubtitleLabel")
        outer.addWidget(title)

        content = QWidget()
        self._content_layout = QVBoxLayout(content)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(12)
        outer.addWidget(content)
        outer.addStretch(1)

        self._refresh()
        return widget

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def _active_profile_id(self) -> Optional[str]:
        if self.context.profiles is None:
            return None
        active = self.context.profiles.get_active_profile()
        return active.profile_id if active else None

    def _clear_content(self) -> None:
        # hide()+setParent(None) before deleteLater() — a real, active
        # ghosting bug: _refresh() genuinely runs more than once here
        # (after generation/accept/reject), and deleteLater() alone
        # doesn't remove a widget from the screen immediately. Found
        # while building modules/toolbox/tools/lite_captures_tool.py
        # (same pattern, caught there by an actual screenshot showing
        # overlapping text) and fixed here too, not just there.
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            child = item.widget()
            if child is not None:
                child.hide()
                child.setParent(None)
                child.deleteLater()

    def _refresh(self) -> None:
        self._clear_content()
        if self.context.discovery is None:
            self._content_layout.addWidget(QLabel("Discovery isn't available."))
            return

        profile_id = self._active_profile_id()
        if profile_id is None:
            self._content_layout.addWidget(QLabel("Log in to a profile to get a mission proposal."))
            return

        proposal = self.context.discovery.pending_proposal_for(profile_id)
        if proposal is not None:
            self._render_pending_proposal(proposal)
        else:
            self._render_propose_button()

    def _render_propose_button(self) -> None:
        info = QLabel("Ask MIA to propose a new mission based on your real skills and progress so far.")
        info.setWordWrap(True)
        self._content_layout.addWidget(info)

        propose_button = QPushButton("Propose a Mission")
        propose_button.clicked.connect(self._on_propose_clicked)
        self._content_layout.addWidget(propose_button)

    def _render_pending_proposal(self, proposal: MissionProposal) -> None:
        card = QLabel(format_proposal_card_text(proposal))
        card.setWordWrap(True)
        card.setObjectName("CharacterPanel")
        self._content_layout.addWidget(card)

        accept_button = QPushButton("Accept")
        accept_button.clicked.connect(lambda: self._on_accept_clicked(proposal.proposal_id))
        self._content_layout.addWidget(accept_button)

        reject_button = QPushButton("Reject")
        reject_button.clicked.connect(lambda: self._on_reject_clicked(proposal.proposal_id))
        self._content_layout.addWidget(reject_button)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_propose_clicked(self) -> None:
        if self.context.llm is None:
            QMessageBox.information(None, "Assistant Unavailable", "MIA's local assistant isn't reachable right now.")
            return
        profile_id = self._active_profile_id()
        if profile_id is None:
            return

        self._clear_content()
        self._content_layout.addWidget(QLabel("MIA is thinking..."))

        prompt = self.context.discovery.build_discovery_prompt(profile_id)
        self._worker = GenerateWorker(self.context.llm, prompt)
        self._worker.result_ready.connect(lambda raw: self._on_generation_result(profile_id, raw))
        self._worker.start()

    def _on_generation_result(self, profile_id: str, raw_text) -> None:
        proposal = self.context.discovery.parse_and_validate_proposal(profile_id, raw_text)
        if proposal is None:
            self._clear_content()
            fallback = QLabel(
                "MIA couldn't come up with a mission it was confident about right now — try again."
            )
            fallback.setWordWrap(True)
            self._content_layout.addWidget(fallback)
            retry_button = QPushButton("Propose a Mission")
            retry_button.clicked.connect(self._on_propose_clicked)
            self._content_layout.addWidget(retry_button)
            return

        self.context.discovery.record_pending_proposal(proposal)
        self._refresh()

    def _on_accept_clicked(self, proposal_id: str) -> None:
        profile_id = self._active_profile_id()
        if profile_id is None:
            return
        mission = self.context.discovery.accept_proposal(profile_id, proposal_id)
        if mission is not None:
            QMessageBox.information(None, "Mission Accepted", f'"{mission.name}" is now in your Missions.')
        self._refresh()

    def _on_reject_clicked(self, proposal_id: str) -> None:
        profile_id = self._active_profile_id()
        if profile_id is None:
            return
        self.context.discovery.reject_proposal(profile_id, proposal_id)
        self._refresh()
