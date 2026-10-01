"""
Accessibility (core/accessibility.py, gui/theme_manager.py,
gui/read_aloud.py), 2026-10-01: text size, high contrast, and reading a
screen aloud; each person's own.
"""

import time
from types import SimpleNamespace

import pytest

import core.config_manager as config_module
import core.profile_manager as profile_module
from core import person_settings
from core.accessibility import TEXT_SIZES, look_for, scale_font_sizes, screen_text, text_scale
from core.app_context import AppContext
from core.assistant_accessibility_actions import _action_read_screen, _action_set_high_contrast, _action_set_text_size
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.profile_manager import ProfileManager


@pytest.fixture
def ctx(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module, "_CONFIG_FILE", tmp_path / "config.json")
    monkeypatch.setattr(profile_module, "_DATA_PROFILES_DIR", tmp_path / "profiles")
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.profiles = ProfileManager(context)
    context.profiles.create_profile("Robin")
    time.sleep(0.01)
    context.other = context.profiles.create_profile("Sam", make_active=False)
    return context


@pytest.fixture
def qapp():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def test_scaling_font_sizes():
    qss = "QLabel { font-size: 14px; } QLabel#TitleLabel { font-size: 28px; } X { font-size: 10pt; }"
    assert scale_font_sizes(qss, 1.5) == "QLabel { font-size: 21px; } QLabel#TitleLabel { font-size: 42px; } X { font-size: 15pt; }"
    assert scale_font_sizes(qss, 1.0) is qss
    assert text_scale("huge") == 1.5 and text_scale("nonsense") == 1.0


def test_the_whole_look(qapp):
    from gui.theme_manager import HIGH_CONTRAST_OVERLAY, build_stylesheet, get_theme_stylesheet

    plain = build_stylesheet("dark_field")
    assert plain == get_theme_stylesheet("dark_field")
    contrast = build_stylesheet("dark_field", "larger", True)
    assert contrast.endswith(scale_font_sizes(HIGH_CONTRAST_OVERLAY, 1.15))
    assert "#ffff00" in contrast and contrast != plain


def test_each_persons_own_look(ctx):
    assert look_for(ctx) == ("normal", False)
    person_settings.put(ctx, "display.text_size", "largest")
    person_settings.put(ctx, "display.high_contrast", True)
    assert look_for(ctx) == ("largest", True)
    sam = SimpleNamespace(config=ctx.config, profiles=ctx.profiles, profile_id=ctx.other.profile_id)
    assert look_for(sam) == ("normal", False)


def test_the_app_applies_it_on_change(ctx, qapp):
    from core.application import MIAApplication

    app = SimpleNamespace(context=ctx, config=ctx.config, qt_app=qapp, _base_font=qapp.font())
    person_settings.put(ctx, "display.text_size", "huge")
    person_settings.put(ctx, "display.high_contrast", True)
    MIAApplication._apply_look(app)
    assert "#ffff00" in qapp.styleSheet()
    if app._base_font.pointSizeF() > 0:
        assert abs(qapp.font().pointSizeF() - app._base_font.pointSizeF() * 1.5) < 0.01
    person_settings.put(ctx, "display.text_size", "normal")
    person_settings.put(ctx, "display.high_contrast", False)
    MIAApplication._apply_look(app)
    assert "#ffff00" not in qapp.styleSheet()
    qapp.setFont(app._base_font)
    qapp.setStyleSheet("")


def test_the_assistant_changes_it(ctx):
    changed = []
    ctx.events.subscribe("display.changed", lambda **kw: changed.append(1))
    assert _action_set_text_size(ctx, {"size": "bigger"}) == "Text size is now larger."
    assert _action_set_text_size(ctx, {"size": "huge"}) == "Text size is now huge."
    assert "biggest" in _action_set_text_size(ctx, {"size": "bigger"})
    assert _action_set_text_size(ctx, {"size": "smaller"}) == "Text size is now largest."
    assert "Bigger or smaller" in _action_set_text_size(ctx, {"size": "purple"})
    assert _action_set_high_contrast(ctx, {"on": True}) == "High contrast is on." and look_for(ctx)[1]
    read = []
    ctx.events.subscribe("accessibility.read_screen", lambda **kw: read.append(1))
    _action_read_screen(ctx, {})
    assert read and len(changed) == 4


def test_screen_text_reads_well():
    lines = ["Budget", "", "✚", "Bills", "Bills", "No bills tracked yet — click Add Bill to get started"]
    assert screen_text(lines) == "Budget. Bills. No bills tracked yet , click Add Bill to get started."
    long = screen_text([f"Line number {i} is here." for i in range(200)], limit=100)
    assert len(long) < 160 and long.endswith("That's the start of this screen.")


def test_reading_a_screen(qapp):
    from PySide6.QtWidgets import QLabel, QLineEdit, QListWidget, QVBoxLayout, QWidget

    from gui.read_aloud import ReadAloud, visible_lines

    root = QWidget()
    layout = QVBoxLayout(root)
    layout.addWidget(QLabel("<b>Kitchen</b>"))
    secret = QLineEdit("hunter2")
    secret.setEchoMode(QLineEdit.EchoMode.Password)
    layout.addWidget(secret)
    items = QListWidget()
    items.addItems(["Milk", "Eggs"])
    layout.addWidget(items)
    hidden = QLabel("Not shown")
    hidden.hide()
    layout.addWidget(hidden)
    root.show()
    qapp.processEvents()
    lines = visible_lines(root)
    assert lines == [" Kitchen ", "Milk", "Eggs"] or [l.strip() for l in lines] == ["Kitchen", "Milk", "Eggs"]
    assert "hunter2" not in " ".join(lines)

    spoken = []
    voice = SimpleNamespace(is_tts_available=lambda: True, synthesize=lambda text, path: spoken.append(text),
                            stop_playback=lambda: spoken.append("STOP"))
    reader = ReadAloud(SimpleNamespace(voice=voice))
    assert reader.toggle(root).startswith("Reading this screen")
    reader._worker.wait(5000)
    assert spoken == ["Kitchen. Milk. Eggs."]
    assert reader.toggle(root) == "Stopped reading." and spoken[-1] == "STOP"
    no_voice = ReadAloud(SimpleNamespace(voice=None))
    assert "voice isn't set up" in no_voice.toggle(root)


def test_high_contrast_recolors_the_themes_own_named_parts():
    from gui.theme_manager import THEMES, _contrast_for_named

    qss = """/* a comment { } */ QPushButton#Chip { color: teal; } QPushButton#Chip:hover { color: cyan; }
    QLabel#Clock, QLabel { color: grey; }"""
    out = _contrast_for_named(qss)
    assert "QPushButton#Chip,\nQLabel#Clock { color: #ffffff; background-color: #000000; }" in out
    assert "QPushButton#Chip:hover { color: #000000; background-color: #ffff00; }" in out
    assert "QPushButton#Chip:disabled { color: #9a9a9a" in out and "comment" not in out
    for theme in THEMES.values():  # every theme gets a well-formed overlay
        overlay = _contrast_for_named(theme)
        assert overlay.count("{") == overlay.count("}") and "/*" not in overlay
