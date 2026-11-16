"""
tests.test_appearance
=======================

The glass design system's foundation (prompt 24 phase A2, DEC-0183, DEC-0184; web/tokens.css, web/themes.css,
core/themes.py, tools/css_colours.py): the five surface tiers exist as tokens with defaults inside their ranges; the
glass material draws every tier from its tokens; a theme can set a tier only within its range, so a dialog can't be made
see-through; status chips keep their meaning colours under glass; the OS's reduced transparency makes glass solid; and
no style sheet gains hard-coded colours.
"""

import re
from pathlib import Path

from core import themes
from tools import css_colours

WEB = Path(__file__).resolve().parent.parent / "web"
TIERS = ("primary", "secondary", "floating", "deep", "interactive")
PARTS = ("alpha", "tint", "blur", "border", "light", "shadow")


def _defaults() -> dict:
    """The tier tokens' default values in web/tokens.css."""
    text = (WEB / "tokens.css").read_text(encoding="utf-8")
    return dict(re.findall(r"(--surface-[a-z]+-[a-z]+):\s*([0-9.]+(?:px)?);", text))


def test_every_tier_has_all_its_tokens_with_defaults_inside_their_ranges():
    found = _defaults()
    for tier in TIERS:
        for part in PARTS:
            key = f"--surface-{tier}-{part}"
            assert key in found, key
            assert themes.clamp_tier(key, found[key]) == found[key].removesuffix("px") + ("px" if part == "blur" else "") \
                or float(themes.clamp_tier(key, found[key]).removesuffix("px")) == float(found[key].removesuffix("px")), key
            assert key in themes.TOKENS


def test_the_glass_material_draws_every_tier_from_its_tokens():
    css = (WEB / "themes.css").read_text(encoding="utf-8")
    for tier in TIERS:
        for part in PARTS:
            assert f"var(--surface-{tier}-{part})" in css, (tier, part)
    glass = css[css.index('[data-material="glass"]'):css.index('[data-material="chrome"]')]
    assert css_colours.count(glass) == 0  # nothing hard-coded left in the glass material


def test_a_theme_sets_a_tier_only_within_its_range():
    tokens = themes.clean_theme({"id": "t", "name": "T", "tokens": {
        "--surface-floating-alpha": "0.2", "--surface-primary-blur": "90px", "--surface-deep-shadow": "nope",
        "--surface-secondary-tint": "0.05", "--chart-2": "#3f79e5"}})["tokens"]
    assert tokens["--surface-floating-alpha"] == "0.8"  # what he must read now is never see-through
    assert tokens["--surface-primary-blur"] == "24px"
    assert "--surface-deep-shadow" not in tokens and tokens["--surface-secondary-tint"] == "0.05"
    assert tokens["--chart-2"] == "#3f79e5"


def test_status_chips_keep_their_meaning_colours_and_reduced_transparency_makes_glass_solid():
    css = (WEB / "themes.css").read_text(encoding="utf-8")
    assert ":is(.chip, " not in css and ".chip:not(.chip-ok, .chip-soon, .chip-bad)" in css
    reduced = css[css.index("prefers-reduced-transparency"):]
    assert "background: rgb(var(--rgb-panel))" in reduced and "backdrop-filter: none" in reduced


def test_no_style_sheet_gains_hard_coded_colours(tmp_path):
    assert css_colours.problems() == []
    (tmp_path / "new.css").write_text(".x { color: #ff0000; background: rgba(var(--rgb-panel), 0.5); }", encoding="utf-8")
    (tmp_path / "base.json").write_text("{}", encoding="utf-8")
    assert css_colours.problems(tmp_path, tmp_path / "base.json") == [
        "web/new.css: 1 hard-coded colours, more than its 0; use a token from web/tokens.css"]


# ---------------------------------------------------------------- phase A3: theme, colour scheme, layout


import pytest

from core import appearance


@pytest.fixture
def settings(monkeypatch):
    """The person's settings as a plain dict (core/person_settings stand-in)."""
    from core import person_settings

    kept = {}
    monkeypatch.setattr(person_settings, "get", lambda context, key, default=None: kept.get(key, default))
    monkeypatch.setattr(person_settings, "put", lambda context, key, value: kept.__setitem__(key, value))
    return kept


