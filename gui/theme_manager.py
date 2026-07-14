"""
gui.theme_manager
====================

Theme registry and selection — docs/ROADMAP.md milestone 13.2. Nothing
like this existed before this milestone: every dialog/screen hardcoded
`gui.styles.DARK_FIELD_THEME` directly, and `config.gui.theme` sat
unread in `config/default_config.json`.

All four themes below reuse the exact same object-name selectors
`gui/styles.py`'s `DARK_FIELD_THEME` already defined (`#TitleLabel`,
`#SubtitleLabel`, `#ReadoutLabel`, `#ModuleButton`, `#HeaderBar`, etc.)
— only which QSS string gets applied changes; no widget code needs new
object names.

The selected theme is applied exactly once, at the `QApplication`
level, in `core/application.py` (`self.qt_app.setStyleSheet(...)`). Qt's
stylesheet cascade means every widget/dialog inherits it automatically
— this is why individual dialogs must NOT also call their own
`setStyleSheet()` (a widget's own stylesheet call overrides inherited
cascade for itself and its children), which is why the old per-widget
`self.setStyleSheet(DARK_FIELD_THEME)` calls were removed from every
dialog/screen as part of this same milestone.
"""

from __future__ import annotations

from gui.styles import DARK_FIELD_THEME

DEFAULT_THEME_ID = "dark_field"

_LOW_ENERGY_THEME = """
QMainWindow, QWidget {
    background-color: #f2f2f0;
    color: #1a1a1a;
    font-family: "Segoe UI", "DejaVu Sans", sans-serif;
    font-size: 14px;
}

QLabel {
    background: transparent;
}

QLabel#TitleLabel {
    font-size: 24px;
    font-weight: 600;
    color: #1a1a1a;
}

QLabel#SubtitleLabel, QLabel#BootSubtitleLabel {
    font-size: 13px;
    color: #4a4a4a;
}

QLabel#BootStatusLabel, QLabel#ReadoutLabel {
    font-family: "Consolas", "DejaVu Sans Mono", monospace;
    font-size: 15px;
    color: #1a1a1a;
    padding: 8px;
    background-color: #e6e6e2;
    border: 1px solid #b8b8b2;
}

QFrame#HeaderBar {
    background-color: #e6e6e2;
    border-bottom: 1px solid #b8b8b2;
}

QFrame#HeaderBar QPushButton#HeaderButton {
    background-color: transparent;
    border: 1px solid #b8b8b2;
    border-radius: 8px;
    padding: 6px 14px;
    color: #3a3a34;
    font-size: 13px;
}

QFrame#HeaderBar QPushButton#HeaderButton:hover {
    background-color: #dcdcd6;
    border: 1px solid #1a1a1a;
    color: #1a1a1a;
}

QFrame#HeaderBar QPushButton#HeaderButton:pressed {
    background-color: #d8d8d2;
}

QFrame#HeaderBar QPushButton#HeaderButton:disabled {
    color: #a8a8a2;
    border: 1px solid #d0d0ca;
}

QFrame#HeaderBar QPushButton#HeaderButton[hasUnread="true"] {
    border: 1px solid #1a1a1a;
    color: #1a1a1a;
    font-weight: 600;
}

QFrame#CharacterPanel {
    background-color: #e6e6e2;
    border: 1px solid #b8b8b2;
    border-radius: 12px;
}

QLabel#CharacterIcon {
    background-color: #dcdcd6;
    border-radius: 48px;
    font-size: 44px;
}

QLabel#CharacterPlaceholderText {
    color: #4a4a4a;
    font-size: 13px;
}

QPushButton#ModuleButton {
    background-color: #e6e6e2;
    border: 1px solid #b8b8b2;
    text-align: left;
}

QPushButton#ModuleButton:hover {
    border: 1px solid #1a1a1a;
}

QLabel#ModuleButtonIcon {
    background-color: #dcdcd6;
    border-radius: 24px;
    font-size: 22px;
}

QLabel#ModuleButtonName {
    font-size: 15px;
    font-weight: 600;
    color: #1a1a1a;
}

QLabel#ModuleButtonDescription {
    font-size: 12px;
    color: #5a5a54;
}

QPushButton#ModuleButton:pressed {
    background-color: #d8d8d2;
}

QProgressBar {
    background-color: #e6e6e2;
    border: 1px solid #b8b8b2;
    text-align: center;
    color: #1a1a1a;
}

QProgressBar::chunk {
    background-color: #4a4a4a;
}

QStatusBar {
    background-color: #e6e6e2;
    color: #4a4a4a;
}

QWizard {
    background-color: #f2f2f0;
}

QLineEdit, QDateEdit, QTimeEdit, QComboBox {
    background-color: #ffffff;
    border: 1px solid #b8b8b2;
    padding: 6px;
    color: #1a1a1a;
}

QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: 1px solid #b8b8b2;
    color: #1a1a1a;
    selection-background-color: #d8d8d2;
    selection-color: #1a1a1a;
    outline: none;
}

QPlainTextEdit#LogView {
    background-color: #ffffff;
    border: 1px solid #b8b8b2;
    color: #1a1a1a;
    font-family: "Consolas", "DejaVu Sans Mono", monospace;
    font-size: 12px;
}

QCheckBox {
    color: #1a1a1a;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #1a1a1a;
    background-color: #ffffff;
}

QCheckBox::indicator:checked {
    background-color: #1a1a1a;
    border: 1px solid #1a1a1a;
}

QCheckBox::indicator:disabled {
    border: 1px solid #b8b8b2;
    background-color: #e6e6e2;
}

QPlainTextEdit#ChatLog {
    background-color: #ffffff;
    border: 1px solid #b8b8b2;
    padding: 10px;
    color: #1a1a1a;
}
"""

