"""
core.voice_manager
====================

The Voice interface's STT/TTS core service — docs/ROADMAP.md milestone
5.3. Defines backend-agnostic `STTBackend`/`TTSBackend` interfaces (same
shape as `core/llm_manager.py`'s `LLMBackend`), with one concrete
implementation each:

- `VoskBackend` (STT) — Vosk is offline, Kaldi-based, and ships ARM/
  aarch64 wheels, making it a realistic fit for the Pi 5's CPU (the AI
  HAT+2's Hailo NPU is an LLM/VLM runtime via `hailo-ollama`, per
  docs/HARDWARE.md — not a general STT/TTS accelerator, so this runs on
  the Pi's own CPU either way).
- `PiperBackend` (TTS) — Piper is developed by the Rhasspy project with
  Raspberry Pi as a primary target platform.

Both models are large binary files fetched by
`deploy/download_voice_models.sh` into `voice_models/` (gitignored, not
committed — see .gitignore) rather than bundled or pip-installed; a
missing/unfetched model degrades to a logged warning and an
"unavailable" state, same pattern as a missing Ollama server in
core/llm_manager.py or a missing/corrupt `.zim` pack in
core/reference_library_manager.py.

**2026-07-15: selectable TTS voices** (`core/voice_catalog.py`), at the
user's explicit request to "pick through different voices for MIA"
`voice.tts_voice_id` (config) selects among `VOICE_CATALOG`'s curated
entries; `list_available_voices()`/`set_voice()` below are the two new
entry points `modules/settings/module.py`'s Voice dropdown uses. The
legacy `voice.tts_model_path` override still wins if explicitly set
(an escape hatch for a model file outside the catalog entirely), same
as before this change.

**2026-07-15: the "AI Voice Effect"** (`core/voice_effects.py`), at the
user's explicit request for MIA to "sound like a futuristic awesome
AI companion device" rather than a plain human voice. `synthesize()`
below post-processes Piper's raw output through
`apply_ai_voice_effect_to_wav_file()` whenever `voice.ai_voice_effect`
is true (default), toggleable in Settings next to the voice picker.
Best-effort — a post-processing failure logs and falls back to the
unprocessed audio rather than losing speech entirely.

**2026-10-29 (DEC-0051): Kokoro is MIA's voice on the computer.**
`KokoroBackend` speaks the `kokoro:*` voices in `core/voice_catalog.py`'s
`KOKORO_CATALOG` (Kokoro-82M through `kokoro-onnx`, offline, 24 kHz,
about five times faster than real time on the home computer). If Kokoro
isn't installed or fails, `synthesize()` falls back to a Piper voice, so
she never goes silent. The AI Voice Effect only ever applies to Piper:
it was there to dress up Piper's low-quality voices, and on Kokoro it
only makes her sound worse.

Recording (mic capture) and playback both go through `sounddevice`,
which wraps the system PortAudio library. Unlike the STT/TTS models,
PortAudio is a *system* package (`libportaudio2` on Debian/Raspberry Pi
OS, installed via apt, not pip) — `import sounddevice` raises `OSError`
outright if it's missing, not just at call time, which is why the
import itself is guarded at module load here rather than inside a
function. This dev environment has no system PortAudio and no audio
hardware at all, so recording/playback can only be verified for their
graceful-degradation path here; the STT/TTS round trip itself (Piper
writes a .wav -> Vosk transcribes it) needs neither and was verified
for real, not just mocked.

**2026-07-18: adjustable playback volume**, at the user's explicit
request ("make the assistant a bit louder with a slider for its
volume"). `voice.playback_volume` (config, default
`_DEFAULT_PLAYBACK_VOLUME` — louder than Piper's raw output, the "bit
louder" half of the ask) is a plain float gain applied to samples in
`play()` itself, not baked into the synthesized `.wav` file the way the
AI Voice Effect is — so moving the Settings slider changes the very
next reply's volume with no re-synthesis needed. Applied in float
space then clipped back to `int16` range (scaling `int16` samples
directly can wrap/overflow instead of clipping cleanly at the top end).
"""

from __future__ import annotations

import json
import re
import tempfile
import wave
from pathlib import Path
from typing import Optional, Protocol

try:  # recording and playback here are the desktop's; a phone uses its own (DEC-0019)
    import numpy as np
except ImportError:
    np = None

