"""
Themes (DEC-0136, core/themes.py): a theme is data checked against what a theme may change, so no theme can restyle
a warning or inject anything; each person picks theirs in Settings or by voice, and every page gets it with the shell.
The Theme Studio builds a theme from a few choices, refuses warning-coloured accents and unreadable text, and saves,
uses and deletes a person's own themes; themes go out and come back as files, and MIA designs one from a description.
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


def test_the_studio_builds_a_theme_from_a_few_choices_and_reads_one_back():
    from core.themes import build_theme, choices_of

    y2k = as_data(THEMES["y2k"])
    picks = choices_of(y2k)
    assert picks["accent"] == "#ff5ce6" and picks["font"] == "y2k" and picks["material"] == "chrome" and picks["radius"] == 14
    picks.update(accent="#8a5cff", radius=40)
    theme = build_theme(picks, y2k, "my_violet", "Violet")
    assert theme["tokens"]["--accent"] == "#8a5cff" and theme["tokens"]["--rgb-accent"] == "138, 92, 255"
    assert theme["tokens"]["--radius"] == "28px" and theme["choices"]["radius"] == 28
    assert theme["tokens"]["--theme-backdrop"] == y2k["tokens"]["--theme-backdrop"]  # the base's backdrop stays
    assert theme["room"]["accent"] == "#8a5cff" and theme["room"]["palette"] == y2k["room"]["palette"]
    assert choices_of(theme)["accent"] == "#8a5cff"


def test_an_accent_that_looks_like_a_warning_or_text_too_faint_to_read_is_refused():
    from core.themes import STARK_CHOICES, accent_problem, build_theme, contrast

    assert "amber" in accent_problem("#f2b33d") and "amber" in accent_problem("#ff9a00")
    assert "red" in accent_problem("#e53935") and "green" in accent_problem("#4fc48c")
    for fine in ("#35d4ff", "#ff5ce6", "#8a5cff", "#96d6ff", "#e8f0ff", "#c0c8d4"):
        assert accent_problem(fine) is None, fine
    assert contrast("#ffffff", "#000000") > 20
    with pytest.raises(ValueError):
        build_theme({**STARK_CHOICES, "accent": "#ff9a00"})
    with pytest.raises(ValueError):
        build_theme({**STARK_CHOICES, "text": "#20242a"})


def test_saving_using_and_deleting_a_theme_of_your_own(ctx):
    from core.actions import ActionError
    from core.theme_actions import _delete, _describe_delete, _describe_save, _save
    from core.themes import all_themes, choices_of, custom_themes

    picks = {**choices_of(as_data(THEMES["glass"])), "accent": "#b9a8ff"}
    params = {"name": "Lavender", "choices": picks, "base": "glass", "use": True}
    assert _describe_save(ctx, params) == "Save the new theme Lavender and use it"
    assert "in use" in _save(ctx, params)
    mine = custom_themes(ctx)
    assert [t["name"] for t in mine] == ["Lavender"] and theme_of(ctx) == mine[0]["id"] == "my_lavender"
    assert for_shell(ctx)["tokens"]["--accent"] == "#b9a8ff" and for_shell(ctx)["material"] == "glass"
    with pytest.raises(ActionError):
        _describe_save(ctx, params)  # the same name again
    assert _describe_save(ctx, {**params, "id": "my_lavender"}).startswith("Update your theme Lavender")
    with pytest.raises(ActionError):
        _describe_save(ctx, {**params, "id": "stark", "name": "Stark"})  # built-ins stay as they are
    with pytest.raises(ActionError):
        _describe_save(ctx, {**params, "name": "Orange", "choices": {**picks, "accent": "#ff8a00"}})
    assert "goes back to Stark" in _describe_delete(ctx, {"id": "my_lavender"})
    assert "Back to Stark" in _delete(ctx, {"id": "my_lavender"}) and theme_of(ctx) == "stark"
    assert "my_lavender" not in all_themes(ctx)
    with pytest.raises(ActionError):
        _describe_delete(ctx, {"id": "y2k"})


def test_your_own_themes_are_in_settings_and_answer_to_their_names(ctx):
    from core.account_actions import _setting
    from core.assistant_accessibility_actions import _action_delete_theme, _action_tweak_theme
    from core.web_account import settings_page

    assert "Purple" not in _action_tweak_theme(ctx, {"accent": "orange"}) and theme_of(ctx) == "stark"
    assert "saved and in use" in _action_tweak_theme(ctx, {"accent": "purple", "material": "glass"})
    assert theme_of(ctx) == "my_stark" and for_shell(ctx)["tokens"]["--accent"] == "#9b6bff"
    assert "saved and in use" in _action_tweak_theme(ctx, {"accent": "pink"})  # theirs in use: updated, not copied
    assert [t["name"] for t in __import__("core.themes", fromlist=["x"]).custom_themes(ctx)] == ["My Stark"]
    groups = {g["title"]: g for g in settings_page(ctx)["groups"]}
    theme_row = next(s for s in groups["Look"]["settings"] if s["key"] == KEY)
    assert {"value": "my_stark", "label": "My Stark"} in theme_row["options"]
    assert _setting(ctx, {"key": KEY, "value": "my_stark"})[1] == "my_stark"
    assert _action_set_theme(ctx, {"theme": "y2k"}) == "Switched to the Y2K Cyber theme."
    assert _action_set_theme(ctx, {"theme": "use my stark"}) == "Switched to the My Stark theme."
    assert "Deleted My Stark" in _action_delete_theme(ctx, {"theme": "my stark"})
    assert "haven't made" in _action_delete_theme(ctx, {"theme": "anything"})


def test_the_studio_screen_lists_every_theme_with_what_it_needs(ctx):
    from core.themes import studio

    page = studio(ctx)
    assert page["current"] == "stark" and [t["id"] for t in page["themes"]] == list(THEMES)
    assert all(t["choices"]["accent"].startswith("#") and not t["own"] for t in page["themes"])
    assert {f["id"] for f in page["fonts"]} >= {"system", "y2k", "technical"} and page["materials"] == list(MATERIALS)
    assert len(page["sample"]) == 5 and page["min_contrast"] == 4.5


def test_a_theme_goes_out_as_a_file_and_comes_back_in_through_the_same_checks(ctx):
    """Export (core/theme_actions.export) and theme.import: a file the Studio exported comes back as one of yours,
    rebuilt from its choices; a file that isn't a MIA theme, or whose accent would read as a warning, is refused."""
    import json
    from pathlib import Path

    from core.actions import ActionError
    from core.theme_actions import FORMAT, _describe_import, _import, export
    from core.themes import custom_themes

    out = export(as_data(THEMES["glass"]))
    assert out["format"] == FORMAT and out["choices"]["accent"] == "#96d6ff" and out["tokens"]["--radius"] == "18px"
    studio_file = (Path(__file__).parent / "fixtures" / "rainy-tokyo-night.mia-theme.json").read_text(encoding="utf-8")
    assert _describe_import(ctx, {"file": studio_file, "use": True}) == "Import the theme Rainy Tokyo Night and use it"
    assert "in use" in _import(ctx, {"file": studio_file, "use": True})
    mine = custom_themes(ctx)
    assert [t["name"] for t in mine] == ["Rainy Tokyo Night"] and theme_of(ctx) == mine[0]["id"]
    assert mine[0]["material"] == "wire" and mine[0]["room"]["mist"] == 2.2
    assert _describe_import(ctx, {"file": studio_file}) == "Import the theme Rainy Tokyo Night 2"  # names stay unique
    for bad in ("not json", json.dumps({"name": "x"}), json.dumps({**json.loads(studio_file), "choices": {"accent": "#ff9a00"}}),
                "x" * 30_000):
        with pytest.raises(ActionError):
            _describe_import(ctx, {"file": bad})
    sneaky = {**json.loads(studio_file), "name": "Sneaky", "choices": None,
              "tokens": {"--attention": "#00ff00", "--accent": "#3f7bff", "--bg": "#000; } body {"}}
    _import(ctx, {"file": json.dumps(sneaky)})
    kept = next(t for t in custom_themes(ctx) if t["name"] == "Sneaky")
    assert "--attention" not in kept["tokens"] and kept["tokens"]["--accent"] == "#3f7bff" and "}" not in kept["tokens"]["--bg"]


