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