from core.app_context import AppContext
from core.logger import get_logger
from core.voice_catalog import (
    DEFAULT_VOICE_ID,
    KOKORO_CATALOG,
    KOKORO_FILES,
    PIPER_DEFAULT_VOICE_ID,
    VOICE_CATALOG,
    VoiceOption,
    find_voice,
)
from core.voice_effects import apply_ai_voice_effect_to_wav_file

log = get_logger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_VOICE_MODELS_DIR = _PROJECT_ROOT / "voice_models"
_DEFAULT_STT_MODEL_PATH = _VOICE_MODELS_DIR / "vosk-model-small-en-us-0.15"
_DEFAULT_SAMPLE_RATE = 16000

#: Playback gain range — see this module's own "adjustable playback
#: volume" docstring note. 1.0 would be Piper's raw, unboosted output;
#: the default is deliberately above that per the user's explicit "make
#: it a bit louder" ask. MIN/MAX bound modules/settings/module.py's slider.
DEFAULT_PLAYBACK_VOLUME = 1.4
MIN_PLAYBACK_VOLUME = 0.5
MAX_PLAYBACK_VOLUME = 2.5


def apply_playback_volume(audio: np.ndarray, volume: float) -> np.ndarray:
    """
    Pure function — testable without real audio hardware (see
    tests/test_voice_manager.py). Scales int16 PCM samples by `volume`
    in float space, then clips back to int16 range rather than letting
    values wrap/overflow — a bare `(audio * volume).astype(int16)`
    would silently wrap a loud, boosted sample around to the opposite
    sign instead of clipping cleanly at the top.
    """
    if volume == 1.0:
        return audio
    amplified = audio.astype(np.float32) * volume
    return np.clip(amplified, -32768, 32767).astype(np.int16)


_MIA_WORD_PATTERN = re.compile(r"\bMIA\b")


def prepare_text_for_speech(text: str) -> str:
    """
    Pure function — testable without a TTS backend (see
    tests/test_voice_manager.py). 2026-07-18: real user ask — "MIA"
    should be *displayed* everywhere (chat text, UI labels), but
    *pronounced* like the name "Mia," not spelled out letter-by-letter,
    which is Piper/espeak's usual heuristic for a bare all-caps word.
    Substituting to mixed-case "Mia" only in the text actually sent to
    synthesis (never in what's shown on screen) gets both at once,
    from one place, regardless of which piece of code composed the
    text. Word-boundary-safe so it doesn't touch "MIAMI" or similar.
    """
    from core.plain_words import for_speech

    return _MIA_WORD_PATTERN.sub("Mia", for_speech(text))  # no "asterisk asterisk" read aloud (2026-10-30)


try:
    if np is None:
        raise ImportError("numpy isn't installed")
    import sounddevice as _sd
    _SOUNDDEVICE_IMPORT_ERROR: Optional[Exception] = None
except (ImportError, OSError) as exc:
    _sd = None
    _SOUNDDEVICE_IMPORT_ERROR = exc


class VoiceUnavailableError(RuntimeError):
    """Raised by a backend when a model is missing or a call otherwise fails."""


class STTBackend(Protocol):
    available: bool

    def transcribe(self, wav_path: Path) -> str:
        """Return the transcribed text, or raise VoiceUnavailableError."""
        ...


class TTSBackend(Protocol):
    available: bool

    def synthesize(self, text: str, output_path: Path) -> None:
        """Write synthesized speech for `text` to `output_path`, or raise VoiceUnavailableError."""
        ...


class VoskBackend:
    """
    STTBackend implementation using Vosk. Loading the model is real
    work (~1s) — deferred to first actual use (`available`/`transcribe`)
    rather than `__init__`, same lazy-cost convention as
    core/reference_library_manager.py's archive opening and
    modules/module_base.py's on_load(), so constructing VoiceManager at
    boot (core/application.py) doesn't add load time to every startup
    for a module that might never be opened.
    """

    def __init__(self, model_path: Path) -> None:
        self._model_path = model_path
        self._model = None
        self._load_failed = False

    def _ensure_loaded(self) -> None:
        if self._model is not None or self._load_failed:
            return
        try:
            from vosk import Model, SetLogLevel

            SetLogLevel(-1)  # Vosk logs verbosely to stderr by default; this app has its own logger.
            self._model = Model(str(self._model_path))
        except Exception as exc:
            log.warning("Could not load Vosk STT model at %s: %s", self._model_path, exc)
            self._load_failed = True

    @property
    def available(self) -> bool:
        self._ensure_loaded()
        return self._model is not None

    def transcribe(self, wav_path: Path) -> str:
        self._ensure_loaded()
        if self._model is None:
            raise VoiceUnavailableError("Vosk STT model is not loaded.")

        from vosk import KaldiRecognizer

        try:
            with wave.open(str(wav_path), "rb") as wf:
                recognizer = KaldiRecognizer(self._model, wf.getframerate())
                text_parts = []
                while True:
                    data = wf.readframes(4000)
                    if not data:
                        break
                    if recognizer.AcceptWaveform(data):
                        text_parts.append(json.loads(recognizer.Result()).get("text", ""))
                text_parts.append(json.loads(recognizer.FinalResult()).get("text", ""))
        except Exception as exc:
            raise VoiceUnavailableError(f"Vosk transcription failed: {exc}") from exc

        return " ".join(part for part in text_parts if part).strip()


