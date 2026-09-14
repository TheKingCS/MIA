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
    build_decline_recommendation,
    build_interest_gap_recommendation,
    build_momentum_recommendation,
    declining_categories,
    format_decline_message,
    format_interest_gap_message,
    format_momentum_message,
    format_skill_decline_insights_message,
    format_skill_momentum_insights_message,
    format_skill_pattern_insights_message,
    momentum_categories,
    scan_skill_decline_insights,
    scan_skill_momentum_insights,
    scan_skill_pattern_insights,
    total_xp_in_category,
    untouched_interests,
    xp_earned_in_category_between,
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
    monkeypatch.setattr(skill_manager_module, "_SKILL_XP_LOG_FILE", data_dir / "skill_xp_log.json")
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


def _backdate_skill(context, profile_id, skill_id, when_iso):
    """Test-only reach-into-internals helper — add_skill_xp() always
    stamps "now", so backdating last_touched needs direct access, same
    as this whole session's established "mutate the object, then call
    the manager's own _save()" convention for other managers."""
    progress = context.skills.get_progress(profile_id, skill_id)
    progress.last_touched = when_iso
    context.skills._progress[(profile_id, skill_id)] = progress
    context.skills._save_progress()


# ------------------------------------------------------------------
# declining_categories (pure-ish)
# ------------------------------------------------------------------

def test_declining_categories_flags_stale_real_history(isolated_paths):
    context = _homestead_maker_context()
    context.skills.add_skill_xp("p1", "gardening", 20)
    _backdate_skill(context, "p1", "gardening", (TODAY - timedelta(days=61)).isoformat())

    assert declining_categories(context.skills, "p1", TODAY) == ["Homestead"]


def test_declining_categories_not_flagged_within_the_window(isolated_paths):
    context = _homestead_maker_context()
    context.skills.add_skill_xp("p1", "gardening", 20)
    _backdate_skill(context, "p1", "gardening", (TODAY - timedelta(days=59)).isoformat())

    assert declining_categories(context.skills, "p1", TODAY) == []


def test_declining_categories_ignores_categories_with_no_real_history(isolated_paths):
    context = _homestead_maker_context()
    assert declining_categories(context.skills, "p1", TODAY) == []  # that's interest_gap's job, not this one's


def test_declining_categories_uses_most_recent_touch_in_the_category(isolated_paths):
    context = _homestead_maker_context()
    context.skills.add_skill_xp("p1", "gardening", 20)
    _backdate_skill(context, "p1", "gardening", (TODAY - timedelta(days=90)).isoformat())
    context.skills.add_skill_xp("p1", "canning", 5)  # recent — real activity in the SAME category
    _backdate_skill(context, "p1", "canning", (TODAY - timedelta(days=1)).isoformat())

    assert declining_categories(context.skills, "p1", TODAY) == []


def test_declining_categories_no_real_last_touched_evidence_is_not_flagged(isolated_paths):
    """Real XP exists (earned before last_touched existed) but no real
    evidence of when — can't judge, must not guess "definitely stale.\""""
    context = _homestead_maker_context()
    context.skills.add_skill_xp("p1", "gardening", 20)
    _backdate_skill(context, "p1", "gardening", "")

    assert declining_categories(context.skills, "p1", TODAY) == []


# ------------------------------------------------------------------
# format_decline_message / build_decline_recommendation
# ------------------------------------------------------------------

def test_format_decline_message_single():
    assert format_decline_message(["Homestead"]) == (
        "You used to be active in Homestead, but haven't earned any real XP there in 60+ days."
    )


def test_format_decline_message_multiple():
    assert format_decline_message(["Homestead", "Maker"]) == (
        "You used to be active in Homestead and Maker, but haven't earned any real XP there in 60+ days."
    )


def test_build_decline_recommendation_single():
    assert build_decline_recommendation(["Homestead"]) == "Pick up a Mission in Homestead again, or let it go for now."


def test_build_decline_recommendation_multiple():
    assert "one of these" in build_decline_recommendation(["Homestead", "Maker"])


# ------------------------------------------------------------------
# scan_skill_decline_insights
# ------------------------------------------------------------------

def test_scan_decline_flags_a_real_stale_category(isolated_paths):
    context = _homestead_maker_context()
    context.profiles.create_profile(name="Alex")
    profile = context.profiles.list_profiles()[0]
    context.skills.add_skill_xp(profile.profile_id, "gardening", 20)
    _backdate_skill(context, profile.profile_id, "gardening", (TODAY - timedelta(days=61)).isoformat())

    new_insights = scan_skill_decline_insights(context, TODAY)

    assert len(new_insights) == 1
    assert new_insights[0].kind == "skill_decline"
    assert new_insights[0].source_id == profile.profile_id
    assert "Homestead" in new_insights[0].message
    assert len(context.insights.recommendations_for_insight(new_insights[0].insight_id)) == 1


