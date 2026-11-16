"""
tests.test_theme_picture
==========================

Appearance phase A7's first part (prompt 24 §9, DEC-0184): a theme from a picture, read in code (core/theme_picture.py),
and the theme in use nudged by plain words (core/theme_design.adjust). The reference picture gives a blue glass close
to Aquatic; a sunset's orange never becomes the accent (it colours the room instead) and says so; a grey picture keeps
Aquatic's accent; a file that isn't a picture, or is too big, is refused with a sentence; every result passes
build_theme's checks. By voice, a painting becomes a theme that's saved and used, and "darker and warmer" changes the
theme in use; the Appearance page offers From a Picture.
"""

import colorsys
import io
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

import core.config_manager as config_module
import core.profile_manager as profile_module
from core import theme_picture, themes
from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.profile_manager import ProfileManager
from core.theme_design import adjust, design

ROOT = Path(__file__).resolve().parent.parent
REFERENCE = ROOT / "docs" / "design" / "reference" / "prompt24_glass_dashboard.jpg"


def _stripes(colours) -> bytes:
    """A PNG of horizontal stripes: [((r, g, b), rows)]."""
    image = Image.new("RGB", (60, sum(rows for _, rows in colours)))
    y = 0
    for rgb, rows in colours:
        image.paste(rgb, (0, y, 60, y + rows))
        y += rows
    out = io.BytesIO()
    image.save(out, "PNG")
    return out.getvalue()


def _hue(colour: str) -> float:
    """A colour's hue in degrees."""
    return colorsys.rgb_to_hls(*(int(colour[i:i + 2], 16) / 255 for i in (1, 3, 5)))[0] * 360


def _light(colour: str) -> float:
    """A colour's lightness, 0 to 1."""
    return colorsys.rgb_to_hls(*(int(colour[i:i + 2], 16) / 255 for i in (1, 3, 5)))[1]


@pytest.fixture
def ctx(tmp_path, monkeypatch):
    """A context with profiles on temporary files and one person signed in."""
    monkeypatch.setattr(config_module, "_CONFIG_FILE", tmp_path / "config.json")
    monkeypatch.setattr(profile_module, "_DATA_PROFILES_DIR", tmp_path / "profiles")
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.profiles = ProfileManager(context)
    context.profiles.create_profile("Robin")
    time.sleep(0.01)
    return context


def test_the_reference_picture_gives_a_blue_glass_theme_that_passes_every_check():
    made = theme_picture.from_image(REFERENCE.read_bytes())
    c = made["choices"]
    assert made["base"] == "aquatic" and c["material"] == "glass"
    assert 195 <= _hue(c["accent"]) <= 235  # the picture's steel blue, close to Aquatic's
    assert _light(c["background"]) < 0.08 and themes.contrast(c["text"], c["panel"]) >= 4.5
    themes.build_theme(c, theme_id="from_picture", name=made["name"])  # raises if it wouldn't pass
    assert theme_picture.from_image(REFERENCE) == made  # the same picture, the same theme, read from a path too


def test_a_meaning_colour_never_becomes_the_accent_and_a_grey_picture_keeps_aquatics():
    sunset = theme_picture.from_image(_stripes([((30, 10, 30), 50), ((255, 120, 20), 30), ((180, 60, 160), 20)]))
    assert themes.accent_problem(sunset["choices"]["accent"]) is None and 280 <= _hue(sunset["choices"]["accent"]) <= 330
    assert any(20 <= _hue(p) <= 45 for p in sunset["choices"]["palette"])  # the orange lights the room instead
    assert "orange" in theme_picture.summary(sunset) and "meaning colour" in sunset["missed"][0]
    grey = theme_picture.from_image(_stripes([((20, 20, 20), 50), ((120, 120, 120), 50)]))
    assert grey["choices"]["accent"] == themes.choices_of(themes.as_data(themes.THEMES["aquatic"]))["accent"]
    assert grey["choices"]["palette"] == [] and "no colour" in grey["missed"][0]
    for made in (sunset, grey):
        themes.build_theme(made["choices"])


