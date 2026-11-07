"""
core.startup_sounds
=====================

The startup sounds' names and which one is chosen (Zac, 2026-11-07: "sample
some sounds and I will pick a good start up sound, and make it a togglable
setting"). Kept apart from core/boot_sound.py, which makes the sounds with
numpy, so Settings can list them anywhere MIA runs (the phone too).

`sound.startup` in the device's config: one of STARTUP_SOUNDS, or "off".
It belongs to the computer, not a person: it plays before anyone signs in.
"""

from __future__ import annotations

STARTUP_SOUNDS = {  # id -> the name in Settings
    "warm_chord": "Warm chord",
    "rising_chimes": "Rising chimes",
    "reactor": "Reactor power-up",
    "soft_swell": "Soft swell",
    "ready_tone": "Ready tone",
    "power_up": "The original (sweep and ping)",
}
DEFAULT_STARTUP = "power_up"
OFF = "off"


def options() -> tuple:
    """Pure logic. The Settings choices: each sound, then Off."""
    return tuple(STARTUP_SOUNDS.items()) + ((OFF, "Off (no sound)"),)


def startup_choice(config) -> str:
    """The sound chosen to play at startup ("off" for none): sound.startup in the device's config, else the
    original."""
    chosen = config.get("sound.startup", DEFAULT_STARTUP) if config is not None else DEFAULT_STARTUP
    return chosen if chosen == OFF or chosen in STARTUP_SOUNDS else DEFAULT_STARTUP
