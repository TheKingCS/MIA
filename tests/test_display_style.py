"""
Display styles (DEC-0135, core/display_style.py): each person picks the spatial look (the Nexus and rooms), the cards
look (the Dashboard and cards), or spatial on the computer and cards on the phone; in Settings, by voice, and handed to
every page through the shell.
"""

import time
from types import SimpleNamespace

import pytest

import core.config_manager as config_module
import core.profile_manager as profile_module
from core import person_settings
from core.app_context import AppContext
from core.assistant_accessibility_actions import _action_set_display_style
from core.config_manager import ConfigManager
from core.display_style import DEFAULT_STYLE, KEY, STYLES, resolve, style_of, wants_style
from core.event_bus import EventBus
from core.profile_manager import ProfileManager
from core.web_account import SETTINGS_BY_KEY, clean_setting


@pytest.fixture
def ctx(tmp_path, monkeypatch):
    """A context with profiles on temporary files and two people, Robin (signed in) and Sam."""
    monkeypatch.setattr(config_module, "_CONFIG_FILE", tmp_path / "config.json")
    monkeypatch.setattr(profile_module, "_DATA_PROFILES_DIR", tmp_path / "profiles")
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.profiles = ProfileManager(context)
    context.profiles.create_profile("Robin")
    time.sleep(0.01)
    context.other = context.profiles.create_profile("Sam", make_active=False)
    return context


def test_auto_is_spatial_on_a_computer_and_cards_on_a_phone():
    assert DEFAULT_STYLE == "auto" and set(STYLES) == {"auto", "spatial", "cards"}
    assert resolve("auto", phone=False) == "spatial" and resolve("auto", phone=True) == "cards"
    assert resolve("cards", phone=False) == "cards" and resolve("spatial", phone=True) == "spatial"
    assert resolve("purple", phone=True) == "cards"


def test_the_look_someone_asks_for_is_understood_from_everyday_words():
    assert wants_style("switch to the cards look") == "cards"
    assert wants_style("go back to the old look") == "cards"
    assert wants_style("use the portals") == "spatial"
    assert wants_style("the new look") == "spatial"
    assert wants_style("cards on my phone and spatial on the computer") == "auto"
    assert wants_style("purple") is None


def test_each_person_picks_their_own_look_by_voice(ctx):
    changed = []
    ctx.events.subscribe("display.changed", lambda **kw: changed.append(1))
    assert style_of(ctx) == "auto"
    assert "cards look" in _action_set_display_style(ctx, {"style": "the old look"}) and style_of(ctx) == "cards"
    assert "already" in _action_set_display_style(ctx, {"style": "cards"})
    assert "Nexus" in _action_set_display_style(ctx, {"style": "spatial"}) and style_of(ctx) == "spatial"
    assert "Which look" in _action_set_display_style(ctx, {"style": "purple"})
    assert len(changed) == 2
    sam = SimpleNamespace(config=ctx.config, profiles=ctx.profiles, profile_id=ctx.other.profile_id)
    assert style_of(sam) == "auto"
    person_settings.put(ctx, KEY, "neon")
    assert style_of(ctx) == "auto"


def test_the_look_is_a_setting_on_the_settings_screen_too():
    setting = SETTINGS_BY_KEY[KEY]
    assert setting.kind == "choice" and setting.default == "auto" and setting.child_ok
    assert [v for v, _ in setting.options] == ["auto", "spatial", "cards"]
    assert clean_setting(KEY, "cards") == "cards"
    with pytest.raises(ValueError):
        clean_setting(KEY, "neon")
    assert KEY in person_settings.PERSONAL_SETTINGS


def test_every_page_learns_the_persons_look_from_the_shell(ctx):
    from core.web_surfaces import _display

    assert _display(ctx) == {"style": "auto"}
    person_settings.put(ctx, KEY, "cards")
    assert _display(ctx) == {"style": "cards"}
