"""
gui.styles
==========

Centralized QSS (Qt Style Sheet) theme.

All widgets should pull their look from here rather than setting inline
styles, so the whole application's appearance can be changed (or
swapped for a "theme" config option, per config/default_config.json's
"gui.theme" key) from one place.

**2026-07-16: "Inter"/"JetBrains Mono" font-family names** — the
"ForMIA" design handoff's actual specified typography, not the
"Segoe UI"/"Consolas" system-font fallback this theme originally
shipped with (a real, visible fidelity gap from the reference design,
found while re-comparing against it). Both are bundled in
`assets/fonts/` and registered by `core/application.py`'s
`_load_bundled_fonts()` before this stylesheet is ever applied — see
that function's docstring and `assets/fonts/NOTICE.md` for why they're
bundled rather than assumed installed. The system-font names stay as a
fallback in each `font-family` list, so a font-file load failure still
degrades to something legible rather than a Qt warning-only blank
default. Scoped to this theme only (`dark_field`, the one the ForMIA
handoff is restyling) — the other 3 themes in `gui/theme_manager.py`
keep their original system fonts, unchanged.
"""

DARK_FIELD_THEME = """
QMainWindow, QWidget {
    background-color: #0a0e15;
    color: #e7ecf3;
    font-family: "Inter", "Segoe UI", "DejaVu Sans", sans-serif;
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

/* Settings module's category headers ("Account", "Appearance & Device
Profile", "Voice", "Backup & Restore", "Update Manager") — previously
an inline setStyleSheet("font-weight: 600") with no font-size at all
(just the base 14px), too subtle to read as real section breaks in a
page with 5 of them stacked. */
QLabel#SettingsSectionHeader {
    font-size: 17px;
    font-weight: 700;
    color: #e7ecf3;
    margin-top: 18px;
}

QLabel#BootSubtitleLabel {
    font-size: 20px;
    letter-spacing: 1px;
    color: #7a8a99;
}

QLabel#BootStatusLabel {
    font-family: "JetBrains Mono", "Consolas", "DejaVu Sans Mono", monospace;
    font-size: 16px;
    letter-spacing: 2px;
    color: #4fd1c5;
}

QLabel#ReadoutLabel {
    font-family: "JetBrains Mono", "Consolas", "DejaVu Sans Mono", monospace;
    font-size: 16px;
    color: #4fd1c5;
    padding: 10px;
    background-color: #161b22;
    border: 1px solid #232b34;
    border-radius: 6px;
}

QFrame#HeaderBar {
    background-color: #0c1017;
    border-bottom: 1px solid #1b222e;
}

QFrame#HeaderBar QPushButton#HeaderButton {
    background-color: #111722;
    border: 1px solid #1b222e;
    border-radius: 7px;
    padding: 6px 14px;
    color: #e7ecf3;
    font-size: 13px;
}

QFrame#HeaderBar QPushButton#HeaderButton:hover {
    background-color: #1c2530;
    border: 1px solid #38d9c9;
    color: #e7ecf3;
}

QFrame#HeaderBar QPushButton#HeaderButton:pressed {
    background-color: #0d1116;
}

QFrame#HeaderBar QPushButton#HeaderButton:disabled {
    color: #45505a;
    border: 1px solid #1c232b;
}

QFrame#HeaderBar QPushButton#HeaderButton[hasUnread="true"] {
    border: 1px solid #38d9c9;
    color: #38d9c9;
    font-weight: 600;
}

QFrame#CharacterPanel {
    background-color: #0c1017;
    border: 1px solid #1b222e;
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
    font-family: "JetBrains Mono", "Consolas", "DejaVu Sans Mono", monospace;
    font-size: 34px;
    font-weight: 700;
    color: #e7ecf3;
    letter-spacing: 1px;
}

QLabel#DashboardClockDate {
    font-size: 13px;
    color: #7c8798;
}

/* The "SYSTEM OVERVIEW"/"WIDGETS" section overline labels — distinct
from #DashboardSectionTitle's smaller mono card-eyebrow style, per the
ForMIA mockup's own two-tier label hierarchy (a bold section header
above the mono per-card eyebrows). */
QLabel#DashboardOverlineLabel {
    font-size: 13px;
    font-weight: 700;
    color: #7c8798;
    letter-spacing: 0.3px;
}

/* The "● ALL SYSTEMS NOMINAL" status pill next to SYSTEM OVERVIEW —
same ambient-status-text precedent as MainWindow's own status bar
default message ("M.I.A. core online."), not a live health check. */
QLabel#DashboardStatusChip {
    font-family: "JetBrains Mono", "Consolas", "DejaVu Sans Mono", monospace;
    font-size: 11px;
    font-weight: 600;
    color: #38d9c9;
    background-color: #0f1a1c;
    border: 1px solid #1f3538;
    border-radius: 10px;
    padding: 5px 10px;
}

QFrame#DashboardCard {
    background-color: #101722;
    border: 1px solid #1b222e;
    border-radius: 10px;
}

/* 2026-07-16: gui/character_panel.py's sidebar chat bubbles
(gui/widgets/chat_bubble.py), per the ForMIA mockup — replaces the
plain scrolling QPlainTextEdit log the sidebar shipped with. Both
share ChatBubbleText's font/color; only the bubble's own background/
border differs, matching the mockup's exact two-tone scheme. */
QFrame#ChatBubbleUser {
    background-color: #111722;
    border: 1px solid #1b222e;
    border-radius: 8px;
}

QFrame#ChatBubbleAssistant {
    background-color: #0f1a1c;
    border: 1px solid #1f3538;
    border-radius: 8px;
}

QLabel#ChatBubbleText {
    font-size: 12px;
    color: #c3ccd9;
}

QFrame#NotificationCard {
    background-color: #101722;
    border-radius: 6px;
}

QFrame#NotificationCard[level="info"] {
    border-left: 4px solid #38d9c9;
}

QFrame#NotificationCard[level="warning"] {
    border-left: 4px solid #e0af68;
}

QFrame#NotificationCard[level="critical"] {
    border-left: 4px solid #e06666;
}

QLabel#NotificationCardMeta {
    font-size: 11px;
    color: #7c8798;
}

/* 2026-07-15 "ForMIA" design handoff: widget cards no longer show an
icon badge (see gui/home_dashboard.py's _build_widget_header()) — this
selector is kept only for gui/settings_module or any future reuse, not
currently applied to any built widget. */
QLabel#DashboardSectionIcon {
    background-color: transparent;
    border: 2px solid #38d9c9;
    border-radius: 20px;
    font-size: 18px;
}

/* The "eyebrow" label — small uppercase mono-style tag above a card's
value, per the ForMIA widget stencil. QSS has no text-transform, so
gui/home_dashboard.py uppercases the label text itself before setting it. */
QLabel#DashboardSectionTitle {
    font-family: "JetBrains Mono", "Consolas", "DejaVu Sans Mono", monospace;
    font-size: 10px;
    font-weight: 600;
    color: #5b6a80;
    letter-spacing: 1px;
}

QLabel#DashboardSectionBody {
    font-size: 13px;
    color: #7c8798;
}

/* Activity Log's feed line — monospace, per the ForMIA stencil's
"Log / feed" widget variant (distinct from every other widget's
regular Inter-style DashboardSectionBody). */
QLabel#DashboardActivityLogBody {
    font-family: "JetBrains Mono", "Consolas", "DejaVu Sans Mono", monospace;
    font-size: 12px;
    color: #7c8798;
}

QLabel#DashboardBriefingText {
    font-size: 13px;
    font-weight: 400;
    color: #c3ccd9;
}

QPushButton#AppsLaunchButton {
    background-color: #101722;
    border: 1px solid #38d9c9;
    border-radius: 8px;
    padding: 14px;
    color: #38d9c9;
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
    font-family: "JetBrains Mono", "Consolas", "DejaVu Sans Mono", monospace;
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

/* Restyled 2026-07-16 to match the ForMIA mockup's small pill-shaped
"suggested-prompt chip" (was a full-width left-aligned bar before —
gui/character_panel.py now also adds these with AlignLeft so the
layout doesn't stretch them back to full width). */
QPushButton#SuggestionButton {
    background-color: #0f1a1c;
    border: 1px solid #1f3538;
    border-radius: 12px;
    padding: 6px 12px;
    color: #38d9c9;
    font-size: 11px;
    text-align: left;
}

QPushButton#SuggestionButton:hover {
    background-color: #16292c;
    border: 1px solid #5eead4;
    color: #5eead4;
}

QPushButton#SuggestionButton:pressed {
    background-color: #0d1116;
}

/* 2026-07-16: Hold to Talk previously had no styling at all — press/
release was only reflected in the small status label below it, not the
button itself. [recording="true"] is a dynamic property set from
modules/assistant/module.py's _set_talk_button_recording(), same
pattern as QPushButton#HeaderButton[hasUnread]'s notification-bell
accent above — solid red is the universal "actively recording"
convention (reusing this theme's existing #e06666 critical-notification
red rather than inventing a new color), unmistakably different from the
idle teal-outline look. */
QPushButton#TalkButton {
    background-color: #101722;
    border: 1px solid #38d9c9;
    border-radius: 8px;
    padding: 8px 14px;
    color: #38d9c9;
}

QPushButton#TalkButton:hover {
    background-color: #16292c;
}

QPushButton#TalkButton:disabled {
    color: #45505a;
    border: 1px solid #1c232b;
}

QPushButton#TalkButton[recording="true"] {
    background-color: #e06666;
    border: 1px solid #e06666;
    color: #0d1116;
    font-weight: 600;
}
"""
