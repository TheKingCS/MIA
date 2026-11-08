"""
Themes (DEC-0136, core/themes.py): a theme is data checked against what a theme may change, so no theme can restyle
a warning or inject anything; each person picks theirs in Settings or by voice, and every page gets it with the shell.
"""

import time
from types import SimpleNamespace

import pytest

import core.config_manager as config_module
import core.profile_manager as profile_module
from core import person_settings
from core.app_context import AppContext
from core.assistant_accessibility_actions import _action_set_theme
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.profile_manager import ProfileManager
from core.themes import KEY, MATERIALS, THEMES, TOKENS, as_data, clean_theme, for_shell, theme_of, wants_theme
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


def test_every_built_in_theme_survives_its_own_check_unchanged():
    assert list(THEMES)[:4] == ["stark", "y2k", "cyberpunk", "glass"]
    for theme in THEMES.values():
        data = clean_theme(as_data(theme))
        assert data["tokens"] == theme.tokens and data["material"] in MATERIALS, theme.id
        assert set(data["room"]) == set(theme.room), theme.id


def test_no_theme_can_change_what_a_colour_means():
    for meaning in ("--attention", "--bad", "--ok", "--win", "--soon", "--rarity-legendary", "--rgb-amber", "--rgb-bad"):
        assert meaning not in TOKENS
    data = clean_theme({"id": "sneaky", "name": "Sneaky", "tokens": {"--attention": "#00ff00", "--accent": "#123456"}})
    assert data["tokens"] == {"--accent": "#123456"}


def test_a_theme_cannot_break_out_of_css_or_reach_the_network():
    data = clean_theme({"id": "x", "name": "X", "material": "lava", "tokens": {
        "--bg": "#000; } body { display: none", "--theme-backdrop": "url(https://example.com/a.png)",
        "--font": "Comic Sans MS</style><script>", "--text": "#fff"},
        "room": {"accent": "red", "fire": 9, "bloom": "lots", "palette": ["#ff00ff", "nope", "#00ffff"]}})
    assert data["tokens"] == {"--text": "#fff"} and data["material"] == "solid"
    assert data["room"] == {"fire": 2.0, "palette": ["#ff00ff", "#00ffff"]}
    with pytest.raises(ValueError):
        clean_theme({"id": "Bad Id!", "name": "x"})


def test_the_theme_someone_asks_for_is_understood_from_everyday_words():
    assert wants_theme("switch to the Y2K theme") == "y2k"
    assert wants_theme("give me the myspace look") == "y2k"
    assert wants_theme("make it cyberpunk") == "cyberpunk"
    assert wants_theme("something minimal") == "glass"
    assert wants_theme("back to Stark") == "stark"
    assert wants_theme("cyberpunk or y2k") is None and wants_theme("purple") is None


def test_each_person_picks_their_own_theme_by_voice_and_in_settings(ctx):
    changed = []
    ctx.events.subscribe("display.changed", lambda **kw: changed.append(1))
    assert theme_of(ctx) == "stark" and for_shell(ctx)["id"] == "stark"
    assert _action_set_theme(ctx, {"theme": "the y2k one"}) == "Switched to the Y2K Cyber theme."
    assert theme_of(ctx) == "y2k" and for_shell(ctx)["material"] == "chrome"
    assert "already" in _action_set_theme(ctx, {"theme": "y2k"})
    assert "Which theme" in _action_set_theme(ctx, {"theme": "purple"})
    assert changed == [1]
    sam = SimpleNamespace(config=ctx.config, profiles=ctx.profiles, profile_id=ctx.other.profile_id)
    assert theme_of(sam) == "stark"
    setting = SETTINGS_BY_KEY[KEY]
    assert setting.kind == "choice" and [v for v, _ in setting.options] == list(THEMES)
    assert clean_setting(KEY, "glass") == "glass" and KEY in person_settings.PERSONAL_SETTINGS
    person_settings.put(ctx, KEY, "vaporwave")
    assert theme_of(ctx) == "stark"


def test_every_page_gets_the_persons_theme_with_the_shell(ctx):
    from core.web_surfaces import _display

    person_settings.put(ctx, KEY, "cyberpunk")
    display = _display(ctx)
    assert display["style"] == "auto" and display["theme"]["id"] == "cyberpunk" and display["theme"]["room"]["scan"] > 0


def test_every_page_with_the_design_tokens_also_loads_the_materials():
    from pathlib import Path

    web = Path(__file__).resolve().parent.parent / "web"
    for page in web.glob("*.html"):
        html = page.read_text(encoding="utf-8")
        if 'href="tokens.css"' in html:
            assert html.index('href="tokens.css"') < html.index('href="themes.css"'), page.name
