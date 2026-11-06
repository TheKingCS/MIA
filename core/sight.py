"""
core.sight
============

Sight (build plan step 15): a photo the person takes, with the glasses'
camera, the phone or the PC, and a question about it, answered by a local
vision model on this PC (Ollama, `sight.model`, Qwen2.5-VL 7B by default).
Nothing leaves the PC.

**Three ways to look** (`kind_of()`, from the question, in code):

- **what**: "what is this?", "what am I looking at?";
- **read**: "read this label", "what does this say?": Tesseract first
  (core/ocr.py: its words are exactly what's printed), the model only when
  Tesseract isn't installed or finds nothing;
- **inspect**: "inspect this part", "is this worn?", "what's wrong with this?":
  condition, wear, damage, what the part likely is, and what to check by hand.

**Within inspection's permission levels** (core/inspection.py): looking is
*authorized*, by the person, one photo at a time, never a camera left
running. **It never identifies a person** ("who is this?" is refused in code,
and the model is told not to), and the photo isn't kept: it's read and let go,
unless the person sends it on to the Inbox.

**Honest about what it is**: a vision model's answer is a judgment from a
picture, so it's said as one ("from the photo, it looks like..."), never as a
fact; text Tesseract read is said as read. Each look is noted in the person's
own folder (kind, how long, whether it answered: never the photo or the
answer) for the `sight.failed` loop.
"""

from __future__ import annotations

import base64
import json
import re
import tempfile
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from core.logger import get_logger

log = get_logger(__name__)

MODEL = "qwen2.5vl:7b"
MAX_BYTES = 15 * 1024 * 1024
WHAT, READ, INSPECT = "what", "read", "inspect"
_READ = re.compile(r"\b(read|what does (it|this|that) say|what('s| is) (written|printed)|the (label|text|sign|words)|"
                   r"ingredients|serial|model number|part number|instructions)\b", re.IGNORECASE)
_INSPECT = re.compile(r"\b(inspect|worn|wear|damage\w*|broken|crack\w*|rust\w*|leak\w*|wrong with|condition|"
                      r"replace|safe to|good shape|failing|what part|which part|identify (this|the) part)\b",
                      re.IGNORECASE)
_WHO = re.compile(r"\b(who (is|are|'s) (this|that|these|they|he|she|in)|whose face|recogni[sz]e (him|her|them|this "
                  r"person)|what('s| is) (his|her|their) name|identify (him|her|them|this person|the person))\b",
                  re.IGNORECASE)
NO_FACES = ("I don't identify people from their faces. I can describe what's in the picture, or read what's written, "
            "if that helps.")

PROMPTS = {
    WHAT: "Say what this photo shows, in two or three plain sentences, starting with the main thing. If you aren't "
          "sure, say what it most likely is and what else it could be. Never identify a person or guess who anyone is.",
    READ: "Read the text in this photo exactly as printed, line by line. Don't add anything that isn't written. "
          "If part of it can't be read, say so. Never identify a person.",
    INSPECT: "This is a photo of a part or a thing to inspect. Say what it most likely is, then its condition: wear, "
             "cracks, rust, leaks, damage, anything missing. Then one or two things to check by hand that a photo "
             "can't show. Be plain and say how sure you are. Never identify a person.",
}


class SightError(ValueError):
    """A look that can't be done; the message says why."""


def kind_of(question: str) -> str:
    """Pure logic. What kind of looking a question asks for."""
    if _INSPECT.search(question or ""):
        return INSPECT
    if _READ.search(question or ""):
        return READ
    return WHAT


def refuses(question: str) -> bool:
    """Pure logic. A question that asks who someone is."""
    return bool(_WHO.search(question or ""))


def _ollama(model: str, prompt: str, image: bytes, url: str = "http://127.0.0.1:11434") -> str:
    body = json.dumps({"model": model, "prompt": prompt, "images": [base64.b64encode(image).decode("ascii")],
                       "stream": False, "options": {"temperature": 0.2}}).encode("utf-8")
    request = urllib.request.Request(f"{url}/api/generate", data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=300) as answer:
        return str(json.loads(answer.read()).get("response", "")).strip()


def _tesseract(context, image: bytes) -> str:
    from core import ocr

    config = getattr(context, "config", None)
    exe = ocr.tesseract_path(config) if config is not None else None
    if not exe:
        return ""
    with tempfile.TemporaryDirectory(prefix="mia_sight_") as tmp:
        path = Path(tmp) / "look.jpg"
        path.write_bytes(image)
        try:
            return ocr.clean_text(ocr.ocr_image(exe, path))
        except Exception:
            log.exception("Sight: Tesseract couldn't read the photo")
            return ""


def look(context, image: bytes, question: str = "what is this?", ask: Optional[Callable] = None,
         read_text: Optional[Callable] = None) -> dict:
    """One look: {"kind", "said", "how", "seconds"}. Raises SightError for what it won't or can't do."""
    if not image:
        raise SightError("No photo came through.")
    if len(image) > MAX_BYTES:
        raise SightError("That photo is over 15 MB.")
    if refuses(question):
        return {"kind": "refused", "said": NO_FACES, "how": "refused", "seconds": 0.0}
    kind = kind_of(question)
    config = getattr(context, "config", None)
    model = (config.get("sight.model", MODEL) if config is not None else MODEL) or MODEL
    started = time.monotonic()
    said, how = "", ""
    if kind == READ:
        text = (read_text or (lambda img: _tesseract(context, img)))(image)
        if text.strip():
            said, how = f"It says:\n{text.strip()}", "read"
    if not said:
        try:
            answer = (ask or _ollama)(model, PROMPTS[kind] + f"\n\nThe person asked: {question}", image)
        except Exception as problem:
            _note(context, kind, False, time.monotonic() - started)
            raise SightError(f"My eyes ({model}) aren't answering on this PC: {problem}") from problem
        if not answer:
            _note(context, kind, False, time.monotonic() - started)
            raise SightError("I couldn't make anything out in that photo.")
        said = answer if kind == READ else "From the photo: " + answer
        how = "vision model"
    seconds = round(time.monotonic() - started, 1)
    _note(context, kind, True, seconds)
    return {"kind": kind, "said": said, "how": how, "seconds": seconds}


# ------------------------------------------------------------------ the record (never the photo or the answer)

def _folder(context) -> Optional[Path]:
    for name in ("failures", "traces"):
        found = getattr(getattr(context, name, None), "data_dir", None)
        if found is not None:
            return Path(found)
    return None


def _note(context, kind: str, answered: bool, seconds: float) -> None:
    folder = _folder(context)
    if folder is None:
        return
    try:
        folder.mkdir(parents=True, exist_ok=True)
        with open(folder / "sight_log.jsonl", "a", encoding="utf-8") as out:
            out.write(json.dumps({"at": datetime.now().isoformat(timespec="seconds"), "kind": kind,
                                  "answered": answered, "seconds": round(seconds, 1)}) + "\n")
    except OSError:
        log.exception("Sight: couldn't note a look")


def looks(context, days: int = 30) -> list[dict]:
    folder = _folder(context)
    if folder is None:
        return []
    since = (datetime.now().timestamp() - days * 86400)
    out = []
    try:
        lines = (folder / "sight_log.jsonl").read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    for line in lines:
        try:
            found = json.loads(line)
        except ValueError:
            continue
        try:
            if datetime.fromisoformat(found["at"]).timestamp() >= since:
                out.append(found)
        except (KeyError, ValueError):
            continue
    return out