_COLORED_THEME = """
QMainWindow, QWidget {
    background-color: #1b1030;
    color: #f1e9ff;
    font-family: "Segoe UI", "DejaVu Sans", sans-serif;
    font-size: 14px;
}

QLabel {
    background: transparent;
}

QLabel#TitleLabel {
    font-size: 26px;
    font-weight: 600;
    color: #ff6b6b;
    letter-spacing: 2px;
}

QLabel#SubtitleLabel, QLabel#BootSubtitleLabel {
    font-size: 13px;
    color: #c9b8e8;
}

QLabel#BootStatusLabel, QLabel#ReadoutLabel {
    font-family: "Consolas", "DejaVu Sans Mono", monospace;
    font-size: 16px;
    color: #ffd166;
    padding: 10px;
    background-color: #2a1b47;
    border: 1px solid #4a2f78;
    border-radius: 8px;
}

QFrame#HeaderBar {
    background-color: #2a1b47;
    border-bottom: 1px solid #4a2f78;
}

QFrame#HeaderBar QPushButton#HeaderButton {
    background-color: transparent;
    border: 1px solid #4a2f78;
    border-radius: 8px;
    padding: 6px 14px;
    color: #c9b8e8;
    font-size: 13px;
}

QFrame#HeaderBar QPushButton#HeaderButton:hover {
    background-color: #3a2560;
    border: 1px solid #ff6b6b;
    color: #f1e9ff;
}

QFrame#HeaderBar QPushButton#HeaderButton:pressed {
    background-color: #150a26;
}

QFrame#HeaderBar QPushButton#HeaderButton:disabled {
    color: #6a5a88;
    border: 1px solid #3a2864;
}

QFrame#HeaderBar QPushButton#HeaderButton[hasUnread="true"] {
    border: 1px solid #06d6a0;
    color: #06d6a0;
    font-weight: 600;
}

QFrame#CharacterPanel {
    background-color: #2a1b47;
    border: 1px solid #4a2f78;
    border-radius: 12px;
}

QLabel#CharacterIcon {
    background-color: #3a2560;
    border-radius: 48px;
    font-size: 44px;
}

QLabel#CharacterPlaceholderText {
    color: #06d6a0;
    font-size: 13px;
}

QPushButton#ModuleButton {
    background-color: #2a1b47;
    border: 1px solid #4a2f78;
    border-radius: 12px;
    text-align: left;
}

QPushButton#ModuleButton:hover {
    background-color: #3a2560;
    border: 1px solid #ff6b6b;
}

QLabel#ModuleButtonIcon {
    background-color: #3a2560;
    border-radius: 24px;
    font-size: 22px;
}

QLabel#ModuleButtonName {
    font-size: 15px;
    font-weight: 600;
    color: #f1e9ff;
}

QLabel#ModuleButtonDescription {
    font-size: 12px;
    color: #c9b8e8;
}

QPushButton#ModuleButton:pressed {
    background-color: #150a26;
}

QProgressBar {
    background-color: #2a1b47;
    border: 1px solid #4a2f78;
    border-radius: 4px;
    text-align: center;
    color: #f1e9ff;
}

QProgressBar::chunk {
    background-color: #06d6a0;
    border-radius: 4px;
}

QStatusBar {
    background-color: #2a1b47;
    color: #c9b8e8;
}

QWizard {
    background-color: #1b1030;
}

QLineEdit, QDateEdit, QTimeEdit, QComboBox {
    background-color: #2a1b47;
    border: 1px solid #4a2f78;
    border-radius: 4px;
    padding: 6px;
    color: #f1e9ff;
}

QComboBox QAbstractItemView {
    background-color: #2a1b47;
    border: 1px solid #4a2f78;
    color: #f1e9ff;
    selection-background-color: #3a2560;
    selection-color: #ff6b6b;
    outline: none;
}

QPlainTextEdit#LogView {
    background-color: #150a26;
    border: 1px solid #4a2f78;
    border-radius: 6px;
    color: #c9b8e8;
    font-family: "Consolas", "DejaVu Sans Mono", monospace;
    font-size: 12px;
}

QCheckBox {
    color: #f1e9ff;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #ff6b6b;
    border-radius: 3px;
    background-color: #2a1b47;
}

QCheckBox::indicator:checked {
    background-color: #ff6b6b;
    border: 1px solid #ff6b6b;
}

QCheckBox::indicator:disabled {
    border: 1px solid #4a2f78;
    background-color: #1b1030;
}

QPlainTextEdit#ChatLog {
    background-color: #2a1b47;
    border: 1px solid #4a2f78;
    border-radius: 6px;
    padding: 10px;
    color: #f1e9ff;
}
"""