def test_mia_designs_a_theme_from_a_description_in_code():
    """core/theme_design.design: places and moods pick the base and the room, colour words the accent; warm accents and
    light themes are explained, not made; every design passes build_theme's checks."""
    from core.theme_design import design, summary
    from core.themes import build_theme

    tokyo = design("a rainy Tokyo night")
    assert tokyo["name"] == "Rainy Tokyo Night" and tokyo["base"] == "cyberpunk" and tokyo["choices"]["mist"] == 2.2
    assert "rainy: rain, heavy mist" in tokyo["understood"] and "Cyberpunk" in summary(tokyo)
    ocean = design("calm ocean glass")
    assert ocean["base"] == "glass" and ocean["choices"]["accent"] == "#2aa8ff" and ocean["choices"]["fire"] == 0.4
    assert design("purple space")["choices"]["accent"] == "#9b6bff"
    sunset = design("an orange sunset")
    assert sunset["choices"]["accent"] == "#ff8ad8" and "warning colour" in sunset["missed"][0]
    assert "dark for now" in design("light mode pastel")["missed"][0]
    assert design("zxqv")["base"] == "stark" and design("zxqv")["missed"]
    for words in ("a rainy Tokyo night", "calm ocean glass", "loud 2000s rave", "cozy forest cabin, rounded",
                  "hacker terminal", "winter snow", "retro arcade", "an orange sunset", "purple space", "zxqv"):
        made = design(words)
        build_theme(made["choices"], as_data(THEMES[made["base"]]), "my_x", made["name"])  # raises if it wouldn't pass


def test_mia_designs_and_puts_on_a_theme_by_voice(ctx):
    from core.assistant_accessibility_actions import _action_design_theme
    from core.themes import custom_themes

    said = _action_design_theme(ctx, {"description": "calm ocean glass"})
    assert said.startswith("I made Calm Ocean Glass") and "undo" in said
    assert theme_of(ctx) == custom_themes(ctx)[0]["id"] and for_shell(ctx)["tokens"]["--accent"] == "#2aa8ff"
    assert "Calm Ocean Glass 2" in _action_design_theme(ctx, {"description": "calm ocean glass"})
    assert "Describe it" in _action_design_theme(ctx, {"description": ""})