def test_a_file_that_isnt_a_picture_or_is_too_big_is_refused_with_a_sentence(monkeypatch):
    for data, said in ((b"", "empty"), (b"not a picture at all", "can't read that")):
        with pytest.raises(ValueError, match=said):
            theme_picture.from_image(data)
    monkeypatch.setattr(theme_picture, "MAX_BYTES", 10)
    with pytest.raises(ValueError, match="too big"):
        theme_picture.from_image(_stripes([((0, 0, 0), 4)]))


def test_plain_words_nudge_a_theme_and_warmth_never_makes_an_amber_accent():
    start = themes.choices_of(themes.as_data(themes.THEMES["aquatic"]))
    darker, done = adjust(start, "a bit darker please")
    assert done == ["a darker field"] and _light(darker["background"]) < _light(start["background"])
    warm, done = adjust(start, "darker and warmer")
    assert len(done) == 2 and themes.accent_problem(warm["accent"]) is None
    assert _hue(warm["accent"]) != _hue(start["accent"])
    for words in ("warmer", "warmer warmer", "cooler", "brighter", "calmer", "more contrast", "lighter"):
        themes.build_theme(adjust(start, words)[0])  # each still passes the checks
    assert adjust(start, "zxqv") == (start, [])


def test_a_soft_gold_is_an_accent_from_a_description_since_dec_0186():
    made = design("elegant gold night")
    assert made["choices"]["accent"] == "#d9b867" and not any("gold" in m for m in made["missed"])
    themes.build_theme(made["choices"])
    assert "warning colour" in design("an orange sunset")["missed"][0]  # vivid orange is still refused


def test_by_voice_a_painting_becomes_a_theme_and_darker_changes_the_one_in_use(ctx, tmp_path):
    from core.assistant_accessibility_actions import _action_adjust_theme, _action_theme_from_picture
    from core.themes import custom_themes, for_shell, theme_of

    picture = tmp_path / "abc123def456.png"
    picture.write_bytes(_stripes([((4, 20, 40), 60), ((20, 120, 200), 25), ((200, 230, 255), 15)]))
    item = {"id": "abc123def456", "description": "a calm ocean at night", "made_at": "2026-11-16"}
    ctx.art = SimpleNamespace(all=lambda: [item], get=lambda i: item if i == item["id"] else None,
                              path=lambda i: picture if i == item["id"] else None)
    said = _action_theme_from_picture(ctx, {"picture": "the ocean one"})
    assert said.startswith("I made A Calm Ocean from the picture") and "undo" in said
    mine = custom_themes(ctx)[0]
    assert theme_of(ctx) == mine["id"] and 195 <= _hue(for_shell(ctx)["tokens"]["--accent"]) <= 235
    assert "Which of your paintings" in _action_theme_from_picture(ctx, {"picture": "castle"})

    before = for_shell(ctx)["tokens"]["--bg"]
    assert "a darker field" in _action_adjust_theme(ctx, {"how": "darker"})
    assert theme_of(ctx) == mine["id"] and len(custom_themes(ctx)) == 1  # their own theme is updated, not copied
    assert _light(for_shell(ctx)["tokens"]["--bg"]) < _light(before)
    assert "How should it change" in _action_adjust_theme(ctx, {"how": "zxqv"})


def test_adjusting_a_built_in_theme_saves_their_own_copy(ctx):
    from core.assistant_accessibility_actions import _action_adjust_theme
    from core.themes import custom_themes, theme_of

    said = _action_adjust_theme(ctx, {"how": "cooler"})
    assert said.startswith("Done: My Aquatic now has a cooler field")
    assert theme_of(ctx) == custom_themes(ctx)[0]["id"]


def test_the_appearance_page_offers_a_theme_from_a_picture():
    studio = (ROOT / "web" / "studio.js").read_text(encoding="utf-8")
    assert "From a Picture" in studio and "MIA.themeFromPicture" in studio and "readAsDataURL" in studio
    assert '"/api/themes/picture"' in (ROOT / "web" / "mia.js").read_text(encoding="utf-8")
    assert '"/api/themes/picture"' in (ROOT / "server" / "app.py").read_text(encoding="utf-8")
