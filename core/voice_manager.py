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
user's explicit request to "pick through different voices for M.I.A."
`voice.tts_voice_id` (config) selects among `VOICE_CATALOG`'s curated
entries; `list_available_voices()`/`set_voice()` below are the two new
entry points `modules/settings/module.py`'s Voice dropdown uses. The
legacy `voice.tts_model_path` override still wins if explicitly set
(an escape hatch for a model file outside the catalog entirely), same
as before this change.

**2026-07-15: the "AI Voice Effect"** (`core/voice_effects.py`), at the
user's explicit request for M.I.A. to "sound like a futuristic awesome
AI companion device" rather than a plain human voice. `synthesize()`
below post-processes Piper's raw output through
`apply_ai_voice_effect_to_wav_file()` whenever `voice.ai_voice_effect`
is true (default), toggleable in Settings next to the voice picker.
Best-effort — a post-processing failure logs and falls back to the
unprocessed audio rather than losing speech entirely.

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
import tempfile
import wave
from pathlib import Path
from typing import Optional, Protocol

import numpy as np

from core.app_context import AppContext
from core.logger import get_logger
from core.voice_catalog import DEFAULT_VOICE_ID, VOICE_CATALOG, VoiceOption
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

try:
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
        # VOICE_CATALOG, falling back to the default voice.
        explicit_tts_path = context.config.get("voice.tts_model_path", "")
        self._voice_id = context.config.get("voice.tts_voice_id", DEFAULT_VOICE_ID)
        tts_model_path = Path(explicit_tts_path) if explicit_tts_path else self._model_path_for_voice(self._voice_id)
        self._tts: TTSBackend = PiperBackend(tts_model_path)

        self._recording_frames: list = []
        self._input_stream = None

    # ------------------------------------------------------------------
    # STT / TTS
    # ------------------------------------------------------------------

    def is_stt_available(self) -> bool:
        return self._stt.available

    def is_tts_available(self) -> bool:
        return self._tts.available

    @staticmethod
    def _model_path_for_voice(voice_id: str) -> Path:
        option = VOICE_CATALOG.get(voice_id)
        filename = option.voice_id if option is not None else voice_id
        return _VOICE_MODELS_DIR / f"{filename}.onnx"

    @property
    def current_voice_id(self) -> str:
        return self._voice_id

    def list_available_voices(self) -> list[VoiceOption]:
        """Catalog entries whose .onnx file is actually present in
        voice_models/ — a fetch via deploy/download_voice_models.sh
        isn't guaranteed to have run for every entry (see
        docs/KNOWN_ISSUES.md)."""
        return [option for option in VOICE_CATALOG.values() if self._model_path_for_voice(option.voice_id).exists()]

    def set_voice(self, voice_id: str) -> bool:
        """Switches the active TTS voice and persists the choice.
        Returns False (logged, no change made) if that voice's model
        file isn't present locally."""
        model_path = self._model_path_for_voice(voice_id)
        if not model_path.exists():
            log.warning("Cannot switch to voice '%s' — model file not found at %s", voice_id, model_path)
            return False
        self._voice_id = voice_id
        self._tts = PiperBackend(model_path)
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
        try:
            output_path = Path(output_path)
            self._tts.synthesize(text, output_path)
            if self.context.config.get("voice.ai_voice_effect", True):
                # Best-effort — a post-processing failure shouldn't turn
                # working speech into no speech at all. See
                # core/voice_effects.py's docstring for what this does
                # and why the defaults are deliberately conservative.
                try:
                    apply_ai_voice_effect_to_wav_file(output_path)
                except Exception:
                    log.exception("AI voice effect post-processing failed — using unprocessed audio instead.")
            return output_path
        except VoiceUnavailableError as exc:
            log.warning("Text-to-speech unavailable: %s", exc)
            return None

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
