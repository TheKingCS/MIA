"""
core.system_check
===================

"Is everything set up?" (2026-10-01, accounts stage 5): one list that
says what works on this device, what's missing, and exactly what to do
about each, so a new person (or a new Raspberry Pi) doesn't have to
guess why voice or photos of receipts don't work.

Each check is quick (a few seconds at most) and never changes anything.
The fixes are shown as steps or commands to run; MIA doesn't install
software by herself. `docs/SETUP_GUIDE.md` has the long version of each.

Shown in Settings → Check My Setup, and by the Assistant ("is
everything set up?").
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

OK, MISSING, OPTIONAL = "ok", "missing", "optional"

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_LOW_DISK_BYTES = 1_000_000_000


@dataclass
class Check:
    name: str
    status: str  # ok | missing | optional (not needed unless you want that feature)
    detail: str
    fix: str = ""


def _ollama_models(base_url: str, timeout: float = 3.0) -> Optional[list[str]]:
    """Model names Ollama has, or None if it isn't reachable."""
    try:
        import requests

        response = requests.get(base_url.rstrip("/") + "/api/tags", timeout=timeout)
        response.raise_for_status()
        return [m.get("name", "") for m in response.json().get("models", [])]
    except Exception:
        return None


def _has_package(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def check_model(config, models: Callable[[str], Optional[list[str]]] = _ollama_models) -> Check:
    base_url = config.get("llm.base_url", "http://localhost:11434")
    model = config.get("llm.model", "llama3.2:3b")
    found = models(base_url)
    if found is None:
        return Check("Assistant's model", MISSING, f"Ollama isn't answering at {base_url}.",
                     "Install Ollama (ollama.com), start it, then run: ollama pull " + model)
    wanted = model if ":" in model else model + ":latest"
    if not any(name in (model, wanted) for name in found):
        return Check("Assistant's model", MISSING, f"Ollama is running but doesn't have {model}.",
                     f"Run: ollama pull {model}")
    return Check("Assistant's model", OK, f"{model} is ready.")


def run_checks(context, models: Callable[[str], Optional[list[str]]] = _ollama_models,
               data_dir: Optional[Path] = None) -> list[Check]:
    config = context.config
    checks: list[Check] = []

    version = sys.version_info
    checks.append(Check("Python", OK if version >= (3, 10) else MISSING, f"Python {version.major}.{version.minor}.",
                        "" if version >= (3, 10) else "Install Python 3.10 or newer."))
    checks.append(check_model(config, models))

    voice = getattr(context, "voice", None)
    stt = bool(voice and voice.is_stt_available())
    tts = bool(voice and voice.is_tts_available())
    checks.append(Check("Hearing you (speech to text)", OK if stt else OPTIONAL,
                        "Ready." if stt else "No speech-to-text model yet; typing still works.",
                        "" if stt else "Run deploy/download_voice_models.sh (fetches the speech models into voice_models/)."))
    checks.append(Check("Speaking (text to speech)", OK if tts else OPTIONAL,
                        "Ready." if tts else "No voice yet; replies are shown as text.",
                        "" if tts else "Run deploy/download_voice_models.sh (fetches Piper's voice into voice_models/)."))

    from core.ocr import available as ocr_available

    ocr = ocr_available(config)
    checks.append(Check("Reading photos and scans", OK if ocr else OPTIONAL,
                        "Tesseract is installed." if ocr else "Photos of receipts and scanned books can't be read yet.",
                        "" if ocr else "Install Tesseract: sudo apt install tesseract-ocr (Windows: SETUP_GUIDE.md, Part 1a)."))

    phone = _has_package("fastapi") and _has_package("uvicorn")
    checks.append(Check("Phone access", OK if phone else OPTIONAL,
                        ("Ready" + (" and switched on." if config.get("server.enabled", False) else
                                    "; switch it on in Settings when you want it.")) if phone else
                        "The phone server's packages aren't installed.",
                        "" if phone else "Run: pip install -r requirements.txt"))
    checks.append(Check("Bank sync (Plaid)", OK if _has_package("plaid") else OPTIONAL,
                        "Installed." if _has_package("plaid") else "Not installed; budgets work without it.",
                        "" if _has_package("plaid") else "Run: pip install -r requirements.txt"))

    folder = Path(data_dir) if data_dir is not None else _DATA_DIR
    folder.mkdir(parents=True, exist_ok=True)
    writable = os.access(folder, os.W_OK)
    free = shutil.disk_usage(folder).free
    checks.append(Check("Saving your data", OK if writable else MISSING,
                        f"{free / 1e9:.1f} GB free." if writable else f"MIA can't write to {folder}.",
                        "" if writable else f"Give your user write access to {folder}."))
    if writable and free < _LOW_DISK_BYTES:
        checks.append(Check("Disk space", MISSING, f"Only {free / 1e6:.0f} MB free.",
                            "Free up space or move data/ to a bigger drive (HARDWARE.md)."))

    profiles = getattr(context, "profiles", None)
    active = profiles.get_active_profile() if profiles is not None else None
    if active is not None:
        if not active.has_password:
            checks.append(Check("Your password", OPTIONAL, "Your account has no password.",
                                "Settings, Change Password: needed for the phone, and it gives you a recovery code."))
        elif not active.email:
            checks.append(Check("Your sign-in email", OPTIONAL, "No email on your account yet.",
                                "Settings, Email, Recovery Code & Household."))
        else:
            checks.append(Check("Your account", OK, f"Signed in as {active.email}."))
    return checks


def summary(checks: list[Check]) -> str:
    """Pure logic. One short spoken sentence, then what to fix."""
    missing = [c for c in checks if c.status == MISSING]
    optional = [c for c in checks if c.status == OPTIONAL]
    if not missing and not optional:
        return "Everything's set up."
    parts = []
    if missing:
        parts.append("Needs fixing: " + "; ".join(f"{c.name} ({c.fix or c.detail})" for c in missing) + ".")
    else:
        parts.append("Everything I need works.")
    if optional:
        parts.append("Optional extras not set up: " + ", ".join(c.name.lower() for c in optional) + ".")
    return " ".join(parts) + " Settings, Check My Setup shows the steps."
