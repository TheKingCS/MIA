"""
gui.presence_widget
======================

PresenceWidget: M.I.A.'s living "core presence" — the visual entity
`docs/VISION.md`'s Home visual-identity section calls for, at the
user's own framing: *"MIA should have an avatar/core presence that
reacts during interactions. When listening, thinking, loading modules,
or completing tasks, the visual system should communicate her state
through motion, lighting, and animation."* Replaces
`gui/character_panel.py`'s static emoji-swap with an always-alive orb
instead of inventing a new animation system from scratch — milestone
2.9's original boot animation (`PulsingCoreWidget`, a timer-driven
breathing glow-orb with layered translucent rings for cheap bloom, no
real blur pass) already proved this rendering technique out; this
generalizes it to be state-driven (color/pulse-speed/an optional
rotating highlight ring) and to render an arbitrary centered glyph
instead of a fixed "M.I.A." label, so each module still keeps its own
icon identity — state communicates *what M.I.A. is doing*, the glyph
still communicates *what you're looking at*. `PulsingCoreWidget` itself
was removed once this widget fully superseded its one caller
(`gui/splash_screen.py`) — no reason to keep two versions of the same
technique around.

Deliberately still 2D/QPainter, no OpenGL/3D — Home has real GPU-class
hardware (`docs/HARDWARE.md`'s Project 2 section), so this isn't a
hardware constraint the way it would be for Core, but restraint is also
just better taste here: a glowing orb that breathes/pulses/rotates
convincingly reads as "alive" without needing a real 3D engine, and
stays cheap regardless of how Home's GPU ends up used elsewhere (LLM
inference, not UI rendering).

**Not yet wired: a genuine "listening" state.** `gui/character_panel.py`'s
sidebar chat is text-only by design (no mic) — voice lives on the full
`modules/assistant/module.py` screen, which doesn't have a presence
widget yet. Flagged in `docs/ROADMAP.md`, not silently skipped.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

# One config per state: base color, how fast the breathing pulse
# cycles, and whether a rotating highlight arc plays on top (reserved
# for states that should read as "actively working," not idle).
_STATE_CONFIG: dict[str, dict] = {
    "idle": {"color": "#4fd1c5", "pulse_step": 0.05, "rotating": False},
    "listening": {"color": "#4fd1c5", "pulse_step": 0.18, "rotating": True},
    "thinking": {"color": "#a78bfa", "pulse_step": 0.14, "rotating": True},
    "loading": {"color": "#e0af68", "pulse_step": 0.12, "rotating": True},
    "notification": {"color": "#e0af68", "pulse_step": 0.35, "rotating": False},
}
_DEFAULT_STATE = "idle"
_LABEL_COLOR = QColor("#0d1116")
_FRAME_INTERVAL_MS = 33  # ~30fps, same as PulsingCoreWidget
_ROTATION_STEP_DEGREES = 3.5
_ARC_SPAN_DEGREES = 50


class PresenceWidget(QWidget):
    """A presence orb sized per caller — small (96px) for
    gui/character_panel.py's sidebar, larger (200px) for
    gui/splash_screen.py's boot moment. See this module's docstring for the
    state model."""

    def __init__(self, parent=None, diameter: int = 96) -> None:
        super().__init__(parent)
        self.setFixedSize(diameter, diameter)
        self._phase = 0.0
        self._rotation = 0.0
        self._state = _DEFAULT_STATE
        self._glyph = ""

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(_FRAME_INTERVAL_MS)

    def set_state(self, state: str) -> None:
        """Switches which motion/color config drives the animation.
        Falls back to "idle" for an unrecognized state rather than
        raising — a typo in a caller's state name should degrade
        gracefully, not crash the presence widget mid-conversation."""
        self._state = state if state in _STATE_CONFIG else _DEFAULT_STATE

    def set_glyph(self, glyph: str) -> None:
        """The icon/emoji rendered centered in the orb — same slot
        PulsingCoreWidget uses for the "M.I.A." boot-screen label, now
        per-caller instead of fixed."""
        self._glyph = glyph
        self.update()

    def stop(self) -> None:
        """Stop the animation timer — call before this widget is discarded."""
        self._timer.stop()

    def _tick(self) -> None:
        config = _STATE_CONFIG[self._state]
        self._phase += config["pulse_step"]
        if config["rotating"]:
            self._rotation = (self._rotation + _ROTATION_STEP_DEGREES) % 360
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt override signature)
        config = _STATE_CONFIG[self._state]
        core_color = QColor(config["color"])

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)

        # Breathing intensity oscillates between 0.8 and 1.0 (not 0-1)
        # so the core never fades out completely — same as
        # PulsingCoreWidget.
        intensity = 0.8 + 0.2 * math.sin(self._phase)

        center = self.rect().center()
        max_radius = min(self.width(), self.height()) / 2 - 2

        for radius_frac, alpha_frac in ((1.0, 0.10), (0.75, 0.20), (0.55, 0.35)):
            color = QColor(core_color)
            color.setAlphaF(alpha_frac * intensity)
            painter.setBrush(color)
            radius = max_radius * radius_frac
            painter.drawEllipse(center, radius, radius)

        solid_color = QColor(core_color)
        solid_color.setAlphaF(0.75 + 0.25 * intensity)
        painter.setBrush(solid_color)
        core_radius = max_radius * (0.32 + 0.03 * intensity)
        painter.drawEllipse(center, core_radius, core_radius)

        if config["rotating"]:
            ring_pen = QPen(core_color, max(2.0, max_radius * 0.07))
            ring_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(ring_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            arc_radius = max_radius * 0.93
            arc_rect = QRectF(
                center.x() - arc_radius, center.y() - arc_radius, arc_radius * 2, arc_radius * 2
            )
            # Qt angles are in 1/16ths of a degree.
            painter.drawArc(arc_rect, int(self._rotation * 16), int(_ARC_SPAN_DEGREES * 16))
            painter.setPen(Qt.PenStyle.NoPen)

        if self._glyph:
            font = QFont()
            # Tuned for two real cases, not a continuous formula: a
            # single emoji glyph (CharacterPanel's module icons) can
            # fill most of the core, but multi-character text (the boot
            # screen's literal "M.I.A." emblem) needs to shrink to still
            # fit inside the circle — 0.32 matches the original
            # PulsingCoreWidget's own tuning for that exact text.
            size_factor = 0.5 if len(self._glyph) <= 2 else 0.32
            font.setPointSizeF(max(1.0, max_radius * size_factor))
            painter.setFont(font)
            text_color = QColor(_LABEL_COLOR)
            text_color.setAlphaF(0.85 + 0.15 * intensity)
            painter.setPen(text_color)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._glyph)

        painter.end()