_ANIME_MONOCHROME_THEME = """
QMainWindow, QWidget {
    background-color: #ffffff;
    color: #000000;
    font-family: "Segoe UI", "DejaVu Sans", sans-serif;
    font-size: 14px;
}

QLabel {
    background: transparent;
}

QLabel#TitleLabel {
    font-size: 28px;
    font-weight: 700;
    color: #000000;
    letter-spacing: 3px;
}

QLabel#SubtitleLabel, QLabel#BootSubtitleLabel {
    font-size: 13px;
    color: #444444;
}

QLabel#BootStatusLabel, QLabel#ReadoutLabel {
    font-family: "Consolas", "DejaVu Sans Mono", monospace;
    font-size: 16px;
    color: #ffffff;
    padding: 10px;
    background-color: #000000;
    border: 2px solid #000000;
}

QFrame#HeaderBar {
    background-color: #000000;
    border-bottom: 3px solid #000000;
}

/*
#TitleLabel/#SubtitleLabel default to black text for contrast against
this theme's white body background (used as a module page's own
header, e.g. modules/expeditions/module.py) — but gui/main_window.py
also places both inside #HeaderBar, which is solid black here. Without
this override, black-on-black made the app's own top bar title
unreadable (found by actually rendering this theme and looking, not
just checking stylesheet-string equality).
*/
QFrame#HeaderBar QLabel#TitleLabel,
QFrame#HeaderBar QLabel#SubtitleLabel {
    color: #ffffff;
}

/*
Unlike ModuleButton, HeaderButton has no QLabel children — its label is
the QPushButton's own text — so the black/white hover invert this theme
uses everywhere else is safe here; it's the QLabel-descendant :hover
selector specifically that triggers the rendering bug documented above
on ModuleButton, not a plain QPushButton:hover rule.
*/
QFrame#HeaderBar QPushButton#HeaderButton {
    background-color: transparent;
    border: 2px solid #ffffff;
    padding: 6px 14px;
    color: #ffffff;
    font-size: 13px;
}

QFrame#HeaderBar QPushButton#HeaderButton:hover {
    background-color: #ffffff;
    color: #000000;
}

QFrame#HeaderBar QPushButton#HeaderButton:pressed {
    background-color: #444444;
    color: #ffffff;
}

QFrame#HeaderBar QPushButton#HeaderButton:disabled {
    color: #777777;
    border: 2px solid #555555;
}

QFrame#HeaderBar QPushButton#HeaderButton[hasUnread="true"] {
    border: 2px solid #ffffff;
    font-weight: 700;
}

QFrame#CharacterPanel {
    background-color: #ffffff;
    border: 2px solid #000000;
}

QLabel#CharacterIcon {
    background-color: #f0f0f0;
    border-radius: 48px;
    border: 1px solid #000000;
    font-size: 44px;
}

QLabel#CharacterPlaceholderText {
    color: #000000;
    font-size: 13px;
    font-weight: 600;
}

QPushButton#ModuleButton {
    background-color: #ffffff;
    border: 2px solid #000000;
    text-align: left;
}

/*
Deliberately a light-gray highlight, not this theme's usual "invert to
solid black" treatment other elements use — a solid-black hover
background here would need the name/description QLabel children (now
separate widgets, not the button's own text — see gui/widgets/module_button.py's
2026-07-14 redesign) to flip to white via a
"QPushButton:hover QLabel {...}" descendant selector, which is a real,
reproducible Qt/PySide6 rendering bug: that specific selector pattern
(a :hover compound selector targeting a DESCENDANT widget, not the
button itself) made the label text vanish even in the *non*-hover
state, confirmed in an isolated, freshly-started process (not just an
artifact of this project's usual offscreen-Qt dev sandbox — re-verify
on real display hardware before ever reintroducing this pattern). A
lighter background avoids the whole bug class rather than working
around it.
*/
QPushButton#ModuleButton:hover {
    background-color: #f0f0f0;
    border: 2px solid #000000;
}

QLabel#ModuleButtonIcon {
    background-color: #f0f0f0;
    border-radius: 24px;
    border: 1px solid #000000;
    font-size: 22px;
}

QLabel#ModuleButtonName {
    font-size: 15px;
    font-weight: 700;
    color: #000000;
}

QLabel#ModuleButtonDescription {
    font-size: 12px;
    color: #444444;
}

QPushButton#ModuleButton:pressed {
    background-color: #444444;
    color: #ffffff;
}

QProgressBar {
    background-color: #ffffff;
    border: 2px solid #000000;
    text-align: center;
    color: #000000;
}

QProgressBar::chunk {
    background-color: #000000;
}

QStatusBar {
    background-color: #000000;
    color: #ffffff;
}

QWizard {
    background-color: #ffffff;
}

QLineEdit, QDateEdit, QTimeEdit, QComboBox {
    background-color: #ffffff;
    border: 2px solid #000000;
    padding: 6px;
    color: #000000;
}

QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: 2px solid #000000;
    color: #000000;
    selection-background-color: #000000;
    selection-color: #ffffff;
    outline: none;
}

QPlainTextEdit#LogView {
    background-color: #000000;
    border: 2px solid #000000;
    color: #ffffff;
    font-family: "Consolas", "DejaVu Sans Mono", monospace;
    font-size: 12px;
}

QCheckBox {
    color: #000000;
    spacing: 8px;
    font-weight: 600;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 2px solid #000000;
    background-color: #ffffff;
}

QCheckBox::indicator:checked {
    background-color: #000000;
    border: 2px solid #000000;
}

QCheckBox::indicator:disabled {
    border: 2px solid #888888;
    background-color: #ffffff;
}

QPlainTextEdit#ChatLog {
    background-color: #ffffff;
    border: 2px solid #000000;
    padding: 10px;
    color: #000000;
}
"""

#: theme_id -> QSS. Surfaced in modules/settings/module.py's Theme
#: dropdown as: Dark Field / Low Energy / Colored / Anime Monochrome.
THEMES: dict[str, str] = {
    "dark_field": DARK_FIELD_THEME,
    "low_energy": _LOW_ENERGY_THEME,
    "colored": _COLORED_THEME,
    "anime_monochrome": _ANIME_MONOCHROME_THEME,
}

THEME_DISPLAY_NAMES: dict[str, str] = {
    "dark_field": "Dark Field",
    "low_energy": "Low Energy",
    "colored": "Colored",
    "anime_monochrome": "Anime Monochrome",
}


def get_theme_stylesheet(theme_id: str) -> str:
    """Falls back to DEFAULT_THEME_ID for an unrecognized id (e.g. after a config downgrade)."""
    return THEMES.get(theme_id, THEMES[DEFAULT_THEME_ID])
