# Known Issues (open, not yet fixed)

Tracked here so nothing gets lost between sessions.

## 1. Easter egg dialog — button text still not appearing, name still clipped

Reported after the sizing fix in `gui/easter_egg.py` (switched from
`setFixedSize` to `setMinimumWidth` + layout-driven sizing). The fix
was incomplete — the "Nice." button still shows no text, and the
credit line ("Zachary Taylar Rhodes") is still getting cut off at the
bottom of the dialog. Since the sizing fix should have addressed this
in theory but clearly didn't, next session should actually inspect
this on the real machine (screenshot or exact dimensions) rather than
guessing again — likely something more specific than dialog height,
possibly the QVBoxLayout's alignment flag fighting with auto-sizing,
or the multi-line credit label needing explicit wrapping/height.

## 2. Kiosk fullscreen doesn't persist through the lock screen -> main window transition

If fullscreen (kiosk_mode) is active on the lock screen, signing in
drops back to a normal window instead of staying fullscreen. Root
cause: `MainWindow`'s fullscreen behavior is applied in its own
`showEvent()` (see `gui/main_window.py`), but `LockScreen` and
`ProfileSelectScreen` don't currently apply the same kiosk fullscreen
behavior themselves — so the transition from lock screen to main
window isn't preserving a "we're in kiosk mode" state consistently.
Fix likely belongs in `core/application.py`: every top-level screen
`MIAApplication` shows (splash, wizard, profile select, lock screen,
main window) should check `kiosk_mode` and go fullscreen the same way,
rather than only `MainWindow` handling it. Worth designing as one
shared helper rather than patching each screen individually.

## Next session — start here
1. Fix #2 first — it's the clearer/simpler root cause of the two.
2. For #1, get a screenshot or exact widget dimensions from the real
   machine before attempting another fix; two guesses in a row missed,
   so verify the actual failure mode this time before patching again.
