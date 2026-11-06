"""
core.vault_captions
=====================

Finding a photo again (the memory vault's next step, DEC-0030 phase E): each
photo the computer keeps for the phone (core/memory_vault.py's VaultShelf)
gets one plain sentence saying what's in it, written on this PC by the local
vision model (core/sight.py's model), from a small copy of the photo. Then
"find my photos of the creek" searches those sentences.

- **Never who anyone is.** The caption says "a person" or "two people", as
  sight does; it's never asked who.
- **Kept with the photo**: the caption goes in the shelf's own index, in
  the person's folder (`data/profiles/<id>/vault/`), beside the photo. It
  never leaves this PC.
- **At night, in a process of its own** (`python -m tools.vault_captions`):
  the model takes a few seconds a photo, so a night does a few hundred,
  newest first, and stops at its time budget or when the model doesn't
  answer.
"""

from __future__ import annotations

import io
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from core.logger import get_logger

log = get_logger(__name__)

ROOT = Path(__file__).resolve().parent.parent
PROMPT = ("Describe this photo in one plain sentence, so it can be found again later: the place, the main things in it, "
          "and what's happening. Say 'a person' or 'two people'; never say or guess who anyone is. At most 25 words.")
SMALL = 768  # px on the long side: plenty to say what's in it, and fast
NIGHT_SECONDS = 45 * 60
_STOP = frozenset(("the", "and", "with", "photo", "photos", "picture", "pictures", "pics", "pic", "find", "show", "my",
                   "me", "of", "from", "where", "any", "some", "all", "that", "this", "there", "have", "had"))


def _small(path: Path) -> bytes:
    """A small JPEG of the photo for the model; the photo itself is never changed."""
    try:
        from PIL import Image

        with Image.open(path) as img:
            img = img.convert("RGB")
            img.thumbnail((SMALL, SMALL))
            out = io.BytesIO()
            img.save(out, "JPEG", quality=85)
            return out.getvalue()
    except Exception:
        return path.read_bytes()


def _clean(said: str) -> str:
    line = " ".join(str(said or "").split()).strip(" \"'")
    return line[:240]


def caption_shelf(shelf, ask: Optional[Callable[[str, str, bytes], str]] = None, model: str = "",
                  seconds: float = NIGHT_SECONDS, limit: int = 500) -> int:
    """Caption the shelf's photos that have none yet, newest first, within `seconds`. Returns how many."""
    from core import sight

    ask = ask or sight._ollama
    model = model or sight.MODEL
    waiting = sorted(((sha, e) for sha, e in shelf.index.items()
                      if e.get("kind", "photo") == "photo" and not e.get("caption")),
                     key=lambda item: item[1].get("taken_at") or "", reverse=True)[:limit]
    started, done = time.monotonic(), 0
    for sha, entry in waiting:
        if time.monotonic() - started > seconds:
            break
        path = shelf.path_of(sha)
        if path is None:
            continue
        try:
            said = _clean(ask(model, PROMPT, _small(path)))
        except Exception as problem:  # the model isn't there tonight: stop, try again tomorrow
            log.warning("Captions stopped: %s", problem)
            break
        if not said:
            continue
        entry["caption"], entry["captioned_at"] = said, datetime.now().isoformat(timespec="seconds")
        done += 1
        if done % 20 == 0:
            shelf._save()
    if done:
        shelf._save()
    return done


def _stems(text: str) -> list[str]:
    words = [w for w in re.findall(r"[a-z]+", (text or "").lower()) if len(w) > 2 and w not in _STOP]
    return [w[:-1] if w.endswith("s") and len(w) > 3 else w for w in words]


def search(shelf, words: str, limit: int = 8) -> list[dict]:
    """Photos whose caption has every word asked for (plurals aside), newest first: [{sha, taken_at, name, caption}]."""
    want = _stems(words)
    if not want:
        return []
    found = []
    for sha, entry in shelf.index.items():
        caption = str(entry.get("caption") or "").lower()
        if caption and all(w in caption for w in want):
            found.append({"sha": sha, "taken_at": entry.get("taken_at", ""), "name": entry.get("name", ""),
                          "caption": entry["caption"]})
    return sorted(found, key=lambda f: f["taken_at"] or "", reverse=True)[:limit]


def shelves(root: Path = ROOT) -> list[Path]:
    """Every person's vault folder on this PC."""
    return sorted(p.parent for p in (root / "data" / "profiles").glob("*/vault/index.json"))


# ------------------------------------------------------------------ at night

DATA = ROOT / "data" / "vault_captions"


def due(now: Optional[datetime] = None) -> bool:
    """Between 2 and 5 at night, once, on a PC that keeps someone's photos."""
    now = now or datetime.now()
    return 2 <= now.hour < 5 and bool(shelves()) and not (DATA / f"started-{now.date().isoformat()}").exists()


def launch() -> None:
    import os
    import subprocess

    if os.environ.get("PYTEST_CURRENT_TEST"):
        return  # never from a test run: it runs the vision model
    from core.dev_lab import _python

    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / f"started-{datetime.now().date().isoformat()}").write_text(datetime.now().isoformat(), encoding="utf-8")
    with open(DATA / "last_run.log", "w", encoding="utf-8") as out:
        subprocess.Popen([_python(), "-m", "tools.vault_captions", "run"], cwd=str(ROOT), stdout=out,
                         stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


# ------------------------------------------------------------------ asked for

def _action_find_photos(context, arguments: dict) -> str:
    from core.memory_vault import shelf_for
    from core.person_settings import person_id

    words = str(arguments.get("what", "") or "").strip()
    pid = person_id(context)
    if not words or not pid:
        return "What should I look for in your photos?"
    shelf = shelf_for(context, pid)
    if not any(e.get("caption") for e in shelf.index.values()):
        return ("I haven't looked through your photos yet: I describe the ones this computer keeps for your phone at "
                "night, a few hundred a night, and then I can find them.")
    found = search(shelf, words)
    if not found:
        return f"None of the photos I've looked at show {words}."
    lines = [f"- {f['taken_at'][:10] or 'undated'}: {f['caption']}" for f in found]
    return f"{len(found)} photo{'s' if len(found) != 1 else ''} with {words}:\n" + "\n".join(lines)


def register_vault_caption_actions(registry) -> None:
    from core.assistant_actions import AssistantAction

    registry.register(AssistantAction(
        name="find_photos", domain="vault",
        description=("Find the person's photos by what's in them (the memory vault, described on this PC): "
                     "'photos of the creek', 'the dog in the snow'."),
        parameters={"type": "object", "properties": {
            "what": {"type": "string", "description": "What's in the photo, e.g. 'the creek' or 'a dog in snow'."},
        }, "required": ["what"]},
        handler=_action_find_photos,
        trigger_phrases=("find my photos", "find photos", "photos of", "pictures of", "find the photo",
                         "find a picture", "show me photos"),
    ))
