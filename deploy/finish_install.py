#!/usr/bin/env python3
"""
deploy/finish_install.py
==========================

The part of MIA's installer that's the same on every computer
(2026-10-01). `install.sh` (Linux, Raspberry Pi) and `install.ps1`
(Windows) install system tools and Python packages, then run this with
MIA's own Python:

1. **Voice**: downloads the speech-to-text model and every voice in
   core/voice_catalog.py into voice_models/ (skips what's there).
2. **Brain**: `ollama pull` of the model in MIA's config, if Ollama is
   installed.
3. **Shortcut**: a "MIA" entry in the app menu and on the desktop
   (Linux; the Windows installer makes its own).
4. **Check**: prints Check My Setup (core/system_check.py), so the
   person sees what works and what's left.

Safe to run again any time. Flags: --no-voice, --no-model,
--no-shortcut, --check-only.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

MIA_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(MIA_DIR))

VOSK_MODEL = "vosk-model-small-en-us-0.15"
VOSK_URL = f"https://alphacephei.com/vosk/models/{VOSK_MODEL}.zip"


def say(text: str) -> None:
    print(text, flush=True)


# ---------------------------------------------------------------- voice


def voice_downloads(models_dir: Path) -> list[tuple[str, Path]]:
    """Pure logic. (url, target) for every voice file not downloaded yet.
    The speech-to-text model (a zip) is listed as its folder."""
    from core.voice_catalog import VOICE_CATALOG

    wanted: list[tuple[str, Path]] = []
    if not (models_dir / VOSK_MODEL / "am").is_dir():  # an empty or half-unpacked folder doesn't count
        wanted.append((VOSK_URL, models_dir / VOSK_MODEL))
    for voice in VOICE_CATALOG.values():
        for url, name in ((voice.onnx_url, f"{voice.voice_id}.onnx"), (voice.onnx_json_url, f"{voice.voice_id}.onnx.json")):
            if not (models_dir / name).exists():
                wanted.append((url, models_dir / name))
    return wanted


def _download(url: str, target: Path) -> None:
    partial = target.with_name(target.name + ".part")
    with urllib.request.urlopen(url, timeout=60) as response, open(partial, "wb") as out:
        shutil.copyfileobj(response, out)
    partial.replace(target)


def install_voice(models_dir: Path) -> bool:
    models_dir.mkdir(parents=True, exist_ok=True)
    todo = voice_downloads(models_dir)
    if not todo:
        say("  Voice: already downloaded.")
        return True
    ok = True
    for url, target in todo:
        say(f"  Downloading {target.name}...")
        try:
            if url.endswith(".zip"):
                with tempfile.TemporaryDirectory() as tmp:
                    archive = Path(tmp) / "model.zip"
                    _download(url, archive)
                    with zipfile.ZipFile(archive) as z:
                        z.extractall(models_dir)
            else:
                _download(url, target)
        except Exception as exc:  # network trouble: keep going, the check will say what's missing
            say(f"  Couldn't download {target.name} ({exc}). Run the installer again later.")
            ok = False
    return ok


# ---------------------------------------------------------------- brain


def model_name() -> str:
    from core.config_manager import ConfigManager

    return ConfigManager().get("llm.model", "llama3.2")


def install_model(ollama: str | None = None) -> bool:
    ollama = ollama or shutil.which("ollama")
    if not ollama:
        say("  Ollama isn't installed, so MIA's brain is skipped. The installer can add it; or see ollama.com.")
        return False
    name = model_name()
    say(f"  Getting the model {name} (about 2 GB the first time)...")
    return subprocess.call([ollama, "pull", name]) == 0


# ---------------------------------------------------------------- shortcut


def desktop_entry(mia_dir: Path) -> str:
    """Pure logic. A freedesktop launcher for MIA."""
    python = mia_dir / ".venv" / "bin" / "python"
    icon = mia_dir / "assets" / "mia_icon.png"
    lines = [
        "[Desktop Entry]", "Type=Application", "Name=MIA",
        "Comment=Your offline assistant and organizer",
        f'Exec="{python}" "{mia_dir / "main.py"}"', f"Path={mia_dir}", "Terminal=false",
        "Categories=Utility;Office;",
    ]
    if icon.exists():
        lines.append(f"Icon={icon}")
    return "\n".join(lines) + "\n"


def install_shortcut(mia_dir: Path, home: Path) -> list[Path]:
    if os.name == "nt":
        return []  # install.ps1 makes the Windows shortcut
    text = desktop_entry(mia_dir)
    written = []
    folders = [home / ".local" / "share" / "applications"]
    if (home / "Desktop").is_dir():
        folders.append(home / "Desktop")
    for folder in folders:
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / "mia.desktop"
        target.write_text(text, encoding="utf-8")
        target.chmod(0o755)
        written.append(target)
    return written


# ---------------------------------------------------------------- check


def print_check() -> int:
    from core.app_context import AppContext
    from core.config_manager import ConfigManager
    from core.event_bus import EventBus
    from core.system_check import MISSING, OK, run_checks

    context = AppContext(config=ConfigManager(), events=EventBus())
    try:
        from core.voice_manager import VoiceManager

        context.voice = VoiceManager(context)
    except Exception:
        context.voice = None
    checks = run_checks(context)
    marks = {OK: "[ok]", MISSING: "[!!]"}
    say("\nMIA setup check:")
    for check in checks:
        say(f"  {marks.get(check.status, '[--]')} {check.name}: {check.detail}")
        if check.fix:
            say(f"       To do: {check.fix}")
    return 1 if any(c.status == MISSING for c in checks) else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Finish installing MIA.")
    parser.add_argument("--no-voice", action="store_true")
    parser.add_argument("--no-model", action="store_true")
    parser.add_argument("--no-shortcut", action="store_true")
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args(argv)
    if not args.check_only:
        if not args.no_voice:
            say("Voice (hearing and speaking):")
            install_voice(MIA_DIR / "voice_models")
        if not args.no_model:
            say("MIA's brain:")
            install_model()
        if not args.no_shortcut:
            for path in install_shortcut(MIA_DIR, Path.home()):
                say(f"  Shortcut: {path}")
    return print_check()


if __name__ == "__main__":
    sys.exit(main())