class PiperBackend:
    """TTSBackend implementation using Piper. Lazy-loaded — see VoskBackend's docstring for why."""

    def __init__(self, model_path: Path) -> None:
        self._model_path = model_path
        self._voice = None
        self._load_failed = False

    def _ensure_loaded(self) -> None:
        if self._voice is not None or self._load_failed:
            return
        try:
            from piper.voice import PiperVoice

            config_path = self._model_path.with_suffix(self._model_path.suffix + ".json")
            self._voice = PiperVoice.load(str(self._model_path), config_path=str(config_path))
        except Exception as exc:
            log.warning("Could not load Piper TTS voice at %s: %s", self._model_path, exc)
            self._load_failed = True

    @property
    def available(self) -> bool:
        self._ensure_loaded()
        return self._voice is not None

    def synthesize(self, text: str, output_path: Path) -> None:
        self._ensure_loaded()
        if self._voice is None:
            raise VoiceUnavailableError("Piper TTS voice is not loaded.")
        try:
            with wave.open(str(output_path), "wb") as wav_file:
                self._voice.synthesize_wav(text, wav_file)
        except Exception as exc:
            raise VoiceUnavailableError(f"Piper synthesis failed: {exc}") from exc


def _kokoro_dir() -> Path:
    """Read at call time, so tests can point _VOICE_MODELS_DIR elsewhere."""
    return _VOICE_MODELS_DIR / "kokoro"


def kokoro_installed(models_dir: Optional[Path] = None) -> bool:
    """Kokoro's package and both of its files are here (deploy/finish_install.py fetches them)."""
    import importlib.util

    models_dir = models_dir or _kokoro_dir()

    return all((models_dir / name).exists() for _url, name in KOKORO_FILES) and \
        importlib.util.find_spec("kokoro_onnx") is not None


def float_to_int16(samples) -> "np.ndarray":
    """Pure function. Kokoro's float samples (-1..1) as 16-bit PCM, clipped, not wrapped."""
    return (np.clip(np.asarray(samples, dtype=np.float32), -1.0, 1.0) * 32767).astype(np.int16)


