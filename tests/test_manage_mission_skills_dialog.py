"""
tests.test_manage_mission_skills_dialog
==========================================

Unit tests for gui.manage_mission_skills_dialog's pure
format_skill_reward_row() function, same style as
tests/test_manage_project_skills_dialog.py (no Qt event loop, no
fixtures).
"""

from __future__ import annotations

from gui.manage_mission_skills_dialog import format_skill_reward_row


class _FakeSkillDefinition:
    def __init__(self, name):
        self.name = name


class _FakeSkills:
    def __init__(self, definitions):
        self._definitions = definitions

    def get_skill(self, skill_id):
        return self._definitions.get(skill_id)


class _FakeContext:
    def __init__(self, skills=None):
        self.skills = skills


def test_format_skill_reward_row_known_skill():
    context = _FakeContext(skills=_FakeSkills({"aquaponics": _FakeSkillDefinition("Aquaponics")}))
    assert format_skill_reward_row(context, "aquaponics", 120) == "Aquaponics: 120 XP"


def test_format_skill_reward_row_unknown_skill_falls_back_to_id():
    context = _FakeContext(skills=_FakeSkills({}))
    assert format_skill_reward_row(context, "stale_id", 10) == "stale_id: 10 XP"


def test_format_skill_reward_row_no_skills_service_falls_back_to_id():
    context = _FakeContext(skills=None)
    assert format_skill_reward_row(context, "aquaponics", 10) == "aquaponics: 10 XP"
