"""
gui.splash_screen
==================

The boot splash shown while core.application.MIAApplication runs
through its boot sequence — the "M.I.A. waking up" animation
`docs/VISION.md`'s Home visual-identity section calls for (a real boot
sequence should feel like "powering on a futuristic device," not a
static progress bar), building on milestone 2.9's original "Jarvis-
style" pass.

**2026-07-15 rewrite**: three real changes, not just a re-skin.
1. `gui/presence_widget.py`'s `PresenceWidget` (state-driven, built for
   `gui/character_panel.py`) replaces the old fixed `PulsingCoreWidget`
   (milestone 2.9's original boot orb, now removed — this widget fully
   superseded its one caller) — boot now shows the `loading` state
   (amber, rotating ring) throughout, then flips to `idle` (calm teal
   breathing) the moment boot actually finishes, a visible "she's awake
   now" beat instead of just closing the window.
2. `set_status()` (replace the one line) is gone — `add_log_line()`
   *appends* instead, so boot reads as a real accumulating system log
   (closer to a sci-fi terminal boot sequence) rather than one line
   being silently swapped underneath the user.
3. `show_modules()` reveals a row of small icon badges — one per
   *actually discovered* module (`core/module_manager.py`'s real
   `ModuleBase.icon`/`display_name`, not placeholder art) — the literal
   "modules come online" moment from the design brief, faded in with
   one simple `QGraphicsOpacityEffect` animation rather than a
   staggered per-icon sequence (see `core/application.py`'s boot-step
   docstring for why: staggering would add real wall-clock boot time
   per module, a batch reveal doesn't).

`core/application.py`'s boot steps now each report something *real*
(Assistant/voice/power availability, actual module count) instead of
cosmetic filler text — see that file for the step definitions.

Still a plain QWidget (not QSplashScreen), same reasoning as before:
full control over layout, easier to keep extending.
"""

from __future__ import annotations

from PySide6.QtCore import QPropertyAnimation, Qt
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from gui.presence_widget import PresenceWidget

_MAX_LOG_LINES = 8