class KokoroBackend:
    """TTSBackend implementation using Kokoro (DEC-0051). Lazy-loaded like
    the others; the model is loaded once and shared by every Kokoro voice,
    so switching voices in Settings doesn't reload 300 MB."""

    _loaded: dict[str, object] = {}  # models folder -> kokoro_onnx.Kokoro

    def __init__(self, option: VoiceOption, models_dir: Optional[Path] = None, speed: float = 1.0) -> None:
        self._option = option
        self._models_dir = models_dir or _kokoro_dir()
        self._speed = speed
        self._load_failed = False

    def _model(self):
        key = str(self._models_dir)
        if key in self._loaded or self._load_failed:
            return self._loaded.get(key)
        try:
            from kokoro_onnx import Kokoro

            model, voices = (self._models_dir / name for _url, name in KOKORO_FILES)
            self._loaded[key] = Kokoro(str(model), str(voices))
        except Exception as exc:
            log.warning("Could not load Kokoro from %s: %s", self._models_dir, exc)
            self._load_failed = True
        return self._loaded.get(key)

    @property
    def available(self) -> bool:
        return self._model() is not None

    def synthesize(self, text: str, output_path: Path) -> None:
        model = self._model()
        if model is None:
            raise VoiceUnavailableError("Kokoro is not loaded.")
        try:
            samples, sample_rate = model.create(text, voice=self._option.kokoro_name, speed=self._speed,
                                                lang=self._option.kokoro_lang)
            with wave.open(str(output_path), "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(int(sample_rate))
                wav_file.writeframes(float_to_int16(samples).tobytes())
        except Exception as exc:
            raise VoiceUnavailableError(f"Kokoro synthesis failed: {exc}") from exc


class VoiceManager:
    """
    Core-level Voice service (`AppContext.voice`). Config-driven via
    `voice.stt_model_path`/`voice.tts_model_path`/`voice.sample_rate`,
    following the `modules.<id>.*` / top-level-service config
    convention CLAUDE.md documents. Every public method here catches
    its backend's failure mode and returns None/False (logged) rather
    than raising, so a missing model, missing PortAudio, or absent
    mic/speaker never crashes a caller.
    """

    def __init__(self, context: AppContext) -> None:
        self.context = context
        stt_model_path = Path(context.config.get("voice.stt_model_path", "") or _DEFAULT_STT_MODEL_PATH)
        self._sample_rate = int(context.config.get("voice.sample_rate", _DEFAULT_SAMPLE_RATE))
        self._stt: STTBackend = VoskBackend(stt_model_path)

        # An explicit voice.tts_model_path always wins (a pre-2026-07-15
        # escape hatch for a model file outside the curated catalog
        # entirely); otherwise resolve the configured voice_id against
        # the catalogs, falling back to the default voice.
        explicit_tts_path = context.config.get("voice.tts_model_path", "")
        self._voice_id = context.config.get("voice.tts_voice_id", DEFAULT_VOICE_ID)
        if explicit_tts_path:
            self._tts: TTSBackend = PiperBackend(Path(explicit_tts_path))
            self._engine = "piper"
        else:
            self._tts, self._engine = self._backend_for(self._voice_id)
        self._fallback: Optional[TTSBackend] = None  # Piper, built only if Kokoro fails

        self._recording_frames: list = []
        self._input_stream = None

    # ------------------------------------------------------------------
    # STT / TTS
    # ------------------------------------------------------------------

    def is_stt_available(self) -> bool:
        return self._stt.available

    def is_tts_available(self) -> bool:
        if self._tts.available:
            return True
        fallback = self._piper_fallback() if self._engine == "kokoro" else None
        return fallback is not None and fallback.available

    @staticmethod
    def _model_path_for_voice(voice_id: str) -> Path:
        option = VOICE_CATALOG.get(voice_id)
        filename = option.voice_id if option is not None else voice_id
        return _VOICE_MODELS_DIR / f"{filename}.onnx"

    def _backend_for(self, voice_id: str) -> tuple[TTSBackend, str]:
        option = find_voice(voice_id)
        if option is not None and option.engine == "kokoro":
            speed = float(self.context.config.get("voice.kokoro_speed", 1.0) or 1.0)
            return KokoroBackend(option, speed=speed), "kokoro"
        return PiperBackend(self._model_path_for_voice(voice_id)), "piper"

    def _piper_fallback(self) -> Optional[TTSBackend]:
        """The Piper voice to speak with when Kokoro can't: the default, or any that's here."""
        if self._fallback is None:
            ids = [PIPER_DEFAULT_VOICE_ID] + list(VOICE_CATALOG)
            path = next((p for p in map(self._model_path_for_voice, ids) if p.exists()), None)
            if path is not None:
                self._fallback = PiperBackend(path)
        return self._fallback

    @property
    def current_voice_id(self) -> str:
        return self._voice_id

    def list_available_voices(self) -> list[VoiceOption]:
        """Kokoro's voices first when Kokoro is installed, then the Piper
        voices whose .onnx file is actually present in voice_models/ — a
        fetch via deploy/finish_install.py isn't guaranteed to have run for
        every entry (see docs/KNOWN_ISSUES.md)."""
        kokoro = list(KOKORO_CATALOG.values()) if kokoro_installed() else []
        return kokoro + [option for option in VOICE_CATALOG.values()
                         if self._model_path_for_voice(option.voice_id).exists()]

    def set_voice(self, voice_id: str) -> bool:
        """Switches the active TTS voice and persists the choice.
        Returns False (logged, no change made) if that voice isn't
        installed locally."""
        option = find_voice(voice_id)
        if option is not None and option.engine == "kokoro":
            if not kokoro_installed():
                log.warning("Cannot switch to voice '%s' — Kokoro isn't installed in %s", voice_id, _kokoro_dir())
                return False
        elif not self._model_path_for_voice(voice_id).exists():
            log.warning("Cannot switch to voice '%s' — model file not found at %s",
                        voice_id, self._model_path_for_voice(voice_id))
            return False
        self._voice_id = voice_id
        self._tts, self._engine = self._backend_for(voice_id)
        self.context.config.set("voice.tts_voice_id", voice_id)
        self.context.config.save()
        return True

    def transcribe(self, wav_path: Path) -> Optional[str]:
        try:
            return self._stt.transcribe(Path(wav_path))
        except VoiceUnavailableError as exc:
            log.warning("Speech-to-text unavailable: %s", exc)
            return None

    def synthesize(self, text: str, output_path: Path) -> Optional[Path]:
        output_path = Path(output_path)
        spoken = prepare_text_for_speech(text)
        engine = self._engine
        try:
            self._tts.synthesize(spoken, output_path)
        except VoiceUnavailableError as exc:
            fallback = self._piper_fallback() if engine == "kokoro" else None
            if fallback is None:
                log.warning("Text-to-speech unavailable: %s", exc)
                return None
            log.warning("Kokoro couldn't speak (%s); using Piper instead.", exc)
            try:
                fallback.synthesize(spoken, output_path)
            except VoiceUnavailableError as fallback_exc:
                log.warning("Text-to-speech unavailable: %s", fallback_exc)
                return None
            engine = "piper"
        if engine == "piper" and self.context.config.get("voice.ai_voice_effect", True):
            # Best-effort — a post-processing failure shouldn't turn
            # working speech into no speech at all. See
            # core/voice_effects.py's docstring for what this does
            # and why the defaults are deliberately conservative.
            # Piper only (DEC-0051): see this module's docstring.
            try:
                apply_ai_voice_effect_to_wav_file(output_path)
            except Exception:
                log.exception("AI voice effect post-processing failed — using unprocessed audio instead.")
        return output_path

    # ------------------------------------------------------------------
    # Recording / playback (sounddevice / PortAudio)
    # ------------------------------------------------------------------

    def start_recording(self) -> bool:
        """Begin capturing mic audio for a push-to-talk press. Returns False (logged) if unavailable."""
        if _sd is None:
            log.warning("Cannot start recording — sounddevice/PortAudio is not available: %s", _SOUNDDEVICE_IMPORT_ERROR)
            return False

        self._recording_frames = []
        try:
            self._input_stream = _sd.InputStream(
                samplerate=self._sample_rate,
                channels=1,
                dtype="int16",
                callback=self._on_audio_block,
            )
            self._input_stream.start()
        except Exception as exc:
            log.warning("Could not start audio recording: %s", exc)
            self._input_stream = None
            return False
        return True

    def _on_audio_block(self, indata, frames, time_info, status) -> None:
        self._recording_frames.append(indata.copy())

    def stop_recording(self) -> Optional[Path]:
        """Stop capturing and write the captured audio to a temp WAV file, or None if nothing was captured."""
        if self._input_stream is None:
            return None

        try:
            self._input_stream.stop()
            self._input_stream.close()
        except Exception as exc:
            log.warning("Error stopping audio recording: %s", exc)
        self._input_stream = None

        if not self._recording_frames:
            return None

        audio = np.concatenate(self._recording_frames, axis=0)
        self._recording_frames = []
        output_path = Path(tempfile.gettempdir()) / "mia_push_to_talk.wav"
        with wave.open(str(output_path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self._sample_rate)
            wav_file.writeframes(audio.tobytes())
        return output_path

    def play(self, wav_path: Path) -> bool:
        """Play a WAV file through the system's audio output. Returns False (logged) if unavailable."""
        if _sd is None:
            log.warning("Cannot play audio — sounddevice/PortAudio is not available: %s", _SOUNDDEVICE_IMPORT_ERROR)
            return False

        try:
            with wave.open(str(wav_path), "rb") as wf:
                audio = np.frombuffer(wf.readframes(wf.getnframes()), dtype="int16")
                volume = self.context.config.get("voice.playback_volume", DEFAULT_PLAYBACK_VOLUME)
                audio = apply_playback_volume(audio, volume)
                _sd.play(audio, samplerate=wf.getframerate())
                _sd.wait()
        except Exception as exc:
            log.warning("Could not play audio: %s", exc)
            return False
        return True

    def stop_playback(self) -> None:
        """Immediately cuts off whatever `play()` is currently doing —
        lets the user interrupt MIA mid-sentence. `sounddevice.stop()`
        aborts the stream a running `play()` call started on another
        thread (`core/tts_worker.py`'s `QThread`); the `sd.wait()` inside
        that call's `play()` returns right away once the stream is
        stopped, same as it would on natural playback completion. A
        no-op (not an error) if nothing is currently playing."""
        if _sd is None:
            return
        try:
            _sd.stop()
        except Exception as exc:
            log.warning("Could not stop audio playback: %s", exc)