def test_scan_decline_does_not_duplicate_on_a_second_scan(isolated_paths):
    context = _homestead_maker_context()
    context.profiles.create_profile(name="Alex")
    profile = context.profiles.list_profiles()[0]
    context.skills.add_skill_xp(profile.profile_id, "gardening", 20)
    _backdate_skill(context, profile.profile_id, "gardening", (TODAY - timedelta(days=61)).isoformat())

    first_run = scan_skill_decline_insights(context, TODAY)
    second_run = scan_skill_decline_insights(context, TODAY)

    assert len(first_run) == 1
    assert second_run == []
    assert len(context.insights.all_insights()) == 1


def test_scan_decline_resolves_once_real_xp_lands_again(isolated_paths):
    context = _homestead_maker_context()
    context.profiles.create_profile(name="Alex")
    profile = context.profiles.list_profiles()[0]
    context.skills.add_skill_xp(profile.profile_id, "gardening", 20)
    _backdate_skill(context, profile.profile_id, "gardening", (TODAY - timedelta(days=61)).isoformat())

    new_insights = scan_skill_decline_insights(context, TODAY)
    insight_id = new_insights[0].insight_id

    context.skills.add_skill_xp(profile.profile_id, "gardening", 5)  # real activity today
    scan_skill_decline_insights(context, TODAY)

    assert context.insights.get_insight(insight_id).status == "resolved"


def test_scan_decline_does_not_cross_resolve_a_different_pattern_kind(isolated_paths):
    """Same real bug class as mission_patterns.py's own regression test
    — resolution here must be scoped to kind="skill_decline" only."""
    context = _homestead_maker_context()
    context.profiles.create_profile(name="Alex")
    profile = context.profiles.list_profiles()[0]
    unrelated = context.insights.create_insight_if_new(
        source_type="patterns", source_id=profile.profile_id, kind="interest_gap",
        title="Unrelated", message="A different real pattern.",
    )

    scan_skill_decline_insights(context, TODAY)  # nothing declining -> nothing of its own to resolve

    assert context.insights.get_insight(unrelated.insight_id).status == "open"


def test_scan_decline_with_no_profiles_service_returns_empty(isolated_paths):
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.skills = SkillManager(context)
    context.insights = InsightManager(context)
    assert scan_skill_decline_insights(context, TODAY) == []


# ------------------------------------------------------------------
# format_skill_decline_insights_message
# ------------------------------------------------------------------

def test_format_skill_decline_insights_message_none_when_empty():
    assert format_skill_decline_insights_message([]) is None


# ------------------------------------------------------------------
# xp_earned_in_category_between / momentum_categories (pure-ish)
# ------------------------------------------------------------------

def _backdate_last_xp_event(context, when_iso):
    """Test-only reach-into-internals helper — add_skill_xp() always
    stamps "now" on the event it logs; backdating needs direct access,
    same convention _backdate_skill() above uses for last_touched."""
    context.skills._xp_log[-1].timestamp = when_iso
    context.skills._save_xp_log()


def test_xp_earned_in_category_between_sums_across_skills(isolated_paths):
    context = _homestead_maker_context()
    context.skills.add_skill_xp("p1", "gardening", 15)
    _backdate_last_xp_event(context, (TODAY - timedelta(days=2)).isoformat())
    context.skills.add_skill_xp("p1", "canning", 10)
    _backdate_last_xp_event(context, (TODAY - timedelta(days=3)).isoformat())
    context.skills.add_skill_xp("p1", "woodworking", 999)  # different category, must not count

    window_start = TODAY - timedelta(days=7)
    assert xp_earned_in_category_between(context.skills, "p1", "Homestead", window_start, TODAY) == 25


def test_momentum_categories_flags_a_real_burst_over_flat_prior(isolated_paths):
    context = _homestead_maker_context()
    context.skills.add_skill_xp("p1", "gardening", 40)
    _backdate_last_xp_event(context, (TODAY - timedelta(days=2)).isoformat())

    assert momentum_categories(context.skills, "p1", TODAY) == ["Homestead"]


def test_momentum_categories_not_flagged_below_the_minimum_floor(isolated_paths):
    context = _homestead_maker_context()
    context.skills.add_skill_xp("p1", "gardening", 10)  # below _MOMENTUM_MIN_RECENT_XP
    _backdate_last_xp_event(context, (TODAY - timedelta(days=2)).isoformat())

    assert momentum_categories(context.skills, "p1", TODAY) == []


def test_momentum_categories_not_flagged_when_prior_window_was_just_as_active(isolated_paths):
    context = _homestead_maker_context()
    context.skills.add_skill_xp("p1", "gardening", 40)
    _backdate_last_xp_event(context, (TODAY - timedelta(days=2)).isoformat())
    context.skills.add_skill_xp("p1", "gardening", 40)  # same pace the week before — not a "burst"
    _backdate_last_xp_event(context, (TODAY - timedelta(days=10)).isoformat())

    assert momentum_categories(context.skills, "p1", TODAY) == []


