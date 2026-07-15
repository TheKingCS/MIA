# Known Issues

Closed items are kept below for history — each links back to its root
cause and fix, in case something similar resurfaces later.

## Open: Security Toolkit's Wi-Fi analyzer + active tooling blocked on missing system tools (docs/ROADMAP.md milestone 11.5)

`modules/field_kit/module.py`'s Security tab only ships recon tools
that need no external binary: hash identifier, password strength,
subnet calculator, and a pure-Python TCP connect-scan port scanner
(`core/port_scanner.py`). Confirmed **blocked, not just deferred**: none
of `nmap`, `john`, `hashcat`, `scapy` (the Python package), `aircrack-ng`,
or `hydra` are installed in this dev sandbox, and none can be installed
without root (the same "no sudo" wall Ollama's portable-binary install
and Media/Music's missing `libpulse` already hit). This blocks:
- **Wi-Fi/network analyzer** — needs `aircrack-ng`/raw-socket
  packet capture, both root-gated.
- **Active tooling** (hash cracking via John/Hashcat, packet crafting
  via scapy, exploit-framework launching) — needs the actual
  binaries/libraries present to wrap at all; M.I.A.'s own design intent
  here is to be a UI/launcher over already-installed system tools, not
  to reimplement them.

Re-test once M.I.A. actually runs on real Pi 5 + AI HAT+ 2 hardware (or
any environment with these tools installed and root available) —
nothing about the *design* is blocked, only this dev sandbox's ability
to verify it.

## Open: Calendar has no recurring-event support, so "anniversaries" don't repeat automatically (2026-07-14 aesthetic pass part 5)

The daily occasion-check timer (`core/application.py`'s
`_check_daily_occasions()`) surfaces today's Calendar events as part of
"remind them of anniversaries" — but `core/calendar_manager.py`'s
`CalendarEvent` has no recurrence field at all. A user-created "Our
Anniversary" event only fires this reminder on the exact date it was
entered; it will not automatically reappear next year unless the user
(or the Assistant) adds a fresh event for it annually. Real recurring
events (yearly/monthly/weekly) would need a genuine `CalendarEvent`
schema change plus UI for it — not built here, since it's a separate
feature from the daily-digest mechanism itself. Revisit if recurring
reminders turn out to matter enough to justify that change.

## Open: Home dashboard's volume control unverified on real audio hardware (2026-07-14 aesthetic pass part 3)

`core/volume_manager.py` shells out to ALSA's `amixer` CLI (no Python
audio binding, same "avoid the libpulse/libportaudio2 wall" reasoning
as everything else Media/Voice-adjacent in this project). This dev
sandbox has **no `amixer` binary at all** (confirmed via `which
amixer`, same "confirmed blocked, not just untested" situation as the
Security Toolkit entry above) — `VolumeManager.is_available()` correctly
reports `False` here, and `gui/home_dashboard.py`'s volume slider
degrades to disabled + a "Not available on this device" note, which is
as far as this environment can verify the feature. `parse_amixer_output()`'s
text-parsing logic is unit-tested against captured sample output
(`tests/test_volume_manager.py`), but the real `amixer get/set Master`
round-trip against actual audio hardware has never run.

Re-test once M.I.A. runs on real Pi 5 hardware with `alsa-utils`
installed (ships on a standard Raspberry Pi OS image) — nothing about
the design is blocked, only this dev sandbox's ability to verify it.

## Open: AI HAT+ 2 inference path unconfirmed (docs/ROADMAP.md milestone 14)

`core/llm_manager.py` talks to Ollama's standard HTTP API
(`OLLAMA_HOST`, CPU/generic-GPU inference), which is what this dev
sandbox actually runs against (see `docs/HARDWARE.md`). Whether Ollama
can drive the AI HAT+ 2's NPU accelerator directly, needs a different
backend/runtime for that hardware, or needs a HAT-specific model
format, is **genuinely unresolved** — there's no AI HAT+ 2 in this
sandbox to test against, and this shouldn't be guessed at without the
real hardware. Flag this before assuming the Assistant's current LLM
backend will "just work" once M.I.A. actually runs on the Pi 5 + AI
HAT+ 2 — verify on real hardware first, and expect `core/llm_manager.py`
may need a HAT-specific code path if Ollama can't use the accelerator.

## Open: Polling intervals not yet budgeted against real Pi 5 + AI HAT+ 2 power/CPU constraints

Several modules run a widget-owned `QTimer` on a fixed interval
regardless of device profile (`core/device_profile.py`): Field Kit's
device-list refresh (`modules/field_kit/module.py`,
`_DEVICE_REFRESH_MS = 3000`) and the Diagnostics System Health panel
(`modules/diagnostics/module.py`, `_HEALTH_REFRESH_MS = 3000`) both
poll every 3 seconds unconditionally. Whether this is actually a
meaningful power/CPU cost on Pi 5 + AI HAT+ 2 hardware — and whether
it's worth slowing down specifically for the Core profile — is
**not verified**, so intervals haven't been changed: adjusting them
blindly without real hardware to benchmark against would be exactly
the kind of unverified guess this project avoids elsewhere. Revisit
once real Core hardware exists to actually measure against.

## Closed: App hang while copying large content packs into reference_library/

Symptom: during 4.3 manual testing, `python main.py` stopped logging
entirely mid-session (no shutdown, no traceback) while several
multi-gigabyte Kiwix packs (`ifixit_en_all`, `wikibooks_en_all_nopic`,
plus a few `wikipedia_en_*_mini` packs) were still being copied into
`reference_library/` in the background — forcing a terminal restart.

Root cause: `ReferenceLibraryManager.list_packs()` globs every `.zim`
in `reference_library/` and opens any not-yet-cached file via
`Archive()` — and this runs on *every keystroke* in Ctrl+K search
(`modules/knowledge/module.py`'s search provider calls `list_packs()`
per query). A pack still mid-copy is a truncated/growing file on disk;
opening it with libzim can hang rather than raise, and since a failed
open was never cached, a bad file was retried every keystroke, so
typing while a copy was in flight compounded into what looked like a
dead process. `_get_archive()` also only caught `RuntimeError`, so a
corrupt (not just partial) file could raise something else uncaught.

Fixed by adding a quiet-period guard in `_get_archive()` — skip any
`.zim` file modified more recently than `_MIN_QUIET_SECONDS` (5s)
rather than attempting to open it — plus broadening the open's
exception catch to `Exception`, and caching failures keyed by
`(size, mtime)` so a genuinely broken file isn't retried every call
but a since-replaced/since-finished one is. **Not reproduced under a
controlled repro** — root-caused from `logs/mia.log`'s timestamp
against the packs' file mtimes plus code inspection, not an isolated
crash test; covered going forward by
`tests/test_reference_library_manager.py`'s quiet-period and
recovers-once-replaced tests. Re-confirm if a similar hang resurfaces
during real content-pack installs on the Pi.

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
