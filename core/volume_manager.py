"""
core.volume_manager
======================

System volume control for the Home Dashboard's volume widget
(gui/home_dashboard.py). Same backend-agnostic shape as
core/power_manager.py (`PowerBackend`/`PsutilBatteryBackend`) and
core/llm_manager.py's `LLMBackend`: one `VolumeBackend` Protocol, one
concrete implementation, `AmixerVolumeBackend`, shelling out to ALSA's
`amixer` CLI via `subprocess` — no Python audio binding needed, which
sidesteps the exact `libpulse`/`libportaudio2` "no sudo, can't install
system packages" wall that has blocked Media/Voice in this dev sandbox
(see docs/ROADMAP.md's Media notes). `amixer` ships with `alsa-utils`,
which is present on a standard Raspberry Pi OS image.

**This dev sandbox has no `amixer` binary at all** (confirmed via `which
amixer`, same "confirmed blocked, not just untested" situation as
11.5's nmap/hashcat) — `is_available()` correctly reports `False` here,
and every public method degrades to None/False rather than raising, so
building against a real device's audio stack can't be verified end to
end until this runs on real Pi hardware. Flagged in docs/ROADMAP.md and
docs/KNOWN_ISSUES.md, same treatment as 11.3b/11.6 rather than silently
assumed to work.

`parse_amixer_output()` is a pure function (no subprocess call) so the
volume/mute parsing logic itself is unit-testable against captured
sample `amixer get Master` text, without needing a real `amixer` binary
in the test environment — same reasoning as
`core/power_manager.py`/`core/device_framework.py` separating the pure
parsing/decision logic from the actual I/O.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from typing import Optional, Protocol

from core.app_context import AppContext
from core.logger import get_logger

log = get_logger(__name__)

_MIXER_CONTROL = "Master"
_SUBPROCESS_TIMEOUT_SECONDS = 2.0

# Matches e.g. "Mono: Playback 32768 [50%] [on]" or
# "Front Left: Playback 32768 [50%] [on]" — amixer's per-channel line
# format varies by control/hardware, but the "[NN%]" and "[on|off]"
# tokens are consistent across all of them.
_PERCENT_PATTERN = re.compile(r"\[(\d{1,3})%\]")
_STATE_PATTERN = re.compile(r"\[(on|off)\]")


class VolumeUnavailableError(RuntimeError):
    """Raised by a backend when the system volume can't be read or changed."""


@dataclass
class VolumeStatus:
    percent: int
    muted: bool


class VolumeBackend(Protocol):
    def read(self) -> VolumeStatus:
        """Return the current volume status, or raise VolumeUnavailableError."""
        ...

    def set_volume(self, percent: int) -> None:
        """Set the volume to `percent` (0-100), or raise VolumeUnavailableError."""
        ...

    def toggle_mute(self) -> None:
        """Toggle mute, or raise VolumeUnavailableError."""
        ...


def parse_amixer_output(output: str) -> Optional[VolumeStatus]:
    """
    Pure parsing logic — testable without a real `amixer` binary (see
    module docstring). Returns None if `output` doesn't contain a
    recognizable "[NN%]"/"[on|off]" pair (e.g. a control with no
    playback switch, or unexpected/empty output).
    """
    percent_match = _PERCENT_PATTERN.search(output)
    state_match = _STATE_PATTERN.search(output)
    if percent_match is None or state_match is None:
        return None
    return VolumeStatus(percent=int(percent_match.group(1)), muted=state_match.group(1) == "off")


class AmixerVolumeBackend:
    """VolumeBackend implementation shelling out to ALSA's `amixer` CLI."""

    def read(self) -> VolumeStatus:
        output = self._run("get")
        status = parse_amixer_output(output)
        if status is None:
            raise VolumeUnavailableError(f"Could not parse amixer output for control '{_MIXER_CONTROL}'.")
        return status

    def set_volume(self, percent: int) -> None:
        self._run("set", f"{percent}%")

    def toggle_mute(self) -> None:
        self._run("set", "toggle")

    def _run(self, *args: str) -> str:
        try:
            result = subprocess.run(
                ["amixer", *args, _MIXER_CONTROL],
                capture_output=True,
                text=True,
                timeout=_SUBPROCESS_TIMEOUT_SECONDS,
                check=False,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            raise VolumeUnavailableError(f"amixer is not available: {exc}") from exc
        if result.returncode != 0:
            raise VolumeUnavailableError(f"amixer exited {result.returncode}: {result.stderr.strip()}")
        return result.stdout


class VolumeManager:
    """
    Core-level Volume service (`AppContext.volume`). Every public method
    catches its backend's failure mode and returns None/False (logged at
    debug level, not warning — the expected common case in this dev
    sandbox and on any non-Pi desktop is "no amixer," not an error)
    rather than raising, same degrade-gracefully pattern as
    core/power_manager.py's PowerManager.
    """

    def __init__(self, context: AppContext) -> None:
        self.context = context
        self._backend: VolumeBackend = AmixerVolumeBackend()

    def is_available(self) -> bool:
        try:
            self._backend.read()
        except VolumeUnavailableError:
            return False
        return True

    def read(self) -> Optional[VolumeStatus]:
        try:
            return self._backend.read()
        except VolumeUnavailableError as exc:
            log.debug("Volume status unavailable: %s", exc)
            return None

    def set_volume(self, percent: int) -> bool:
        percent = max(0, min(100, percent))
        try:
            self._backend.set_volume(percent)
        except VolumeUnavailableError as exc:
            log.debug("Could not set volume: %s", exc)
            return False
        return True

    def toggle_mute(self) -> bool:
        try:
            self._backend.toggle_mute()
        except VolumeUnavailableError as exc:
            log.debug("Could not toggle mute: %s", exc)
            return False
        return True