def test_momentum_categories_flagged_when_recent_clears_the_multiplier(isolated_paths):
    context = _homestead_maker_context()
    context.skills.add_skill_xp("p1", "gardening", 10)  # prior window, modest
    _backdate_last_xp_event(context, (TODAY - timedelta(days=10)).isoformat())
    context.skills.add_skill_xp("p1", "gardening", 40)  # recent window, well over 2x
    _backdate_last_xp_event(context, (TODAY - timedelta(days=2)).isoformat())

    assert momentum_categories(context.skills, "p1", TODAY) == ["Homestead"]


def test_momentum_categories_ignores_events_outside_either_window(isolated_paths):
    context = _homestead_maker_context()
    context.skills.add_skill_xp("p1", "gardening", 999)
    _backdate_last_xp_event(context, (TODAY - timedelta(days=30)).isoformat())  # long before either window

    assert momentum_categories(context.skills, "p1", TODAY) == []


# ------------------------------------------------------------------
# format_momentum_message / build_momentum_recommendation
# ------------------------------------------------------------------

def test_format_momentum_message_single():
    assert format_momentum_message(["Homestead"]) == "You've been on a roll with Homestead lately!"


def test_format_momentum_message_multiple():
    assert format_momentum_message(["Homestead", "Maker"]) == "You've been on a roll with Homestead and Maker lately!"


def test_build_momentum_recommendation_single():
    assert build_momentum_recommendation(["Homestead"]) == "Keep it going — tackle another Mission in Homestead."


def test_build_momentum_recommendation_multiple():
    assert "one of these" in build_momentum_recommendation(["Homestead", "Maker"])


# ------------------------------------------------------------------
# scan_skill_momentum_insights
# ------------------------------------------------------------------

def test_scan_momentum_flags_a_real_burst(isolated_paths):
    context = _homestead_maker_context()
    context.profiles.create_profile(name="Alex")
    profile = context.profiles.list_profiles()[0]
    context.skills.add_skill_xp(profile.profile_id, "gardening", 40)
    _backdate_last_xp_event(context, (TODAY - timedelta(days=2)).isoformat())

    new_insights = scan_skill_momentum_insights(context, TODAY)

    assert len(new_insights) == 1
    assert new_insights[0].kind == "skill_momentum"
    assert new_insights[0].source_id == profile.profile_id
    assert "Homestead" in new_insights[0].message
    assert len(context.insights.recommendations_for_insight(new_insights[0].insight_id)) == 1


def test_scan_momentum_does_not_duplicate_on_a_second_scan(isolated_paths):
    context = _homestead_maker_context()
    context.profiles.create_profile(name="Alex")
    profile = context.profiles.list_profiles()[0]
    context.skills.add_skill_xp(profile.profile_id, "gardening", 40)
    _backdate_last_xp_event(context, (TODAY - timedelta(days=2)).isoformat())

    first_run = scan_skill_momentum_insights(context, TODAY)
    second_run = scan_skill_momentum_insights(context, TODAY)

    assert len(first_run) == 1
    assert second_run == []
    assert len(context.insights.all_insights()) == 1


def test_scan_momentum_resolves_once_the_burst_ages_out(isolated_paths):
    context = _homestead_maker_context()
    context.profiles.create_profile(name="Alex")
    profile = context.profiles.list_profiles()[0]
    context.skills.add_skill_xp(profile.profile_id, "gardening", 40)
    _backdate_last_xp_event(context, (TODAY - timedelta(days=2)).isoformat())

    new_insights = scan_skill_momentum_insights(context, TODAY)
    insight_id = new_insights[0].insight_id

    later = TODAY + timedelta(days=10)  # the burst is now outside the recent window, nothing replaced it
    scan_skill_momentum_insights(context, later)

    assert context.insights.get_insight(insight_id).status == "resolved"


def test_scan_momentum_does_not_cross_resolve_a_different_pattern_kind(isolated_paths):
    """Same real bug class as mission_patterns.py's own regression test
    — resolution here must be scoped to kind="skill_momentum" only."""
    context = _homestead_maker_context()
    context.profiles.create_profile(name="Alex")
    profile = context.profiles.list_profiles()[0]
    unrelated = context.insights.create_insight_if_new(
        source_type="patterns", source_id=profile.profile_id, kind="skill_decline",
        title="Unrelated", message="A different real pattern.",
    )

    scan_skill_momentum_insights(context, TODAY)  # no burst -> nothing of its own to resolve

    assert context.insights.get_insight(unrelated.insight_id).status == "open"


def test_scan_momentum_with_no_profiles_service_returns_empty(isolated_paths):
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.skills = SkillManager(context)
    context.insights = InsightManager(context)
    assert scan_skill_momentum_insights(context, TODAY) == []


# ------------------------------------------------------------------
# format_skill_momentum_insights_message
# ------------------------------------------------------------------

def test_format_skill_momentum_insights_message_none_when_empty():
    assert format_skill_momentum_insights_message([]) is None