def _built_in():
    """Every built-in theme as the page gets it."""
    return {tid: themes.clean_theme(themes.as_data(t)) for tid, t in themes.THEMES.items()}


def test_every_theme_and_scheme_pairing_is_readable_and_no_scheme_takes_a_meaning_colour():
    for tid, theme in _built_in().items():
        assert appearance.readability_problems(theme) == [], tid
        for scheme in appearance.SCHEMES:
            assert appearance.scheme_problem(scheme, theme) == "", (tid, scheme)
    stark = _built_in()["stark"]
    appearance.SCHEMES["gold_test"] = ("Gold", "#e8c27a", "#c99a52", "#f3dcae")
    try:
        assert "amber" in appearance.scheme_problem("gold_test", stark)  # a warm gold reads as "needs you"
    finally:
        del appearance.SCHEMES["gold_test"]
    pale = dict(stark, material="glass", tokens={"--bg": "#e0e0e0", "--rgb-bg": "224, 224, 224", "--text": "#f2f6fa",
                                                  "--rgb-panel": "230, 230, 230", "--surface-primary-alpha": "0.5"})
    found = appearance.readability_problems(pale)  # white text on pale glass: every tier is unreadable
    assert found and all("under 4.5:1" in f for f in found) and any("primary" in f for f in found)


def test_a_scheme_changes_only_the_accents_and_a_layout_only_the_layout(settings):
    glass = _built_in()["glass"]
    violet = appearance.compose(glass, "violet")
    changed = {k for k in violet["tokens"] if violet["tokens"][k] != glass["tokens"].get(k)}
    assert changed and all(k.startswith(("--accent", "--rgb-accent", "--chart-")) for k in changed)
    assert violet["material"] == glass["material"] and violet["scheme"] == "violet" and violet["room"]["accent"] == "#a48bff"
    assert appearance.compose(glass, "theme")["tokens"] == glass["tokens"]
    settings[themes.KEY] = "glass"
    before = appearance.for_shell(None)
    appearance.set_layout(None, density="compact", sidebar="icons")
    after = appearance.for_shell(None)
    assert after["layout"] == {"density": "compact", "sidebar": "icons"} and after["tokens"] == before["tokens"]
    appearance.set_scheme(None, "rose")
    assert appearance.for_shell(None)["layout"] == after["layout"]  # colours never move his workspace
    with pytest.raises(ValueError):
        appearance.set_layout(None, sidebar="hidden")  # not until navigation has another home on the PC


def test_the_look_matches_its_published_schema(settings):
    from core import schema_check

    settings[themes.KEY] = "stark"
    settings[appearance.SCHEME_KEY] = "champagne"
    settings[appearance.EFFECTS_KEY] = "light"
    look = appearance.for_shell(None)
    assert schema_check.errors(look, schema_check.load("appearance.schema.json")) == []
    assert look["scheme"] == "champagne" and look["effects"] == "light" and look["reduce_transparency"] is False
    settings[appearance.SCHEME_KEY] = "nonsense"
    assert appearance.for_shell(None)["scheme"] == "theme"


def test_the_voice_tools_set_colours_layout_and_glass_on_their_own(settings):
    from core.assistant_accessibility_actions import _action_set_layout, _action_set_scheme

    assert "Violet" in _action_set_scheme(None, {"scheme": "make the colours violet"})
    assert settings[appearance.SCHEME_KEY] == "violet"
    assert "theme's own" in _action_set_scheme(None, {"scheme": "theme"})
    said = _action_set_layout(None, {"density": "compact", "effects": "none"})
    assert "compact" in said and settings[appearance.EFFECTS_KEY] == "none"
    assert "one of" in _action_set_layout(None, {"effects": "sparkly"})


def test_the_page_sets_layout_and_effects_and_the_sheets_read_them():
    shell = (WEB / "shell.js").read_text(encoding="utf-8")
    assert all(f"root.dataset.{k}" in shell for k in ("density", "sidebar", "effects", "transparency"))
    css = (WEB / "themes.css").read_text(encoding="utf-8") + (WEB / "shell.css").read_text(encoding="utf-8")
    for attr in ('[data-density="compact"]', '[data-sidebar="icons"]', '[data-effects="light"]', '[data-transparency="reduced"]'):
        assert attr in css, attr
    assert ".layout:has(.home-mia)" in css.split('[data-sidebar="icons"]', 1)[1]  # Home keeps its Talk column
