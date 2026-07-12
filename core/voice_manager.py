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
"""

from __future__ import annotations

import json
import tempfile
import wave
from pathlib import Path
from typing import Optional, Protocol

from core.app_context import AppContext
from core.logger import get_logger

log = get_logger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_STT_MODEL_PATH = _PROJECT_ROOT / "voice_models" / "vosk-model-small-en-us-0.15"
_DEFAULT_TTS_MODEL_PATH = _PROJECT_ROOT / "voice_models" / "en_US-lessac-low.onnx"
_DEFAULT_SAMPLE_RATE = 16000

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
        tts_model_path = Path(context.config.get("voice.tts_model_path", "") or _DEFAULT_TTS_MODEL_PATH)
        self._sample_rate = int(context.config.get("voice.sample_rate", _DEFAULT_SAMPLE_RATE))
        self._stt: STTBackend = VoskBackend(stt_model_path)
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

    def transcribe(self, wav_path: Path) -> Optional[str]:
        try:
            return self._stt.transcribe(Path(wav_path))
        except VoiceUnavailableError as exc:
            log.warning("Speech-to-text unavailable: %s", exc)
            return None

    def synthesize(self, text: str, output_path: Path) -> Optional[Path]:
        try:
            self._tts.synthesize(text, Path(output_path))
            return Path(output_path)
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

        import numpy as np

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
            import numpy as np

            with wave.open(str(wav_path), "rb") as wf:
                audio = np.frombuffer(wf.readframes(wf.getnframes()), dtype="int16")
                _sd.play(audio, samplerate=wf.getframerate())
                _sd.wait()
        except Exception as exc:
            log.warning("Could not play audio: %s", exc)
            return False
        return True
