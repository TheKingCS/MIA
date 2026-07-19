"""
core.receiver_indicators
==========================

The Protocol boundary between `core/voice_loop.py` and the Receiver's
physical feedback hardware (recording LED, e-paper status display,
vibration motor — docs/HARDWARE.md's "Modular Backpack" section).

**Deliberately stubbed to a console/log backend, not real GPIO/e-paper
code, for one concrete reason**: as of this writing, `HARDWARE.md`
itself still lists the Receiver's exact e-paper module, LED, and
vibration-motor parts — and whether it gets its own MCU at all — as
open questions ("Exact e-paper display module, recording LED, and
vibration motor parts for the Receiver — see 'Modular Backpack' above").
Writing real driver code against hardware that hasn't been chosen yet
would be building blind, the same discipline this project applied to
11.3b/11.6/the Core-Home handoff. `ConsoleReceiverIndicators` below is
a real, fully-functional implementation of this Protocol (not a mock) —
it's just implemented with log lines instead of GPIO/SPI calls, so
`core/voice_loop.py` and everything that calls it can be exercised for
real today, on any machine, with a working default. Swap in a
`GpioReceiverIndicators` (or similar) once the Receiver's parts are
actually chosen — nothing else in this codebase needs to change.
"""

from __future__ import annotations

from typing import Protocol

from core.logger import get_logger

log = get_logger(__name__)


class ReceiverIndicators(Protocol):
    """One method per voice-loop state the Receiver's hardware should reflect."""

    def on_idle(self) -> None:
        """Waiting for the push-to-talk button — nothing is happening."""

    def on_listening(self) -> None:
        """Recording the user's speech (button held down)."""

    def on_thinking(self) -> None:
        """Transcript captured, waiting on the Assistant's reply."""

    def on_speaking(self) -> None:
        """Playing back the Assistant's synthesized reply."""

    def on_notify(self, message: str) -> None:
        """A one-off notification unrelated to the current turn (e.g. a fired alarm)."""


class ConsoleReceiverIndicators:
    """Default `ReceiverIndicators` — logs state changes instead of driving real hardware.

    Real, working, and exactly what a dev machine or a Receiver-less
    bring-up (like the still-in-progress Pi5 hardware checkout) should
    use — not a placeholder that needs replacing before anything can be
    verified end-to-end. See this module's docstring for why the real
    GPIO/e-paper backend isn't written yet.
    """

    def on_idle(self) -> None:
        log.info("[receiver] idle — waiting for push-to-talk")

    def on_listening(self) -> None:
        log.info("[receiver] listening…")

    def on_thinking(self) -> None:
        log.info("[receiver] thinking…")

    def on_speaking(self) -> None:
        log.info("[receiver] speaking…")

    def on_notify(self, message: str) -> None:
        log.info("[receiver] notification: %s", message)
