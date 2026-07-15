"""
gui.styles
==========

Centralized QSS (Qt Style Sheet) theme.

All widgets should pull their look from here rather than setting inline
styles, so the whole application's appearance can be changed (or
swapped for a "theme" config option, per config/default_config.json's
"gui.theme" key) from one place.
"""

DARK_FIELD_THEME = """
QMainWindow, QWidget {
    background-color: #10141a;
    color: #d8e0e8;
    font-family: "Segoe UI", "DejaVu Sans", sans-serif;
    font-size: 14px;
}

QLabel {
    background: transparent;
}

QLabel#TitleLabel {
    font-size: 26px;
    font-weight: 600;
    color: #4fd1c5;
    letter-spacing: 2px;
}

QLabel#SubtitleLabel {
    font-size: 13px;
    color: #7a8a99;
}

QLabel#BootSubtitleLabel {
    font-size: 20px;
    letter-spacing: 1px;
    color: #7a8a99;
}

QLabel#BootStatusLabel {
    font-family: "Consolas", "DejaVu Sans Mono", monospace;
    font-size: 16px;
    letter-spacing: 2px;
    color: #4fd1c5;
}

QLabel#ReadoutLabel {
    font-family: "Consolas", "DejaVu Sans Mono", monospace;
    font-size: 16px;
    color: #4fd1c5;
    padding: 10px;
    background-color: #161b22;
    border: 1px solid #232b34;
    border-radius: 6px;
}

QFrame#HeaderBar {
    background-color: #161b22;
    border-bottom: 1px solid #232b34;
}

QFrame#HeaderBar QPushButton#HeaderButton {
    background-color: transparent;
    border: 1px solid #232b34;
    border-radius: 8px;
    padding: 6px 14px;
    color: #b8c4cf;
    font-size: 13px;
}

QFrame#HeaderBar QPushButton#HeaderButton:hover {
    background-color: #1c2530;
    border: 1px solid #4fd1c5;
    color: #d8e0e8;
}

QFrame#HeaderBar QPushButton#HeaderButton:pressed {
    background-color: #0d1116;
}

QFrame#HeaderBar QPushButton#HeaderButton:disabled {
    color: #45505a;
    border: 1px solid #1c232b;
}

QFrame#HeaderBar QPushButton#HeaderButton[hasUnread="true"] {
    border: 1px solid #4fd1c5;
    color: #4fd1c5;
    font-weight: 600;
}

QFrame#CharacterPanel {
    background-color: #161b22;
    border: 1px solid #232b34;
    border-radius: 12px;
}

/*
2026-07-14 aesthetic pass part 3 (docs/ROADMAP.md): "bubble outline"
icon look — a colored ring stroke with a transparent center, replacing
the earlier filled-circle badge. Applies to every icon badge in the app
(#CharacterIcon here, #ModuleButtonIcon and #DashboardSectionIcon
below) for one consistent icon language.
*/
QLabel#CharacterIcon {
    background-color: transparent;
    border: 2px solid #4fd1c5;
    border-radius: 48px;
    font-size: 44px;
}

QLabel#CharacterPlaceholderText {
    color: #4fd1c5;
    font-size: 13px;
}

QPushButton#ModuleButton {
    background-color: #161b22;
    border: 1px solid #232b34;
    border-radius: 12px;
    text-align: left;
}

QPushButton#ModuleButton:hover {
    background-color: #1c2530;
    border: 1px solid #4fd1c5;
}

QPushButton#ModuleButton:pressed {
    background-color: #0d1116;
}

QLabel#ModuleButtonIcon {
    background-color: transparent;
    border: 2px solid #4fd1c5;
    border-radius: 24px;
    font-size: 22px;
}

QLabel#ModuleButtonName {
    font-size: 15px;
    font-weight: 600;
    color: #d8e0e8;
}

QLabel#ModuleButtonDescription {
    font-size: 12px;
    color: #7a8a99;
}

QLabel#DashboardClockTime {
    font-size: 34px;
    font-weight: 600;
    color: #d8e0e8;
    letter-spacing: 1px;
}

QLabel#DashboardClockDate {
    font-size: 14px;
    color: #7a8a99;
}

QFrame#DashboardCard {
    background-color: #161b22;
    border: 1px solid #232b34;
    border-radius: 12px;
}

QLabel#DashboardSectionIcon {
    background-color: transparent;
    border: 2px solid #4fd1c5;
    border-radius: 20px;
    font-size: 18px;
}

QLabel#DashboardSectionTitle {
    font-size: 14px;
    font-weight: 600;
    color: #d8e0e8;
}

QLabel#DashboardSectionBody {
    font-size: 13px;
    color: #b8c4cf;
}

QLabel#DashboardBriefingText {
    font-size: 16px;
    font-weight: 500;
    color: #d8e0e8;
}

QPushButton#AppsLaunchButton {
    background-color: #161b22;
    border: 1px solid #4fd1c5;
    border-radius: 10px;
    padding: 14px;
    color: #4fd1c5;
    font-size: 15px;
    font-weight: 600;
}

QPushButton#AppsLaunchButton:hover {
    background-color: #1c2530;
}

QPushButton#AppsLaunchButton:pressed {
    background-color: #0d1116;
}

/*
2026-07-14 aesthetic pass part 5: the Assistant's conversation-history
list (modules/assistant/module.py). Same "no QLabel-descendant :hover
selector" rule as #ModuleButton (gui/widgets/module_button.py's
docstring) — this card's title/meta are QLabel children too, and that
exact selector pattern is a confirmed Qt/PySide6 rendering bug. Hover/
selected only ever change the button's own background/border here.
*/
QPushButton#ConversationCard {
    background-color: #161b22;
    border: 1px solid #232b34;
    border-radius: 8px;
    text-align: left;
}

QPushButton#ConversationCard:hover {
    background-color: #1c2530;
}

QPushButton#ConversationCard[selected="true"] {
    border: 1px solid #4fd1c5;
}

QLabel#ConversationCardTitle {
    font-size: 13px;
    font-weight: 600;
    color: #d8e0e8;
}

QLabel#ConversationCardMeta {
    font-size: 11px;
    color: #7a8a99;
}

/*
QSlider falls back to the native OS/platform look if left unstyled —
same invisible-on-this-background risk this file's own QCheckBox
comment already documents. Used today by the Home dashboard's volume
control (gui/home_dashboard.py).
*/
QSlider::groove:horizontal {
    height: 6px;
    background-color: #232b34;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    width: 16px;
    height: 16px;
    margin: -6px 0;
    background-color: #4fd1c5;
    border-radius: 8px;
}

QSlider::handle:horizontal:disabled {
    background-color: #45505a;
}

QSlider::sub-page:horizontal {
    background-color: #4fd1c5;
    border-radius: 3px;
}

QSlider::sub-page:horizontal:disabled {
    background-color: #2c3742;
}

QProgressBar {
    background-color: #161b22;
    border: 1px solid #232b34;
    border-radius: 4px;
    text-align: center;
    color: #d8e0e8;
}

QProgressBar::chunk {
    background-color: #4fd1c5;
    border-radius: 4px;
}

QStatusBar {
    background-color: #161b22;
    color: #7a8a99;
}

QWizard {
    background-color: #10141a;
}

QLineEdit, QDateEdit, QTimeEdit, QComboBox {
    background-color: #161b22;
    border: 1px solid #232b34;
    border-radius: 4px;
    padding: 6px;
    color: #d8e0e8;
}

/*
QComboBox's popup list is a separate top-level widget (QAbstractItemView)
that does NOT inherit the QComboBox rule above. Left unstyled, it falls
back to a default view that (at least under this custom stylesheet)
doesn't register a click on an item until the mouse first moves —
selecting an item and immediately clicking again elsewhere needs a
mouse-move in between to "wake up" the popup's hit-testing. Styling it
explicitly, including a real selection color, fixes this.
*/
QComboBox QAbstractItemView {
    background-color: #161b22;
    border: 1px solid #232b34;
    color: #d8e0e8;
    selection-background-color: #1c2530;
    selection-color: #4fd1c5;
    outline: none;
}

QPlainTextEdit#LogView {
    background-color: #0d1116;
    border: 1px solid #232b34;
    border-radius: 6px;
    color: #9fb0bf;
    font-family: "Consolas", "DejaVu Sans Mono", monospace;
    font-size: 12px;
}

/*
Unstyled, QCheckBox's indicator box falls back to the native OS/platform
style rather than this theme — under the dark background here, that
rendered as a dark-on-dark box that was effectively invisible (found via
gui/backup_dialog.py's "Encrypt this backup" checkbox, but this affects
every checkbox in the app, including AddProfileDialog's).
*/
QCheckBox {
    color: #d8e0e8;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #4fd1c5;
    border-radius: 3px;
    background-color: #161b22;
}

QCheckBox::indicator:hover {
    border: 1px solid #6fe3d8;
}

QCheckBox::indicator:checked {
    background-color: #4fd1c5;
    border: 1px solid #4fd1c5;
}

QCheckBox::indicator:disabled {
    border: 1px solid #2c3742;
    background-color: #10141a;
}

QPlainTextEdit#ChatLog {
    background-color: #161b22;
    border: 1px solid #232b34;
    border-radius: 6px;
    padding: 10px;
    color: #d8e0e8;
}

QPushButton#SuggestionButton {
    background-color: transparent;
    border: 1px solid #232b34;
    border-radius: 8px;
    padding: 6px 10px;
    color: #b8c4cf;
    font-size: 12px;
    text-align: left;
}

QPushButton#SuggestionButton:hover {
    background-color: #1c2530;
    border: 1px solid #4fd1c5;
    color: #d8e0e8;
}

QPushButton#SuggestionButton:pressed {
    background-color: #0d1116;
}
"""
