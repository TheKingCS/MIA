# Known Issues

Closed items are kept below for history — each links back to its root
cause and fix, in case something similar resurfaces later.

## Open: Diagnostics Level dropdown needs a re-click to select a new value

Symptom: in the Diagnostics log viewer's Level filter (`QComboBox` in
`modules/diagnostics/module.py`), after selecting a value, the *next*
click on the dropdown to pick a different value doesn't register —
moving the mouse away and clicking again does. This is the first
`QComboBox` this app has ever used, so there's no earlier baseline to
compare against.

Suspected root cause: not application QSS (adding explicit
`QComboBox QAbstractItemView` styling in `gui/styles.py` did not fix
it, and Qt cascades ancestor stylesheets onto a widget regardless of
setting that widget's own stylesheet to `""`, so that avenue is likely
a dead end). More likely a WSL/WSLg popup mouse-grab timing quirk —
this was observed running under WSL2, which is explicitly a dev-only
platform per `README.md`; the real deployment target is a Pi 5 kiosk
session on native Linux, not WSLg's Wayland-to-Windows bridge.

**Not yet confirmed either way.** Re-test on real Pi/native-Linux
hardware before spending more effort chasing an app-level fix — if it
doesn't reproduce there, this was a WSLg artifact all along.

## Closed: Easter egg dialog — button text / clipped name

Root cause: `EasterEggDialog` was the only dialog using
`layout.setAlignment(Qt.AlignmentFlag.AlignCenter)` on its top-level
layout, unlike the working `AddProfileDialog`/`PasswordPromptDialog`.
Fixed by matching their layout pattern (no top-level alignment, each
label centers its own text, spacing via `addStretch()`/`addSpacing()`).
**Confirmed fixed on real hardware.**

## Closed: Kiosk fullscreen not persisting through screen transitions

Root cause: fullscreen was only applied inside `MainWindow`'s own
`showEvent` — every other top-level screen (`LockScreen`,
`ProfileSelectScreen`, `SetupWizard`) called plain `.show()` with no
kiosk awareness. Fixed by centralizing display logic in
`MIAApplication._display(widget)`, the single place that now decides
fullscreen vs. normal show for every screen transition.
**Confirmed fixed on real hardware** (Lock Screen -> Main Window,
tested with kiosk_mode on).

## Closed: Header labels showing a mismatched background "box"

Root cause: the global theme's `QMainWindow, QWidget` selector set a
background color that every `QLabel` inherited, painting its own solid
box that didn't match whatever frame it visually sat on top of. Fixed
by adding `QLabel { background: transparent; }` to the shared theme in
`gui/styles.py`. **Confirmed fixed on real hardware.**
