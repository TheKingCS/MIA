"""
Each person's Apps screen (core/focus_presets.py) and MIA's setup
questions (gui/onboarding_dialog.py), 2026-10-01.
"""

import time
from types import SimpleNamespace

import pytest

import core.config_manager as config_module
import core.profile_manager as profile_module
from core import focus_presets, person_settings
from core.app_context import AppContext
from core.assistant_focus_actions import _action_get_app_focus, _action_set_app_focus, _action_set_app_visibility
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.focus_presets import ALWAYS_VISIBLE, FOCUSES, arrange, describe, find_focus, interests_for, recommend
from core.profile_manager import ProfileManager

_APPS = ["dashboard", "assistant", "budget", "kitchen", "lab", "classroom", "greenhouse", "settings", "module_browser",
         "notes", "workout"]


def _modules(ids=_APPS):
    return [SimpleNamespace(module_id=i, display_name=i.replace("_", " ").title()) for i in ids]


@pytest.fixture
def people(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module, "_CONFIG_FILE", tmp_path / "config.json")
    monkeypatch.setattr(profile_module, "_DATA_PROFILES_DIR", tmp_path / "profiles")
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.profiles = ProfileManager(context)
    zac = context.profiles.create_profile("Zac", make_active=True)
    time.sleep(0.01)
    sam = context.profiles.create_profile("Sam", make_active=False)
    modules = _modules()
    context.module_manager = SimpleNamespace(all=lambda: modules, enabled_modules=lambda: modules)
    return context, zac, sam


# ------------------------------------------------------------------ pure logic


def test_goals_pick_a_focus_and_add_their_apps():
    rec = recommend(["school", "health"])
    assert rec.focus_id == "student" and rec.featured[0] == "assistant" and "classroom" in rec.featured
    assert "workout" in rec.featured
    land = recommend(["land", "building", "money"])
    assert land.focus_id == "homestead" and {"greenhouse", "workshop", "toolbox", "budget"} <= set(land.featured)
    # Nothing a goal asks for is ever tucked away.
    biz = recommend(["business", "building"])
    assert biz.focus_id == "business" and "workshop" in biz.featured and "workshop" not in biz.hidden
    assert recommend([]).focus_id == "personal" and recommend(["nonsense"]).focus_id == "personal"
    # Ties go to the more specific focus.
    assert recommend(["home", "land"]).focus_id == "homestead"


def test_no_focus_ever_hides_the_way_around():
    for focus in FOCUSES.values():
        assert not set(focus.hidden) & set(ALWAYS_VISIBLE), focus.focus_id
        assert not set(focus.hidden) & set(focus.featured), focus.focus_id


def test_arrange_puts_featured_first_and_leaves_hidden_out():
    arranged = [m.module_id for m in arrange(_modules(), ["kitchen", "budget", "missing"], ["lab", "settings"])]
    assert arranged[:2] == ["kitchen", "budget"] and "lab" not in arranged and "settings" in arranged
    assert len(arranged) == len(_APPS) - 1
    assert [m.module_id for m in arrange(_modules(), [], [])] == _APPS  # no choice yet: as before


def test_interests_and_wording():
    assert interests_for(["land", "health", "money"], ["Body", "Homestead", "Mind", "Outdoor"]) == ["Body", "Homestead", "Outdoor"]
    text = describe(recommend(["school"]), {"classroom": "Classroom", "notes": "Notes", "lab": "The Lab",
                                           "assistant": "Assistant"})
    assert "Student" in text and "Classroom" in text and "The Lab" in text and "Assistant" not in text
    assert find_focus("put me in homesteading mode").focus_id == "homestead"
    assert find_focus("my business").focus_id == "business" and find_focus("??") is None


# ------------------------------------------------------------------ each person's own


def test_each_person_has_their_own_apps_screen(people):
    context, zac, sam = people
    sam_view = SimpleNamespace(config=context.config, profiles=context.profiles, events=context.events,
                               profile_id=sam.profile_id, module_manager=context.module_manager)
    changed = []
    context.events.subscribe("apps.arrangement_changed", lambda **kw: changed.append(1))
    focus_presets.apply_focus(sam_view, "student")
    assert changed
    sam_menu = [m.module_id for m in focus_presets.menu_modules(sam_view, _modules())]
    zac_menu = [m.module_id for m in focus_presets.menu_modules(context, _modules())]
    assert sam_menu[1] == "classroom" and "lab" not in sam_menu
    assert zac_menu == _APPS
    assert focus_presets.set_app_visible(sam_view, "lab", True)
    assert "lab" in [m.module_id for m in focus_presets.menu_modules(sam_view, _modules())]
    assert not focus_presets.set_app_visible(sam_view, "settings", False)


def test_assistant_tools(people):
    context, _, _ = people
    assert "Business" in _action_set_app_focus(context, {"focus": "my business"})
    assert focus_presets.current(context)[0] == "business"
    assert "tucked" in _action_set_app_visibility(context, {"app": "the kitchen", "visible": False})
    assert "kitchen" in focus_presets.current(context)[2]
    assert "back" in _action_set_app_visibility(context, {"app": "Kitchen", "visible": True})
    assert "always stays" in _action_set_app_visibility(context, {"app": "Settings", "visible": False})
    assert "Which app" in _action_set_app_visibility(context, {"app": "spaceship", "visible": False})
    assert "Business" in _action_get_app_focus(context, {})
    assert "Which focus" in _action_set_app_focus(context, {"focus": "astronaut"})


# ------------------------------------------------------------------ the setup conversation


@pytest.fixture
def qapp():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def test_setup_questions_save_for_that_person(people, qapp):
    from gui.onboarding_dialog import OnboardingDialog, module_names

    context, zac, sam = people
    dialog = OnboardingDialog(context, sam, module_names(context.module_manager))
    dialog._goal_buttons["school"].setChecked(True)
    dialog._goal_buttons["health"].setChecked(True)
    dialog.next_button.click()
    dialog._speak_group.button(0).setChecked(True)  # rarely
    dialog.next_button.click()
    dialog._notes_edit.setPlainText("I'm studying nursing")
    dialog.next_button.click()
    assert dialog.recommendation.focus_id == "student"
    dialog.next_button.click()  # "Sounds good"
    sam_view = SimpleNamespace(config=context.config, profiles=context.profiles, profile_id=sam.profile_id)
    assert focus_presets.current(sam_view)[0] == "student"
    assert person_settings.get(sam_view, "communication.daily_budget", 5) == 2
    assert person_settings.get(sam_view, "setup.questions_done") is True
    saved = context.profiles.get_profile(sam.profile_id)
    assert saved.interview_notes == "I'm studying nursing"
    assert focus_presets.current(context)[0] is None  # Zac (signed in) untouched


def test_skipping_keeps_every_app(people, qapp):
    from gui.onboarding_dialog import OnboardingDialog

    context, zac, _ = people
    dialog = OnboardingDialog(context, zac, {})
    dialog.skip_button.click()
    assert focus_presets.current(context) == (None, [], [])
    assert person_settings.get(context, "setup.questions_done") is True
