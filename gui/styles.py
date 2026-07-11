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

QFrame#HeaderBar {
    background-color: #161b22;
    border-bottom: 1px solid #232b34;
}

QFrame#CharacterPanel {
    background-color: #161b22;
    border: 1px dashed #2c3742;
    border-radius: 8px;
}

QLabel#CharacterPlaceholderText {
    color: #4fd1c5;
    font-size: 13px;
}

QPushButton#ModuleButton {
    background-color: #161b22;
    border: 1px solid #232b34;
    border-radius: 10px;
    padding: 18px;
    text-align: left;
    font-size: 15px;
    color: #d8e0e8;
}

QPushButton#ModuleButton:hover {
    background-color: #1c2530;
    border: 1px solid #4fd1c5;
}

QPushButton#ModuleButton:pressed {
    background-color: #0d1116;
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
"""
