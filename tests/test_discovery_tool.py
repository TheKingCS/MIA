"""
tests.test_discovery_tool
============================

Unit tests for modules.toolbox.tools.discovery_tool's pure
format_proposal_card_text(), same style as tests/test_pathway_tool.py
(no Qt event loop, no fixtures).
"""

from __future__ import annotations

from core.discovery_manager import MissionProposal
from core.gamification import SkillWeight
from modules.toolbox.tools.discovery_tool import format_proposal_card_text


def _proposal(**overrides) -> MissionProposal:
    defaults = dict(
        proposal_id="prop1",
        profile_id="p1",
        name="Build a Grow Tower",
        summary="Construct a vertical grow tower for the garden.",
        difficulty="NORMAL",
        reward_xp=30,
        reward_credits=10,
        skill_rewards=[SkillWeight(skill_id="carpentry", xp=20), SkillWeight(skill_id="framing", xp=10)],
        rationale="This builds on your carpentry progress.",
    )
    defaults.update(overrides)
    return MissionProposal(**defaults)


def test_format_proposal_card_text_includes_all_fields():
    text = format_proposal_card_text(_proposal())

    assert "Build a Grow Tower" in text
    assert "Construct a vertical grow tower for the garden." in text
    assert "Difficulty: NORMAL" in text
    assert "carpentry +20 XP" in text
    assert "framing +10 XP" in text
    assert "30 XP, 10 credits" in text
    assert "This builds on your carpentry progress." in text


def test_format_proposal_card_text_handles_a_single_skill():
    text = format_proposal_card_text(_proposal(skill_rewards=[SkillWeight(skill_id="cooking", xp=15)]))

    assert "cooking +15 XP" in text
    assert "," not in text.split("Skills trained: ")[1].split("\n")[0]
