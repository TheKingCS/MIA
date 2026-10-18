"""
tools.pc_check
================

Is this computer ready to be MIA's home base? (DEC-0022, DEC-0033.)
Everything the phone, the glasses and the cameras need from it, each
with what to do if it isn't there yet:

- MIA's setup check (core/system_check.py): Python, the model, voice,
  reading photos, your password...
- the model: Ollama answering, the configured model downloaded, and how
  much of it fits on the graphics card;
- Phone Access switched on (the server the phone links to);
- Tailscale installed and serving MIA to your own devices;
- ffmpeg, for stream-only cameras (Tapo, Wyze);
- MIA starting when you sign in to Windows, so the phone always finds it.

Usage: .venv\\Scripts\\python tools\\pc_check.py      (setup_home_pc runs it at the end)
Exit code 0 when nothing essential is missing, 2 when something is
(1 is left for a crash, so CI can tell them apart).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OK, MISSING, OPTIONAL = "ok", "missing", "optional"
MARKS = {OK: "[ok]", MISSING: "[!!]", OPTIONAL: "[--]"}


def _get(url: str, timeout: float = 4) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode() or "{}")


def _run(args: list[str], timeout: float = 10) -> tuple[int, str]:
    try:
        done = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return done.returncode, (done.stdout or "") + (done.stderr or "")
    except (OSError, subprocess.TimeoutExpired) as problem:
        return 1, str(problem)


def _tailscale() -> str | None:
    found = shutil.which("tailscale")
    if found:
        return found
    for guess in (r"C:\Program Files\Tailscale\tailscale.exe", "/usr/bin/tailscale", "/usr/local/bin/tailscale"):
        if os.path.exists(guess):
            return guess
    return None


def startup_shortcut() -> Path | None:
    """Where the "start MIA when I sign in" shortcut lives (Windows)."""
    appdata = os.environ.get("APPDATA")
    if not appdata:
        return None
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / "MIA.lnk"


def checks(config) -> list[tuple[str, str, str, str]]:
    """(name, status, what's there, what to do)."""
    out = []
    base = str(config.get("llm.base_url", "http://localhost:11434")).rstrip("/")
    model = str(config.get("llm.model", ""))
    try:
        names = {m["name"] for m in _get(base + "/api/tags").get("models", [])}
        if model in names or f"{model}:latest" in names:
            out.append(("The brain (Ollama)", OK, f"Running, with {model}.", ""))
        else:
            out.append(("The brain (Ollama)", MISSING, f"Running, but {model} isn't downloaded.", f"ollama pull {model}"))
        if not model.startswith("qwen2.5:"):
            out.append(("The home computer's model", OPTIONAL, f"MIA uses {model}.",
                        "setup_home_pc sets qwen2.5:14b (or run tools/pc_model_check.py to pick)."))
    except OSError:
        out.append(("The brain (Ollama)", MISSING, "Ollama isn't answering.",
                    "Install Ollama (setup_home_pc does it), then start it from the Start menu."))
    server = bool(config.get("server.enabled", False))
    port = int(config.get("server.port", 8765))
    out.append(("Phone Access", OK if server else MISSING,
                f"On, at port {port}." if server else "Off: the phone can't link to this computer.",
                "" if server else "MIA → Settings → Phone Access → Let my phone reach MIA (setup_home_pc turns it on)."))
    ts = _tailscale()
    if not ts:
        out.append(("Tailscale", MISSING, "Not installed: the phone can't reach MIA away from home.",
                    "setup_home_pc installs it; or tailscale.com/download."))
    else:
        code, said = _run([ts, "serve", "status"])
        serving = code == 0 and str(port) in said
        url = next((w for w in said.split() if w.startswith("https://") and ".ts.net" in w), "")
        out.append(("Tailscale", OK if serving else MISSING,
                    (f"Serving MIA at {url}." if url else "Serving MIA.") if serving else "Installed, but not serving MIA yet.",
                    "" if serving else f"tailscale up  (sign in), then: tailscale serve --bg http://127.0.0.1:{port}"))
    out.append(("Cameras that stream (ffmpeg)", OK if shutil.which("ffmpeg") else OPTIONAL,
                "Installed." if shutil.which("ffmpeg") else "Not installed; Reolink/Amcrest/Hikvision don't need it.",
                "" if shutil.which("ffmpeg") else "winget install Gyan.FFmpeg (only for Tapo / Wyze)."))
    link = startup_shortcut()
    if link is not None:
        out.append(("Starts with Windows", OK if link.exists() else OPTIONAL,
                    "MIA starts when you sign in." if link.exists() else "MIA only runs when you open it.",
                    "" if link.exists() else "setup_home_pc adds it (so the phone and cameras always find MIA)."))
    return out


def _plain_console() -> None:
    """Windows' console is cp1252 by default: print what it can't show as "?", never crash."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass


def main() -> int:
    _plain_console()
    from core.app_context import AppContext
    from core.config_manager import ConfigManager
    from core.event_bus import EventBus
    from core.system_check import MISSING as SC_MISSING, OK as SC_OK, run_checks

    config = ConfigManager()
    context = AppContext(config=config, events=EventBus())
    try:
        from core.profile_manager import ProfileManager

        context.profiles = ProfileManager(context)
    except Exception:
        context.profiles = None
    print("\nMIA's setup:")
    essential_missing = False
    for c in run_checks(context):
        if c.name in ("Phone access", "Assistant's model", "Your password"):
            continue  # said below, with what the phone needs
        mark = {SC_OK: OK, SC_MISSING: MISSING}.get(c.status, OPTIONAL)
        essential_missing |= mark == MISSING
        print(f"  {MARKS[mark]} {c.name}: {c.detail}" + (f"\n       To do: {c.fix}" if c.fix else ""))
    print("\nThe home computer (phone, glasses, cameras):")
    profiles = getattr(context, "profiles", None)
    active = profiles.get_active_profile() if profiles is not None else None
    people = profiles.list_profiles() if profiles is not None else []
    me = active or (people[0] if people else None)
    if me is None:
        print("  [!!] Your account: none yet.\n       To do: open MIA once and make your account.")
        essential_missing = True
    elif not me.has_password:
        print(f"  [!!] Your password: {me.name} has no password, so the phone can't link."
              "\n       To do: MIA → Settings → Change Password.")
        essential_missing = True
    else:
        print(f"  [ok] Your password: {me.name} can sign in from the phone.")
    for name, status, detail, fix in checks(config):
        essential_missing |= status == MISSING
        print(f"  {MARKS[status]} {name}: {detail}" + (f"\n       To do: {fix}" if fix else ""))
    print("\n" + ("Ready. On the phone: Settings → Home Computer → Link." if not essential_missing
                  else "Not ready yet: do the [!!] lines, then run this again."))
    return 2 if essential_missing else 0


if __name__ == "__main__":
    sys.exit(main())
