"""
gui.splash_screen
==================

The boot splash shown while core.application.MIAApplication runs
through its boot sequence — the "M.I.A. waking up" animation
`docs/VISION.md`'s Home visual-identity section calls for (a real boot
sequence should feel like "powering on a futuristic device," not a
static progress bar), building on milestone 2.9's original "Jarvis-
style" pass.

`gui/presence_widget.py`'s `PresenceWidget` (state-driven, built for
`gui/character_panel.py`) replaces milestone 2.9's original fixed
`PulsingCoreWidget` — same rendering technique, now shared with the
character panel — but boot deliberately keeps it in the plain `idle`
state (calm teal breathing, no rotating ring, no color shift) the whole
way through, matching the original orb's look exactly rather than
introducing a busy/ready distinction.

**2026-07-15 rewrite added a stacking multi-line log, a per-module icon
reveal row, and an amber "loading" orb color — all three reverted
2026-07-16 at the user's explicit request ("made it look worse").**
Boot is back to: one status line that's replaced each step
(`set_status()`), no module icon row, and the orb staying its original
blue-teal throughout. `core/application.py`'s boot steps still each
report something *real* (Assistant/voice/power availability, actual
module count) instead of cosmetic filler text — see that file for the
step definitions.

Still a plain QWidget (not QSplashScreen), same reasoning as before:
full control over layout, easier to keep extending.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QProgressBar, QVBoxLayout, QWidget

from gui.presence_widget import PresenceWidget


class SplashScreen(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.SplashScreen)
        # A resizable default size, not setFixedSize() — MIAApplication
        # now routes this through _display(), which calls
        # showFullScreen() in kiosk mode. A hard fixed size would cap
        # the window at 680x580 even in fullscreen state, leaving most
        # of the screen blank instead of actually filling it. Grown
        # again (560x460 -> 680x580) to fit the bigger 380px orb below —
        # the first size bump (480x380 -> 560x460, orb 200 -> 300) was
        # judged still too small.
        self.resize(680, 580)
        self._build_ui()
        self._center_on_screen()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 32, 40, 32)
        layout.setSpacing(12)

        # No leading addStretch() before the subtitle (there was one) —
        # with equal-weighted stretches on both sides of the orb, the
        # smaller fixed-height content above it (just the subtitle) vs.
        # below it (status label + progress bar) meant the whole group
        # rendered sitting noticeably lower than center. Anchoring the
        # subtitle near the top margin instead and keeping the stretch
        # *below* the orb pulls the whole group upward.
        # "M.I.A." itself is rendered inside the presence orb (see
        # gui/presence_widget.py) rather than as a separate label here.
        subtitle = QLabel("Multifunctional Intelligent Assistant")
        subtitle.setObjectName("BootSubtitleLabel")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._core = PresenceWidget(diameter=380)
        self._core.set_glyph("M.I.A.")
        # Deliberately no set_state() call — PresenceWidget already
        # defaults to "idle" (blue-teal breathing, no rotating ring),
        # matching the original PulsingCoreWidget's look exactly. See
        # this module's docstring for why boot no longer switches to
        # the amber "loading" state.

        self._status_label = QLabel("INITIALIZING CORE SYSTEMS...")
        self._status_label.setObjectName("BootStatusLabel")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)  # indeterminate — number of boot
        # steps may change over time, so we don't hardcode a step count
        self._progress.setFixedHeight(8)
        self._progress.setFixedWidth(360)  # a full-screen-width bar would look odd
        self._progress.setTextVisible(False)

        layout.addWidget(subtitle)
        layout.addSpacing(24)
        layout.addWidget(self._core, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()
        layout.addWidget(self._status_label)
        layout.addWidget(self._progress, alignment=Qt.AlignmentFlag.AlignCenter)

    def _center_on_screen(self) -> None:
        screen = self.screen()
        if screen is None:
            return
        geometry = screen.availableGeometry()
        x = geometry.center().x() - self.width() // 2
        y = geometry.center().y() - self.height() // 2
        self.move(x, y)

    def set_status(self, message: str) -> None:
        """Replaces the one status line — reverted 2026-07-16 back to
        this from the 2026-07-15 rewrite's accumulating add_log_line()."""
        self._status_label.setText(message)

    def closeEvent(self, event) -> None:
        self._core.stop()
        super().closeEvent(event)
