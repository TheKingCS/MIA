#!/usr/bin/env python3
"""
core_main.py
============

Entry point for headless **MIA Core** — the Receiver-driven, voice-first
runtime (docs/VISION.md's 2026-07-15 "Core drops its GUI entirely"
sharpening), separate from `main.py` (which boots the full MIA Home
PySide6 desktop shell). Run this on the Pi 5 + AI HAT+2 hardware
(docs/HARDWARE.md); run `main.py` on Home's desktop-class hardware.

Intentionally minimal, same discipline as `main.py`: all real
sequencing lives in `core/core_runtime.py` (context + curated Assistant
action registry) and `core/voice_loop.py` (the press -> transcribe ->
Assistant -> speak cycle). Never imports PySide6 or `gui.*`, directly or
transitively — see `core/core_runtime.py`'s docstring for why that's a
real deployment-footprint requirement, not just tidiness.

Config: `voice.push_to_talk_gpio_pin` selects a real GPIO button
(`core/push_to_talk_source.py`); unset (the dev default) falls back to
a keyboard-driven push-to-talk (Enter to start, Enter to stop).
"""

import sys

from core.config_manager import ConfigManager
from core.core_runtime import build_core_context
from core.event_bus import EventBus
from core.logger import get_logger
from core.push_to_talk_source import build_push_to_talk_source
from core.receiver_indicators import ConsoleReceiverIndicators
from core.voice_loop import VoiceLoopController

log = get_logger(__name__)


def _log_uncaught_exceptions(exc_type, exc_value, exc_traceback) -> None:
    """Same reasoning as main.py's own hook — a headless crash with no
    screen needs its traceback in logs/mia.log (and journalctl under
    systemd) more than ever."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    log.critical("Unhandled exception — MIA Core is crashing.", exc_info=(exc_type, exc_value, exc_traceback))


def main() -> int:
    sys.excepthook = _log_uncaught_exceptions

    config = ConfigManager()
    events = EventBus()
    context = build_core_context(config, events)

    if context.llm is not None and not context.llm.is_available():
        log.warning("Ollama not detected — the Assistant will be unavailable until it's running.")
    if context.voice is not None and not (context.voice.is_stt_available() and context.voice.is_tts_available()):
        log.warning("Voice models not fully available — check deploy/download_voice_models.sh.")

    push_to_talk = build_push_to_talk_source(config.get("voice.push_to_talk_gpio_pin", None))
    indicators = ConsoleReceiverIndicators()
    loop = VoiceLoopController(context, push_to_talk, indicators)

    log.info("MIA Core starting up (version %s) — headless, voice-first.", config.get("system.version"))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        log.info("MIA Core shutting down.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
