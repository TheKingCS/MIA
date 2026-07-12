"""
core.push_to_talk_trigger
===========================

Unifies the two ways a push-to-talk press can originate — a real GPIO
button interrupt in kiosk deployment, or the on-screen "Hold to Talk"
button in dev (docs/ROADMAP.md milestone 5.3, docs/HARDWARE.md's Voice
interface section) — behind one `pressed`/`released` signal pair, so
modules/assistant/module.py doesn't need to know which one is active.
Same dev/prod split as core/application.py's kiosk_mode handling:
config-driven (`voice.push_to_talk_gpio_pin`), degrading to "not wired
up, use the on-screen button" rather than crashing when `gpiozero` or
real GPIO hardware isn't present (every dev machine, including this
one).

This is a QObject (not a plain callback wrapper) specifically because
gpiozero's `Button.when_pressed`/`when_released` fire on gpiozero's own
polling thread, not the Qt GUI thread — calling straight into GUI code
from there would be a cross-thread Qt violation. Emitting a signal from
a QObject that lives on the GUI thread lets Qt's own auto-queued
connection marshal the call back onto the GUI thread safely; a plain
callable would not.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QObject, Signal

from core.app_context import AppContext
from core.logger import get_logger

log = get_logger(__name__)


class PushToTalkTrigger(QObject):
    """Emits `pressed`/`released` regardless of whether a GPIO button or the on-screen button fired."""

    pressed = Signal()
    released = Signal()

    def __init__(self, context: AppContext, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._button = None

        pin = context.config.get("voice.push_to_talk_gpio_pin", None)
        if pin is None:
            return  # No pin configured — on-screen button only (dev default).

        try:
            from gpiozero import Button
        except ImportError:
            log.info("gpiozero not installed — push-to-talk GPIO button disabled; use the on-screen button instead.")
            return

        try:
            self._button = Button(pin)
            self._button.when_pressed = self.pressed.emit
            self._button.when_released = self.released.emit
            log.info("Push-to-talk GPIO button wired on pin %s.", pin)
        except Exception as exc:
            log.warning("Could not initialize push-to-talk GPIO button on pin %s: %s", pin, exc)
            self._button = None

    @property
    def has_gpio_button(self) -> bool:
        return self._button is not None

    def close(self) -> None:
        if self._button is not None:
            self._button.close()
            self._button = None
