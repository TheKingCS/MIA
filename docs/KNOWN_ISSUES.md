# Known Issues

Closed items are kept below for history — each links back to its root
cause and fix, in case something similar resurfaces later.

## Open: QComboBox popups don't close/reset properly until the mouse moves

Symptom: any `QComboBox` in the app — first seen in the Diagnostics log
viewer's Level filter (`modules/diagnostics/module.py`), now also
confirmed on all three dropdowns in Unit Converter
(`modules/toolbox/calculators/unit_converter.py`) — leaves its popup
list visually stuck open / doesn't register the next click correctly
after a selection, until the mouse is moved away and back. Since this
reproduces identically across every `QComboBox` this app has, on
different screens, with different item counts and different signal
wiring, it's very unlikely to be something in any one screen's code.

Suspected root cause: not application QSS (adding explicit
`QComboBox QAbstractItemView` styling in `gui/styles.py` did not fix
it, and Qt cascades ancestor stylesheets onto a widget regardless of
setting that widget's own stylesheet to `""`, so that avenue is likely
a dead end). More likely a WSL/WSLg popup mouse-grab timing quirk —
this was observed running under WSL2, which is explicitly a dev-only
platform per `README.md`; the real deployment target is a Pi 5 kiosk
session on native Linux, not WSLg's Wayland-to-Windows bridge. The
fact that it now reproduces identically across multiple independent
screens strengthens this theory rather than pointing at app code.

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
