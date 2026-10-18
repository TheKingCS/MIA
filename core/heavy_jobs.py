"""
core.heavy_jobs
=================

Heavy jobs on the home computer (DEC-0022; Zac, 2026-10-18): when this
device can't do a job well itself and it's linked to MIA on the home
computer (core/home_link.py), the computer does it:

- **reading photos and scanned PDFs** (OCR: the phone has no Tesseract),
- **hearing you** (speech to text, when the phone has no speech model),
- **speaking** (the computer's natural voices, when the phone has none).

The phone's own engines always come first when it has them; the PC is
the fallback, and when the PC doesn't answer either, the job says so the
same way it did before. After a failure the PC isn't asked again for
QUIET_AFTER_FAILURE seconds, so a phone away from home never waits on it
turn after turn. Only the file or the words go to the computer, over
your own link, and nothing is kept there.
"""

from __future__ import annotations

import base64
import time
from pathlib import Path
from typing import Optional
from urllib.parse import quote

from core.logger import get_logger

log = get_logger(__name__)

QUIET_AFTER_FAILURE = 60
MAX_UPLOAD = 60 * 1024 * 1024
_down_until: dict[int, float] = {}


def can_use_home(context) -> bool:
    from core.home_link import linked

    return linked(context) and time.monotonic() >= _down_until.get(id(context), 0.0)


def _failed(context) -> None:
    _down_until[id(context)] = time.monotonic() + QUIET_AFTER_FAILURE


def _call(context, path: str, **kwargs):
    from core.home_link import HomeLinkError, home_call

    if not can_use_home(context):
        raise HomeLinkError("The home computer isn't available right now.")
    try:
        return home_call(context, path, **kwargs)
    except HomeLinkError:
        _failed(context)
        raise


def read_document(context, path: Path) -> list[str]:
    """OCR a photo or a PDF on the home computer: its pages' text."""
    from core.ocr import OcrError

    data = Path(path).read_bytes()
    if len(data) > MAX_UPLOAD:
        raise OcrError("That file is too big to send to the home computer (60 MB at most).")
    try:
        got = _call(context, "/api/heavy/ocr", body=data, timeout=600,
                    headers={"X-Filename": quote(Path(path).name), "Content-Type": "application/octet-stream"})
    except Exception as problem:
        raise OcrError(f"The home computer couldn't read it: {problem}") from None
    return [str(p) for p in got.get("pages") or []]


def transcribe(context, wav: bytes) -> Optional[str]:
    """What was said, heard on the home computer; None if it can't."""
    try:
        got = _call(context, "/api/heavy/transcribe", body=wav, timeout=60,
                    headers={"Content-Type": "audio/wav"})
    except Exception:
        return None
    text = got.get("text")
    return text if isinstance(text, str) else None


def speak(context, text: str) -> Optional[str]:
    """A WAV of MIA saying `text` in the home computer's voice, base64; None if it can't."""
    try:
        got = _call(context, "/api/heavy/speak", payload={"text": text[:2000]}, timeout=30)
    except Exception:
        return None
    audio = got.get("audio_wav_base64")
    if not audio:
        return None
    try:
        base64.b64decode(audio, validate=True)
    except ValueError:
        return None
    return audio
