# Known Issues

Closed items are kept below for history — each links back to its root
cause and fix, in case something similar resurfaces later.

## Open (fix applied, unconfirmed): real crash using Home/Back navigation buttons

2026-07-18, reported by the user: "I keep crashing when using the home
and back buttons." `logs/mia.log` shows no Python traceback at all —
the log simply stops mid-session (last line: a `home.shown` event
right after Settings was open) — same "no caught exception" signature
as the fullscreen-crash entry below, strongly suggesting the same
underlying class of bug, not a new one.

Best diagnosis possible without a real display to reproduce against:
`gui/main_window.py`'s `_stack` (a `QStackedWidget` holding Home, the
Apps grid, and every opened module's widget) was added directly to the
body layout with no scroll clipping. Switching `currentWidget()` to a
module whose content's minimum size exceeds the window's current
geometry can make Qt's layout engine try to grow the *window* itself
to satisfy that minimum — while already fullscreen (kiosk mode), that
is exactly the same kind of buffer-size-vs-configured-fullscreen-state
mismatch that already killed the Wayland connection once before (see
below). Fixed by wrapping `_stack` in its own `QScrollArea` — any
module's oversized content now scrolls internally instead of ever
pushing a size demand up to the top-level window.

**Not confirmed as the fix** — verified only that navigation still
renders and functions correctly under headless-Qt (a real crash
reproduction needs the actual Wayland display that hit this). Needs
the user to confirm on their real machine before this is closed out.

## Open (fix applied, unconfirmed): Home dashboard widgets sized wrong after visiting the Assistant

2026-07-18, reported by the user: "I keep having a sizing issue with
the dashboard widgets when going from the Assistant to the Home
Screen." A headless-Qt reproduction at a fixed window size (building a
real `MainWindow`, seeding 80 conversation messages so the Assistant's
own chat log genuinely scrolls, then round-tripping Home → Assistant →
Home) did **not** reproduce a static geometry discrepancy — card sizes
measured identical before and after.

Most likely root cause given that: `HomeDashboard._data_timer` (a
5-second `QTimer`) keeps firing on schedule regardless of whether Home
is the currently-visible `QStackedWidget` page — `QStackedWidget` just
hides the widget, it doesn't pause its timers. `_set_widget_body_text()`
(the existing `heightForWidth`/`sizeHint()` fix from an earlier pass)
reads `label.width()` to compute a correct `setMinimumHeight()`; if that
timer tick lands while Home is hidden, or mid-transition right after a
page switch before layout has settled, the width it reads can be stale,
producing a wrong minimum height that then persists — visibly
clipped/oversized card text — until a later tick happens to catch a
good width (up to 5 seconds, or indefinitely if the page stays hidden).

Fix: `HomeDashboard` now overrides `showEvent()` to call
`_refresh_data()` immediately whenever the page becomes visible again,
instead of relying on the next timer tick. Verified via a headless
spy test that this fires exactly once on initial show and once again
on becoming visible after a hide/show round-trip through a
`QStackedWidget`. As a secondary defensive measure,
`gui/main_window.py`'s four page-switch methods (`show_home()`,
`show_main_menu()`, `go_back()`, `_navigate_to()`) now also call
`updateGeometry()` on both the `QStackedWidget` and the `QScrollArea`
wrapping it (added for the Home/Back crash fix above), in case
`setCurrentWidget()` alone doesn't generate a real resize event for the
newly-current page.

**Not confirmed as the fix** — the original bug was never reproduced
in this headless dev sandbox, so this is the most plausible mechanism
found rather than a verified root cause. Needs the user to confirm on
their real machine that the sizing issue no longer recurs.

## Open (fix applied, unconfirmed): real crash — Wayland connection killed going fullscreen

2026-07-17, hit live on the user's real machine right after selecting a
profile (kiosk_mode on): `xdg_wm_base@3: error 4: xdg_surface buffer
(1920 x 1205) is larger than the configured fullscreen state (1920 x
1200)` then `The Wayland connection experienced a fatal error: Protocol
error` — this kills the whole Wayland session, not just M.I.A.

Root cause (best diagnosis possible without a real Wayland display to
reproduce against — this dev sandbox is headless/offscreen-QPA only):
every top-level screen constructs itself at a small fixed windowed size
first (`MainWindow.resize(1100, 700)`, `SplashScreen.resize(720, 640)`,
etc.), then `core/application.py`'s `_display()` immediately calls
`showFullScreen()` on top of that when kiosk_mode is on. That small-
windowed-then-huge-fullscreen jump is a known trigger for a Qt/Wayland
buffer-negotiation race. Fix: `_display()` now explicitly resizes the
widget to the actual screen's geometry *before* requesting fullscreen,
removing the jump. **Not confirmed fixed** — needs the user to relaunch
on the machine that actually hit this and confirm it doesn't recur.

