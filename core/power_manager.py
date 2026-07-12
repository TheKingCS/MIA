"""
core.power_manager
====================

Power monitoring — docs/ROADMAP.md milestone 7.2. Defines a small
backend-agnostic interface (`PowerBackend`, same shape as
core/llm_manager.py's `LLMBackend` and core/voice_manager.py's
`STTBackend`/`TTSBackend`), with one concrete implementation,
`PsutilBatteryBackend`, using psutil's cross-platform OS battery
reporting (percent/plugged-in/time-remaining) — the generic
software-level backend available today on any laptop/dev machine.

The real UPS HAT's voltage/current telemetry is explicitly NOT this
backend's job: docs/HARDWARE.md's "Open questions" section still lists
"Battery/UPS HAT choice" as unpicked, needing "a documented I2C
interface" once chosen. A bare Pi 5 with no UPS HAT installed reports
no battery at all via psutil (`sensors_battery()` returns `None`) —
the expected common case for the actual kiosk deployment until that
hardware decision is made and given its own backend here, same
"engine/software decided now, exact part later" split as
core/voice_manager.py's STT/TTS engine choice.

`PowerManager.check_low_battery()` is the periodic-alert half of this
milestone — `core/application.py` calls it on a timer, same shape as
`AlarmManager.check_due()`. The actual "should this warn" decision is
the pure `should_warn_low_battery()` function so it's unit-testable
with a constructed `PowerStatus`, no real battery or waiting required
— same reasoning as `AlarmManager.check_due()` taking `now` as a
parameter instead of calling `datetime.now()` itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol

import psutil

from core.app_context import AppContext
from core.logger import get_logger

log = get_logger(__name__)

_DEFAULT_LOW_BATTERY_THRESHOLD_PERCENT = 20.0


class PowerUnavailableError(RuntimeError):
    """Raised by a backend when no battery/UPS is detected or a read otherwise fails."""


@dataclass
class PowerStatus:
    percent: float
    plugged_in: bool
    seconds_left: Optional[int]  # None if unknown or "unlimited" (typically means plugged in)


class PowerBackend(Protocol):
    def read(self) -> PowerStatus:
        """Return the current power status, or raise PowerUnavailableError."""
        ...


class PsutilBatteryBackend:
    """PowerBackend implementation using psutil's cross-platform OS battery reporting."""

    def read(self) -> PowerStatus:
        battery = psutil.sensors_battery()
        if battery is None:
            raise PowerUnavailableError("No battery or UPS detected by the OS.")

        seconds_left = battery.secsleft
        if seconds_left in (psutil.POWER_TIME_UNLIMITED, psutil.POWER_TIME_UNKNOWN):
            seconds_left = None

        return PowerStatus(
            percent=battery.percent,
            plugged_in=bool(battery.power_plugged),
            seconds_left=seconds_left,
        )


def should_warn_low_battery(status: PowerStatus, threshold_percent: float, already_warned: bool) -> bool:
    """
    Pure decision logic — testable without touching psutil or real
    time. Warns once per dip below `threshold_percent` while unplugged
    (not every poll), same "don't re-fire every poll within the same
    condition" shape as AlarmManager.check_due()'s last_triggered
    bookkeeping — `already_warned` is the caller's memory of whether
    it's already fired for the current dip.
    """
    if status.plugged_in:
        return False
    if status.percent > threshold_percent:
        return False
    return not already_warned


class PowerManager:
    """
    Core-level Power service (`AppContext.power`). Config-driven via
    `power.low_battery_threshold_percent`. Every public method here
    catches its backend's failure mode and returns None/False (logged)
    rather than raising, so no battery/UPS present never crashes a
    caller — same degrade-gracefully pattern as core/llm_manager.py.
    """

    def __init__(self, context: AppContext) -> None:
        self.context = context
        self._backend: PowerBackend = PsutilBatteryBackend()
        self._threshold_percent = float(
            context.config.get("power.low_battery_threshold_percent", _DEFAULT_LOW_BATTERY_THRESHOLD_PERCENT)
        )
        self._already_warned = False

    def is_available(self) -> bool:
        try:
            self._backend.read()
        except PowerUnavailableError:
            return False
        return True

    def read(self) -> Optional[PowerStatus]:
        try:
            return self._backend.read()
        except PowerUnavailableError as exc:
            log.debug("Power status unavailable: %s", exc)
            return None

    def check_low_battery(self) -> None:
        """
        Called periodically (see core/application.py's power-check
        timer). Raises a real notification via context.notifications
        the first time the battery dips below threshold while
        unplugged, and resets so a future dip can warn again once the
        battery has recovered above threshold or is plugged in.
        """
        status = self.read()
        if status is None:
            return

        if should_warn_low_battery(status, self._threshold_percent, self._already_warned):
            self._already_warned = True
            if self.context.notifications is not None:
                self.context.notifications.notify(
                    title="Low battery",
                    message=f"Battery at {status.percent:.0f}% — plug in soon.",
                    level="warning",
                    source="power",
                )
            log.warning("Low battery: %.0f%% and unplugged.", status.percent)
        elif status.plugged_in or status.percent > self._threshold_percent:
            self._already_warned = False