class SplashScreen(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.SplashScreen)
        # A resizable default size, not setFixedSize() — MIAApplication
        # now routes this through _display(), which calls
        # showFullScreen() in kiosk mode. A hard fixed size would cap
        # the window at 480x640 even in fullscreen state, leaving most
        # of the screen blank instead of actually filling it. Taller
        # than the original 480x380/460 — the 2026-07-15 boot rewrite
        # added an accumulating multi-line log and a module-icon row,
        # both of which need real vertical room, not just the single
        # status line the old size was tuned for.
        self.resize(480, 640)
        self._log_lines: list[str] = []
        self._module_row_animation: QPropertyAnimation | None = None
        self._build_ui()
        self._center_on_screen()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 32, 40, 32)
        layout.setSpacing(12)
        layout.addStretch()

        # "M.I.A." itself is rendered inside the presence orb (see
        # gui/presence_widget.py) rather than as a separate label here.
        subtitle = QLabel("Multifunctional Intelligent Assistant")
        subtitle.setObjectName("BootSubtitleLabel")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._core = PresenceWidget(diameter=200)
        self._core.set_glyph("M.I.A.")
        self._core.set_state("loading")

        self._module_row = QWidget()
        self._module_row_layout = QHBoxLayout(self._module_row)
        self._module_row_layout.setContentsMargins(0, 0, 0, 0)
        self._module_row_layout.setSpacing(8)
        self._module_row_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._module_row_opacity = QGraphicsOpacityEffect(self._module_row)
        self._module_row_opacity.setOpacity(0.0)
        self._module_row.setGraphicsEffect(self._module_row_opacity)

        self._log_label = QLabel("")
        self._log_label.setObjectName("BootStatusLabel")
        self._log_label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self._log_label.setWordWrap(True)
        self._log_label.setFixedWidth(400)

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)  # indeterminate — number of boot
        # steps may change over time, so we don't hardcode a step count
        self._progress.setFixedHeight(8)
        self._progress.setFixedWidth(360)  # a full-screen-width bar would look odd
        self._progress.setTextVisible(False)

        layout.addWidget(subtitle)
        layout.addStretch()
        layout.addWidget(self._core, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._module_row, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()
        layout.addWidget(self._log_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._progress, alignment=Qt.AlignmentFlag.AlignCenter)

    def _center_on_screen(self) -> None:
        screen = self.screen()
        if screen is None:
            return
        geometry = screen.availableGeometry()
        x = geometry.center().x() - self.width() // 2
        y = geometry.center().y() - self.height() // 2
        self.move(x, y)

    def add_log_line(self, message: str) -> None:
        """Appends one line to the boot log — see this module's
        docstring for why this replaced the old single-line
        set_status(). Keeps only the most recent _MAX_LOG_LINES so a
        long boot (many modules/steps) doesn't grow the label forever;
        boot is short enough in practice that this cap rarely matters."""
        self._log_lines.append(message)
        self._log_lines = self._log_lines[-_MAX_LOG_LINES:]
        self._log_label.setText("\n".join(self._log_lines))
        # A word-wrapped QLabel's height doesn't reliably grow on its
        # own once its text goes from one line to several after the
        # widget's already been shown — confirmed via a real headless-Qt
        # test (the label reported a single-line-tall size despite
        # holding 5 lines of text). adjustSize() + re-activating the
        # parent layout forces Qt to actually recompute it, same
        # "explicit invalidation" fix gui/home_dashboard.py's widget
        # grid needed earlier this session for an analogous issue.
        self._log_label.adjustSize()
        self.layout().activate()

    def show_modules(self, modules: list) -> None:
        """Reveals one small icon badge per discovered module — `modules`
        is `core/module_manager.py`'s real `ModuleBase` instances, each
        already carrying its own `.icon`/`.display_name`. Faded in with
        a single opacity animation rather than staggered per-icon, see
        this module's docstring for why."""
        while self._module_row_layout.count():
            item = self._module_row_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        for module in modules:
            badge = QLabel(module.icon)
            badge.setObjectName("BootModuleIcon")
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setFixedSize(28, 28)
            badge.setToolTip(module.display_name)
            self._module_row_layout.addWidget(badge)

        # Same reasoning as add_log_line() above — the row widget was
        # empty (a real (0, 0) size) when the top-level layout last
        # measured it at construction; adding children afterward needs
        # an explicit nudge to actually get laid out and shown. Confirmed
        # via a real headless-Qt test that activate() calls alone (on
        # the row's own layout and the outer splash layout, in that
        # order) were NOT enough here the way they were for
        # add_log_line()'s QLabel — this widget also carries a
        # QGraphicsOpacityEffect, and effect-wrapped widgets appear to
        # need an actual event-loop pass before their new geometry is
        # queryable, not just a layout-invalidation call. A single
        # processEvents() forces that pass immediately rather than
        # hoping the next natural event-loop iteration (the following
        # boot step's QTimer.singleShot) happens to arrive in time —
        # this only runs once per boot, not a hot path, so the usual
        # "don't call processEvents() inside application code" caution
        # doesn't really bite here.
        self._module_row_layout.activate()
        self._module_row.adjustSize()
        self.layout().activate()
        QApplication.processEvents()

        self._module_row_animation = QPropertyAnimation(self._module_row_opacity, b"opacity")
        self._module_row_animation.setDuration(500)
        self._module_row_animation.setStartValue(0.0)
        self._module_row_animation.setEndValue(1.0)
        self._module_row_animation.start()

    def set_ready(self) -> None:
        """Called the moment boot actually finishes — flips the
        presence orb from the busy "loading" state to a calm "idle"
        breathing pulse, a visible "she's awake now" beat rather than
        the window just closing on the busy animation mid-motion."""
        self._core.set_state("idle")

    def closeEvent(self, event) -> None:
        self._core.stop()
        super().closeEvent(event)
