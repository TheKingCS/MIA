# Known Issues

## 1. Easter egg dialog — button text / clipped name (fix applied, not yet tested)

**Root cause found by comparison, not guessing:** `EasterEggDialog` was
the only dialog in the project calling `layout.setAlignment(Qt.AlignmentFlag.AlignCenter)`
on its top-level `QVBoxLayout`. `AddProfileDialog` and `PasswordPromptDialog`
don't do this, and both are confirmed working on the real device. The
dialog has been rebuilt to match that proven pattern.

**Status: fix applied, still needs a real-machine test** (Ctrl+Shift+Z
in the running app). Not yet confirmed.

## 2. Kiosk fullscreen not persisting through screen transitions — CONFIRMED FIXED

**Root cause:** fullscreen was only ever applied inside `MainWindow`'s
own `showEvent`. Every other top-level screen (`LockScreen`,
`ProfileSelectScreen`, `SetupWizard`) called plain `.show()` with no
kiosk awareness.

**Fix:** centralized in `MIAApplication._display(widget)` — the one
place that now decides fullscreen vs. normal show for every screen
transition.

**Status: confirmed working on real hardware** — tested Lock Screen ->
Main Window transition with kiosk_mode on; fullscreen persisted
correctly through the whole flow.

## 3. Header labels showing a mismatched background "box" — FIXED, pending confirmation

**Reported:** the "M.I.A." title and "Welcome back, `<name>`" greeting
in the header appeared to have an out-of-place box/background behind
the text.

**Root cause:** `gui/styles.py`'s global theme sets a background color
on the broad selector `QMainWindow, QWidget` — and `QLabel` is a
`QWidget`, so every label was painting its own solid background box,
which didn't quite match whatever frame it visually sat on top of
(e.g. the header bar's slightly different background color). This same
issue was already worked around locally inside `gui/notification_toast.py`
(which explicitly sets `QLabel { background: transparent; }`) but that
fix was never applied globally.

**Fix:** added `QLabel { background: transparent; }` to the shared
theme in `gui/styles.py`, so this is fixed everywhere at once — header,
lock screen, profile selector, easter egg, notification center, etc. —
rather than needing a per-widget workaround each time it shows up.

**Status: fix applied, needs visual confirmation on real hardware.**
