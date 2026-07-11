# Known Issues

## 1. Easter egg dialog — button text / clipped name (fix attempted, needs real-machine confirmation)

**Root cause found this time, not just guessed:** `EasterEggDialog` was
the only dialog in the project calling `layout.setAlignment(Qt.AlignmentFlag.AlignCenter)`
on its top-level `QVBoxLayout`. `AddProfileDialog` and `PasswordPromptDialog`
don't do this, and both are confirmed working on the real device. The
dialog has been rebuilt to match that proven pattern — no top-level
layout alignment, each label centers its own text individually, spacing
via `addStretch()`/`addSpacing()` instead.

**Status: fix applied, not yet confirmed on real hardware** (this
sandbox has no PySide6/display access, so this could only be verified
by code-pattern comparison, not by actually rendering it). If this
still doesn't look right after testing, the next step should be a
screenshot or exact pixel dimensions from the real machine rather than
a third structural guess.

## 2. Kiosk fullscreen not persisting through screen transitions — FIXED

**Root cause:** fullscreen was only ever applied inside `MainWindow`'s
own `showEvent`. Every other top-level screen (`LockScreen`,
`ProfileSelectScreen`, `SetupWizard`) called plain `.show()` with no
kiosk awareness, so fullscreen silently dropped the moment you left
`MainWindow`.

**Fix:** added `MIAApplication._display(widget)` in `core/application.py`
— the single place that now decides fullscreen vs. normal show for
every screen transition in the app. Removed the redundant per-window
logic from `MainWindow` (its `showEvent` override is gone entirely) so
there's exactly one source of truth for kiosk display behavior.

**Status: needs a real-machine kiosk test to confirm**, but this is a
structural fix (all 6 `.show()` call sites for top-level screens now
route through the same helper), not a patch — high confidence this
resolves it.
