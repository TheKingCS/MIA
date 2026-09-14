"""
tests.test_skill_patterns
============================

Unit tests for core.skill_patterns — isolates _DATA_DIR for
profile/skill/insight files into a tmp_path scratch area, same
monkeypatch pattern as test_mission_patterns.py's own isolated_paths.
"""

from __future__ import annotations

import json
from datetime import date, timedelta

import pytest

import core.config_manager as config_manager_module
import core.insight_manager as insight_manager_module
import core.profile_manager as profile_manager_module
import core.skill_manager as skill_manager_module
from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.insight_manager import InsightManager
from core.profile_manager import Profile, ProfileManager
from core.skill_manager import SkillManager
from core.skill_patterns import (
    build_interest_gap_recommendation,
    format_interest_gap_message,
    format_skill_pattern_insights_message,
    scan_skill_pattern_insights,
    total_xp_in_category,
    untouched_interests,
)

TODAY = date(2026, 9, 14)


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    monkeypatch.setattr(config_manager_module, "_CONFIG_FILE", tmp_path / "config.json")
    monkeypatch.setattr(profile_manager_module, "_DATA_PROFILES_DIR", tmp_path / "profiles")
    monkeypatch.setattr(skill_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(skill_manager_module, "_SKILL_DEFINITIONS_FILE", data_dir / "skill_definitions.json")
    monkeypatch.setattr(skill_manager_module, "_SKILL_PROGRESS_FILE", data_dir / "skill_progress.json")
    monkeypatch.setattr(insight_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(insight_manager_module, "_INSIGHTS_FILE", data_dir / "insights.json")
    monkeypatch.setattr(insight_manager_module, "_RECOMMENDATIONS_FILE", data_dir / "recommendations.json")
    return data_dir


def _make_context(skills: list[dict]) -> AppContext:
    skill_manager_module._DATA_DIR.mkdir(parents=True, exist_ok=True)
    skill_manager_module._SKILL_DEFINITIONS_FILE.write_text(json.dumps({"skills": skills}))
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.profiles = ProfileManager(context)
    context.skills = SkillManager(context)
    context.insights = InsightManager(context)
    return context


def _homestead_maker_context() -> AppContext:
    return _make_context([
        {"skill_id": "gardening", "name": "Gardening", "category": "Homestead"},
        {"skill_id": "canning", "name": "Canning", "category": "Homestead"},
        {"skill_id": "woodworking", "name": "Woodworking", "category": "Maker"},
    ])


def _profile(**overrides) -> Profile:
    defaults = dict(profile_id="p1", name="Alex", created_at="2026-08-01T10:00:00", interests=["Homestead"])
    defaults.update(overrides)
    return Profile(**defaults)


# ------------------------------------------------------------------
# total_xp_in_category / untouched_interests (pure-ish)
# ------------------------------------------------------------------

def test_total_xp_in_category_zero_when_untouched(isolated_paths):
    context = _homestead_maker_context()
    assert total_xp_in_category(context.skills, "p1", "Homestead") == 0


def test_total_xp_in_category_sums_across_skills_in_that_category(isolated_paths):
    context = _homestead_maker_context()
    context.skills.add_skill_xp("p1", "gardening", 30)
    context.skills.add_skill_xp("p1", "canning", 10)
    context.skills.add_skill_xp("p1", "woodworking", 999)  # different category, must not count

    assert total_xp_in_category(context.skills, "p1", "Homestead") == 40


def test_untouched_interests_returns_only_zero_xp_categories(isolated_paths):
    context = _homestead_maker_context()
    context.skills.add_skill_xp("p1", "gardening", 10)  # Homestead now touched
    profile = _profile(interests=["Homestead", "Maker"])

    assert untouched_interests(context.skills, profile) == ["Maker"]


def test_untouched_interests_empty_when_no_interests_stated(isolated_paths):
    context = _homestead_maker_context()
    profile = _profile(interests=[])
    assert untouched_interests(context.skills, profile) == []


# ------------------------------------------------------------------
# format_interest_gap_message / build_interest_gap_recommendation
# ------------------------------------------------------------------

def test_format_interest_gap_message_single():
    assert format_interest_gap_message(["Homestead"]) == (
        "You said you're interested in Homestead, but haven't earned any real XP there yet."
    )


def test_format_interest_gap_message_two():
    assert format_interest_gap_message(["Homestead", "Maker"]) == (
        "You said you're interested in Homestead and Maker, but haven't earned any real XP there yet."
    )


def test_format_interest_gap_message_three():
    assert format_interest_gap_message(["Homestead", "Maker", "Mind"]) == (
        "You said you're interested in Homestead, Maker, and Mind, but haven't earned any real XP there yet."
    )


def test_build_interest_gap_recommendation_single():
    assert build_interest_gap_recommendation(["Homestead"]) == "Try a Mission or Pathway in Homestead to get started."


def test_build_interest_gap_recommendation_multiple():
    assert "one of these categories" in build_interest_gap_recommendation(["Homestead", "Maker"])


# ------------------------------------------------------------------
# scan_skill_pattern_insights
# ------------------------------------------------------------------

def test_scan_flags_an_untouched_interest_for_an_old_enough_profile(isolated_paths):
    context = _homestead_maker_context()
    old_enough = (TODAY - timedelta(days=31)).isoformat()
    context.profiles.create_profile(name="Alex")
    profile = context.profiles.list_profiles()[0]
    context.profiles.set_interview_answers(profile.profile_id, ["Homestead"], "")
    # Force the profile old enough — create_profile() stamps "now".
    raw = context.config.get(f"profiles.{profile.profile_id}")
    raw["created_at"] = old_enough
    context.config.set(f"profiles.{profile.profile_id}", raw)
    context.config.save()

    new_insights = scan_skill_pattern_insights(context, TODAY)

    assert len(new_insights) == 1
    assert new_insights[0].kind == "interest_gap"
    assert new_insights[0].source_id == profile.profile_id
    assert "Homestead" in new_insights[0].message
    assert len(context.insights.recommendations_for_insight(new_insights[0].insight_id)) == 1


def test_scan_does_not_flag_a_brand_new_profile(isolated_paths):
    context = _homestead_maker_context()
    context.profiles.create_profile(name="Alex")
    profile = context.profiles.list_profiles()[0]
    context.profiles.set_interview_answers(profile.profile_id, ["Homestead"], "")

    assert scan_skill_pattern_insights(context, TODAY) == []


def test_scan_does_not_flag_a_touched_interest(isolated_paths):
    context = _homestead_maker_context()
    context.profiles.create_profile(name="Alex")
    profile = context.profiles.list_profiles()[0]
    context.profiles.set_interview_answers(profile.profile_id, ["Homestead"], "")
    old_enough = (TODAY - timedelta(days=31)).isoformat()
    raw = context.config.get(f"profiles.{profile.profile_id}")
    raw["created_at"] = old_enough
    context.config.set(f"profiles.{profile.profile_id}", raw)
    context.config.save()
    context.skills.add_skill_xp(profile.profile_id, "gardening", 10)

    assert scan_skill_pattern_insights(context, TODAY) == []


def test_scan_does_not_duplicate_on_a_second_scan(isolated_paths):
    context = _homestead_maker_context()
    context.profiles.create_profile(name="Alex")
    profile = context.profiles.list_profiles()[0]
    context.profiles.set_interview_answers(profile.profile_id, ["Homestead"], "")
    old_enough = (TODAY - timedelta(days=31)).isoformat()
    raw = context.config.get(f"profiles.{profile.profile_id}")
    raw["created_at"] = old_enough
    context.config.set(f"profiles.{profile.profile_id}", raw)
    context.config.save()

    first_run = scan_skill_pattern_insights(context, TODAY)
    second_run = scan_skill_pattern_insights(context, TODAY)

    assert len(first_run) == 1
    assert second_run == []
    assert len(context.insights.all_insights()) == 1


def test_scan_resolves_insight_once_real_xp_lands(isolated_paths):
    context = _homestead_maker_context()
    context.profiles.create_profile(name="Alex")
    profile = context.profiles.list_profiles()[0]
    context.profiles.set_interview_answers(profile.profile_id, ["Homestead"], "")
    old_enough = (TODAY - timedelta(days=31)).isoformat()
    raw = context.config.get(f"profiles.{profile.profile_id}")
    raw["created_at"] = old_enough
    context.config.set(f"profiles.{profile.profile_id}", raw)
    context.config.save()

    new_insights = scan_skill_pattern_insights(context, TODAY)
    insight_id = new_insights[0].insight_id

    context.skills.add_skill_xp(profile.profile_id, "gardening", 10)
    scan_skill_pattern_insights(context, TODAY)

    assert context.insights.get_insight(insight_id).status == "resolved"


def test_scan_with_no_profiles_service_returns_empty(isolated_paths):
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.skills = SkillManager(context)
    context.insights = InsightManager(context)
    assert scan_skill_pattern_insights(context, TODAY) == []


def test_scan_with_no_skills_service_returns_empty(isolated_paths):
    context = _homestead_maker_context()
    context.skills = None
    context.profiles.create_profile(name="Alex")
    assert scan_skill_pattern_insights(context, TODAY) == []


def test_scan_with_no_insights_service_returns_empty(isolated_paths):
    context = _homestead_maker_context()
    context.insights = None
    context.profiles.create_profile(name="Alex")
    assert scan_skill_pattern_insights(context, TODAY) == []


# ------------------------------------------------------------------
# format_skill_pattern_insights_message
# ------------------------------------------------------------------

def test_format_skill_pattern_insights_message_none_when_empty():
    assert format_skill_pattern_insights_message([]) is None