## Open: MIA Home's move onto Windows is unverified beyond a static code audit

Static audit (2026-07-16, ahead of running MIA Home on the real Project
2 Windows machine to connect VMagicMirror) found: every pinned
dependency in `requirements.txt` has a Windows wheel (`PySide6`,
`libzim`, `piper-tts`, `vosk`, `sounddevice`, `psutil`, `cryptography`,
`pyserial`, `astral` — checked directly, not assumed), and every
Linux-only *feature* (Volume's `amixer`, Field Kit's `lsblk`/`udisksctl`)
already degrades gracefully rather than crashing. One real gap was
found and fixed: `core/script_runner.py`'s `terminate_process_tree()`
used POSIX-only `os.killpg()`, uncaught on Windows — now branches to
`taskkill /T /F` there. **None of this has been run against a real
Windows install** — this dev sandbox is Linux/WSL2 only. Re-verify
`pip install -r requirements.txt` + `python main.py` actually boot
clean on Windows, and that a Field Kit script's Stop button genuinely
kills a whole process tree there, before trusting either further than
"the code path is exercised."

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

## Closed: TTS playback unverified on real audio hardware (2026-07-15, spoken startup briefing + selectable voices)

`core/voice_manager.py`'s `PiperBackend.synthesize()` was already
verified real (confirmed producing genuinely different audio for
different selected voices, `core/voice_catalog.py`'s 5-voice catalog).
The playback half (`sounddevice`/PortAudio) took 4 rounds of real
environment debugging to get working under this dev sandbox's WSL2 —
worth recording the full chain since it'll matter again for anyone
setting up a fresh WSL2 dev environment for this project:

1. `libportaudio2` (the system library `sounddevice`'s Linux wheel
   needs but doesn't bundle) was missing entirely — `import sounddevice`
   raised `OSError` outright. Fixed: `sudo apt install libportaudio2`.
2. With that installed, `sd.query_devices()` still returned empty and
   playback failed with "Error querying device -1" — this dev sandbox
   (WSL2) has **no real ALSA hardware card at all** (expected; audio is
   virtualized). `amixer`/`alsa-utils` were also missing, but installing
   just those didn't help either — `amixer: Mixer attach default error`
   confirmed there's no ALSA card for `amixer` to control, a different
   problem than a muted mixer.
3. WSLg actually bridges audio through **PulseAudio**, not raw ALSA
   hardware (`/mnt/wslg/PulseServer` was already running, confirmed via
   `pactl info` once `pulseaudio-utils`/`libpulse0` were installed —
   `Default Sink: RDPSink`, WSLg forwards audio to Windows over RDP).
   But `sounddevice`/PortAudio still saw zero devices even after this —
   Ubuntu's `libportaudio2` package talks to ALSA, not directly to
   Pulse, and nothing was routing ALSA's "default" device to Pulse.
4. Fixed with the standard ALSA→Pulse bridge: installed
   `libasound2-plugins` (provides ALSA's `pulse` PCM type) plus a
   `~/.asoundrc`:
   ```
   pcm.!default { type pulse }
   ctl.!default { type pulse }
   ```
   After this, `sd.query_devices()` showed real `pulse`/`default` ALSA
   devices, and a real `VoiceManager.play()` call through M.I.A.'s own
   code returned `True` with no errors — **and the user confirmed
   actually hearing it** through Windows, the first real, human-confirmed
   audio output this project has had.

**Full chain needed on a fresh WSL2 box**: `libportaudio2` +
`alsa-utils` + `pulseaudio-utils` + `libasound2-plugins` (apt) plus the
`~/.asoundrc` snippet above (not project-tracked — it's a user-home
dotfile, has to be set up per machine). None of this is needed on real
Pi 5 hardware, which has actual ALSA-visible audio hardware and doesn't
route through a Windows/WSLg bridge at all — this whole chain is a
WSL2-dev-environment-specific quirk, not something to replicate in
`deploy/install_kiosk.sh`.

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

## Closed: Home dashboard's volume control unverified on real audio hardware (2026-07-14 aesthetic pass part 3)

`core/volume_manager.py` shells out to ALSA's `amixer` CLI. Resolved as
a direct side effect of the WSL2 audio investigation above (see the
"Closed: TTS playback" entry for the full `libportaudio2`/`alsa-utils`/
`pulseaudio-utils`/`libasound2-plugins`/`~/.asoundrc` chain) — once
ALSA's default device was routed through Pulse, `amixer get Master`
started working against the real (virtual) device too. Confirmed via a
real `VolumeManager` call: `is_available()` now `True`,
`read()` -> `VolumeStatus(percent=100, muted=False)` — the dashboard's
volume slider should now be live and functional in this dev sandbox,
not just on real Pi hardware.

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
