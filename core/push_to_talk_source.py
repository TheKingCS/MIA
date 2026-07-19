"""
core.push_to_talk_source
==========================

The headless counterpart to `core/push_to_talk_trigger.py` — that
module is a `QObject` (needs Qt signals to marshal a GPIO interrupt
back onto the GUI thread), which `core/voice_loop.py` deliberately
avoids so a Core deployment never needs PySide6/Qt installed at all
(see `core/core_runtime.py`'s docstring). `core/voice_loop.py` runs a
single blocking loop with no GUI thread to marshal onto, so a plain,
Qt-free `wait_for_press()`/`wait_for_release()` pair is all it needs.

Two implementations, same "degrade gracefully, never crash" shape as
`push_to_talk_trigger.py`'s GPIO/on-screen-button split:
- `GpioPushToTalkSource` — a real button via `gpiozero.Button`, for the
  Receiver hardware once it exists.
- `KeyboardPushToTalkSource` — the dev-machine default. A real physical
  button has a clean press/release pair; a terminal has no equivalent
  "key held down" signal without raw-mode terminal hacks that would add
  real risk for a dev-only convenience, so this uses two explicit
  Enter presses (start talking / stop talking) instead — a real,
  honest interaction you can actually drive by hand, not a simulated
  press/release.
"""

from __future__ import annotations

from typing import Optional, Protocol

from core.logger import get_logger

log = get_logger(__name__)


class PushToTalkSource(Protocol):
    def wait_for_press(self) -> None:
        """Blocks until the user signals "start talking"."""

    def wait_for_release(self) -> None:
        """Blocks until the user signals "stop talking"."""


class KeyboardPushToTalkSource:
    """Dev-machine default — see this module's docstring for why Enter/Enter, not hold-to-talk."""

    def wait_for_press(self) -> None:
        input("\nPress Enter, then speak... ")

    def wait_for_release(self) -> None:
        input("Press Enter again to stop recording... ")


class GpioPushToTalkSource:
    """Real push-to-talk button via `gpiozero.Button` on the Receiver's GPIO pin.

    Raises `RuntimeError` at construction if `gpiozero` isn't installed
    or the pin can't be claimed — `core/voice_loop.py`'s caller decides
    whether to fall back to `KeyboardPushToTalkSource` from there, same
    "caller chooses the fallback" shape as everywhere else a real vs.
    dev backend is picked in this codebase.
    """

    def __init__(self, pin: int) -> None:
        try:
            from gpiozero import Button
        except ImportError as exc:
            raise RuntimeError("gpiozero is not installed — no real GPIO button available.") from exc

        try:
            self._button = Button(pin)
        except Exception as exc:
            raise RuntimeError(f"Could not claim push-to-talk GPIO button on pin {pin}: {exc}") from exc

    def wait_for_press(self) -> None:
        self._button.wait_for_press()

    def wait_for_release(self) -> None:
        self._button.wait_for_release()


def build_push_to_talk_source(gpio_pin: Optional[int]) -> PushToTalkSource:
    """Real GPIO button if `gpio_pin` is configured and claimable, else the keyboard fallback."""
    if gpio_pin is not None:
        try:
            source = GpioPushToTalkSource(gpio_pin)
            log.info("Push-to-talk GPIO button wired on pin %s.", gpio_pin)
            return source
        except RuntimeError as exc:
            log.warning("%s Falling back to the keyboard push-to-talk source.", exc)
    return KeyboardPushToTalkSource()
