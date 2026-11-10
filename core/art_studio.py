"""
core.art_studio
=================

MIA paints (DEC-0140, Zac 2026-11-08: "She should also be able to be
prompted to generate art assets and use them in her program, like if you
wanted the background to show a fantasy castle/village scene"). A
description becomes a picture on the PC's own graphics card, through a local
image engine (ComfyUI, which runs on the RX 7900 XTX with ROCm on Windows;
setup: docs/ART_ENGINE.md). Nothing is sent anywhere else (DEC-0053: a cloud
service only once Zac approves that service). Each picture is kept in the
person's own folder, and can be used in MIA: as a theme's backdrop behind
every page and on the 3D room's far wall (core/themes.py `backdrop`).

- `problem(description)` (pure): why MIA won't paint this, or None
  (sexual content and gore are refused; a real person's likeness too).
- `prompt_for(description, use)` (pure): the prompt the engine gets, its
  negative prompt and size: MIA's style for that use (a wide, atmospheric
  environment for a backdrop; a framed scene for a portal), with no text,
  logos or people in it.
- `ArtStore` (a personal store, `art.json` and `art/<id>.png`): the
  pictures, with what they were painted from.
- `ComfyEngine(url)`: the engine's HTTP API: is it running, which model,
  paint (queue a text-to-image graph, wait for it, fetch the image).
- `start(context, description, use, apply)`: a painting job on its own
  worker thread (the one long-running task here, scoped to this module as
  CLAUDE.md asks). The thread only talks to the engine and writes the
  image to a staging file; it never touches a store.
- `settle(context)`: on the main thread (the art endpoints, the shell, a
  turn), finished jobs become pictures in the person's store and, when the
  painting was asked for as the background, go up as their theme's backdrop
  through `theme.save` (approved by asking, undoable).
- `status(context)`: the engine, the person's pictures and their jobs.
"""

from __future__ import annotations

import json
import random
import re
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from core import life_events
from core.at_rest import open_text
from core.atomic_write import atomic_write_text
from core.logger import get_logger

log = get_logger(__name__)

FILE_NAME = "art.json"
FOLDER = "art"
DEFAULT_URL = "http://127.0.0.1:8188"  # ComfyUI's own port; 127.0.0.1, not localhost (some browsers refuse it)
MAX_ITEMS = 60
# What each use asks of the picture: its size (SDXL's own buckets) and MIA's style for it.
USES: dict[str, tuple[int, int, str]] = {
    "backdrop": (1344, 768, "wide cinematic environment concept art, {d}, sweeping establishing shot, painterly "
                            "digital illustration, rich atmospheric lighting, volumetric light and mist, deep "
                            "shadows toward the edges, highly detailed"),
    "portal": (832, 1216, "{d}, a single clear subject centred in the frame, painterly cinematic illustration, dusk "
                          "or night, glowing light, dark vignette edges, highly detailed"),
    # The Character card's portrait (2026-11-09): a crest, never a person (NEGATIVE keeps people and faces out).
    "crest": (1024, 1024, "{d}, a heraldic crest emblem, one symbolic design centred, ornate metal and glowing light, "
                          "dark background, painterly fantasy illustration, symmetrical, highly detailed"),
}
NEGATIVE = ("text, letters, words, writing, watermark, signature, logo, brand, ui, frame, border, people, person, face, "
            "crowd, blurry, lowres, jpeg artifacts, deformed")
_BLOCKED = re.compile(r"\b(nude|naked|nsfw|porn\w*|sex\w*|erotic|gore|gory|dismember\w*|corpse|mutilat\w*)\b", re.I)
_LIKENESS = re.compile(r"\b(photo|picture|portrait|image|face|likeness) of ([A-Z][a-z]+ [A-Z][a-z]+)")
_ID = re.compile(r"^[a-f0-9]{12}$")


def problem(description: str) -> Optional[str]:
    """Pure logic. Why MIA won't paint this (sexual content, gore, a real person's likeness), or None."""
    text = " ".join((description or "").split())
    if not text:
        return "Describe what to paint: a place, a mood, a time of day."
    if len(text) > 400:
        return "That's a lot to paint; try it in a sentence or two."
    if _BLOCKED.search(text):
        return "MIA doesn't paint that. Scenes and places are her thing."
    if _LIKENESS.search(text):
        return "MIA doesn't paint real people. A place or a scene, though, she'd love to."
    return None


def prompt_for(description: str, use: str = "backdrop") -> dict:
    """Pure logic. {positive, negative, width, height} for the engine: MIA's style for the use around their words."""
    width, height, style = USES.get(use, USES["backdrop"])
    words = " ".join((description or "").split()).rstrip(".")
    return {"positive": style.format(d=words), "negative": NEGATIVE, "width": width, "height": height}


class ArtStore:
    """The person's pictures: `art.json` (what each was painted from) and `art/<id>.png`."""

    def __init__(self, context=None, data_dir: Optional[Path] = None) -> None:
        """Loads art.json from the person's folder (or data/); a file that won't open starts empty."""
        self.context = context
        self.data_dir = Path(data_dir) if data_dir is not None else Path(__file__).resolve().parent.parent / "data"
        self._file = self.data_dir / FILE_NAME
        self.folder = self.data_dir / FOLDER
        self._load()

    def _load(self) -> None:
        """Reads the index. Sealed at rest (DEC-0126): a sealed file is opened; one that won't open is copied aside and starts empty."""
        self.items: list[dict] = []
        if not self._file.exists():
            return
        try:
            data = json.loads(open_text(self._file))
        except (OSError, ValueError):
            log.exception("Art: couldn't read %s; starting empty", self._file)
            return
        self.items = [i for i in (data.get("items") or []) if isinstance(i, dict) and _ID.match(str(i.get("id", "")))]

    def _save(self) -> None:
        """Writes the index atomically (so "undo" can put it back)."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._file, json.dumps({"version": 1, "items": self.items}, indent=2))

    def all(self) -> list[dict]:
        """Every picture, newest first."""
        return sorted(self.items, key=lambda i: i.get("made_at", ""), reverse=True)

    def get(self, art_id: str) -> Optional[dict]:
        """One picture's record, or None."""
        return next((i for i in self.items if i["id"] == art_id), None)

    def path(self, art_id: str) -> Optional[Path]:
        """A picture's file, if it's one of theirs and it's there."""
        if not _ID.match(str(art_id or "")) or self.get(art_id) is None:
            return None
        path = self.folder / f"{art_id}.png"
        return path if path.is_file() else None

    @life_events.on_change("art_added", "a painting MIA made", named=False)
    def add(self, staged: Path, description: str, use: str, prompt: dict, seed: int, engine: str) -> dict:
        """Moves a painted image in from its staging file and records it (and a line in the person's history); the
        oldest go past MAX_ITEMS."""
        self.folder.mkdir(parents=True, exist_ok=True)
        art_id = uuid.uuid4().hex[:12]
        staged.replace(self.folder / f"{art_id}.png")
        item = {"id": art_id, "description": description, "use": use, "prompt": prompt["positive"], "seed": seed,
                "width": prompt["width"], "height": prompt["height"], "engine": engine,
                "made_at": datetime.now().isoformat(timespec="seconds")}
        self.items.append(item)
        self.items = self.all()[:MAX_ITEMS]
        self._save()
        return item

    @life_events.on_change("art_removed", "a painting", named=False)
    def remove(self, art_id: str) -> dict:
        """Takes a picture out of the list (a line in the history); its file is kept aside (art/removed/) so "undo" can
        bring it back."""
        item = self.get(art_id)
        if item is None:
            raise ValueError("That picture isn't one of yours.")
        source = self.folder / f"{art_id}.png"
        if source.is_file():
            (self.folder / "removed").mkdir(parents=True, exist_ok=True)
            source.replace(self.folder / "removed" / f"{art_id}.png")
        self.items = [i for i in self.items if i["id"] != art_id]
        self._save()
        return item


class EngineError(Exception):
    """The image engine couldn't paint (not running, no model, failed, too slow): a sentence for the person."""


class ComfyEngine:
    """ComfyUI's HTTP API on this PC (its own server; MIA only calls it)."""

    def __init__(self, url: str = DEFAULT_URL, timeout: float = 300.0) -> None:
        """The engine at `url`; a painting may take up to `timeout` seconds."""
        self.url = (url or DEFAULT_URL).rstrip("/")
        self.timeout = timeout

    def _get(self, path: str, wait: float = 5.0) -> bytes:
        """GETs a path from the engine."""
        from urllib.request import urlopen

        with urlopen(self.url + path, timeout=wait) as response:  # noqa: S310 (a local engine's own URL)
            return response.read()

    def _post(self, path: str, body: dict) -> dict:
        """POSTs JSON to the engine and reads its JSON answer."""
        from urllib.request import Request, urlopen

        request = Request(self.url + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        with urlopen(request, timeout=10) as response:  # noqa: S310
            return json.loads(response.read() or b"{}")

    def available(self) -> tuple[bool, str]:
        """(running?, a line about it)."""
        try:
            stats = json.loads(self._get("/system_stats", wait=2.0))
        except Exception:
            return False, f"No image engine at {self.url}. Start ComfyUI on this PC (docs/ART_ENGINE.md)."
        devices = stats.get("devices") or []
        name = devices[0].get("name", "") if devices and isinstance(devices[0], dict) else ""
        return True, ("ComfyUI is running" + (f" on {name}" if name else "") + ".")

    def checkpoint(self, preferred: str = "") -> str:
        """The model to paint with: the preferred one if the engine has it, else an SDXL one, else the first."""
        try:
            info = json.loads(self._get("/object_info/CheckpointLoaderSimple"))
            names = info["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"][0]
        except Exception as problem_:
            raise EngineError("The image engine didn't say which models it has.") from problem_
        if not names:
            raise EngineError("The image engine has no model yet. Put an SDXL checkpoint in ComfyUI's models/checkpoints.")
        if preferred in names:
            return preferred
        return next((n for n in names if "xl" in n.lower()), names[0])

    @staticmethod
    def workflow(prompt: dict, seed: int, checkpoint: str, steps: int = 28) -> dict:
        """Pure logic. ComfyUI's text-to-image graph (its API format): model, the two prompts, an empty picture of the
        size, the sampler, decoding, and saving under MIA's name."""
        return {
            "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": checkpoint}},
            "2": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt["positive"], "clip": ["1", 1]}},
            "3": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt["negative"], "clip": ["1", 1]}},
            "4": {"class_type": "EmptyLatentImage", "inputs": {"width": prompt["width"], "height": prompt["height"], "batch_size": 1}},
            "5": {"class_type": "KSampler", "inputs": {"model": ["1", 0], "positive": ["2", 0], "negative": ["3", 0],
                                                        "latent_image": ["4", 0], "seed": seed, "steps": steps, "cfg": 6.5,
                                                        "sampler_name": "dpmpp_2m", "scheduler": "karras", "denoise": 1.0}},
            "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
            "7": {"class_type": "SaveImage", "inputs": {"images": ["6", 0], "filename_prefix": "MIA"}},
        }

    def paint(self, prompt: dict, seed: int, checkpoint: str, poll: float = 1.0) -> bytes:
        """Queues the graph, waits for it, and returns the PNG. EngineError on anything that goes wrong."""
        from urllib.parse import urlencode

        try:
            queued = self._post("/prompt", {"prompt": self.workflow(prompt, seed, checkpoint), "client_id": "mia"})
        except Exception as problem_:
            raise EngineError("The image engine didn't take the painting.") from problem_
        prompt_id = queued.get("prompt_id")
        if not prompt_id:
            raise EngineError("The image engine refused the painting: " + str(queued.get("error") or queued)[:160])
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            try:
                history = json.loads(self._get(f"/history/{prompt_id}"))
            except Exception:
                history = {}
            done = history.get(prompt_id) or {}
            for output in (done.get("outputs") or {}).values():
                for image in output.get("images") or []:
                    query = urlencode({"filename": image["filename"], "subfolder": image.get("subfolder", ""),
                                       "type": image.get("type", "output")})
                    return self._get("/view?" + query, wait=30.0)
            if (done.get("status") or {}).get("status_str") == "error":
                raise EngineError("The image engine hit an error while painting.")
            time.sleep(poll)
        raise EngineError("The painting took too long; the image engine may be busy.")


# ------------------------------------------------------------------ jobs (one worker thread each)
_JOBS: dict[str, dict] = {}
_LOCK = threading.Lock()


def engine_for(context) -> ComfyEngine:
    """The device's image engine (config `art.engine_url`, set by the PC's owner; ComfyUI's port by default)."""
    config = getattr(context, "config", None)
    url = config.get("art.engine_url", DEFAULT_URL) if config is not None else DEFAULT_URL
    return ComfyEngine(url or DEFAULT_URL)


def _person(context) -> str:
    """Whose job this is (the signed-in person, or the device)."""
    from core import person_settings

    try:
        return person_settings.person_id(context) or "device"
    except Exception:
        return "device"


def _staging(context) -> Path:
    """Where a worker leaves a finished image for settle() to take in."""
    store = getattr(context, "art", None)
    base = store.data_dir if store is not None else Path(__file__).resolve().parent.parent / "data"
    return base / FOLDER / "staging"


def start(context, description: str, use: str = "backdrop", apply: bool = False, engine: Optional[ComfyEngine] = None,
          wait: bool = False, area: str = "") -> dict:
    """Starts a painting: checks the words and that the engine is running, then paints on a worker thread. Returns the
    job ({id, status: painting, description, use}); ValueError with a sentence when it can't start. `apply`: put it up
    as the background when it's done (settle); for a portal picture with `area`, put it in that area's portal instead
    (core/portal_pictures); for a crest, on the Character card. `wait`: paint on this thread (tests)."""
    reason = problem(description)
    if reason:
        raise ValueError(reason)
    if use not in USES:
        raise ValueError("MIA paints backdrops, portal pictures and character crests.")
    engine = engine or engine_for(context)
    running, line = engine.available()
    if not running:
        raise ValueError(line)
    config = getattr(context, "config", None)
    preferred = config.get("art.checkpoint", "") if config is not None else ""
    description = " ".join(description.split())
    prompt = prompt_for(description, use)
    seed = random.randint(1, 2**31 - 1)
    job = {"id": uuid.uuid4().hex[:12], "person": _person(context), "description": description, "use": use,
           "apply": bool(apply), "area": str(area or "") if use == "portal" else "", "status": "painting", "error": "", "art_id": "", "seed": seed, "prompt": prompt,
           "engine": engine.url, "started": time.time(), "staged": "", "settled": False}
    staging = _staging(context)

    def work() -> None:
        """Paints and leaves the PNG in staging; never touches a store (settle does, on the main thread)."""
        try:
            checkpoint = engine.checkpoint(preferred)
            png = engine.paint(prompt, seed, checkpoint)
            staging.mkdir(parents=True, exist_ok=True)
            staged = staging / f"{job['id']}.png"
            staged.write_bytes(png)
            with _LOCK:
                job.update(status="painted", staged=str(staged), engine=f"{engine.url} ({checkpoint})")
            _wake()
        except EngineError as problem_:
            with _LOCK:
                job.update(status="failed", error=str(problem_))
            _wake()
        except Exception:
            log.exception("Art: painting %s failed", job["id"])
            with _LOCK:
                job.update(status="failed", error="Something went wrong while painting.")
            _wake()

    with _LOCK:
        _JOBS[job["id"]] = job
    if wait:
        work()
    else:
        threading.Thread(target=work, name=f"mia-art-{job['id']}", daemon=True).start()
    return public(job)


def _wake() -> None:
    """Tells open pages something changed (core/live.py is thread-safe), so they re-read the shell, whose endpoint
    settles the job on the main thread."""
    from core import live

    live.bump()


def active(context) -> int:
    """How many of this person's paintings are still going."""
    me = _person(context)
    with _LOCK:
        return sum(1 for j in _JOBS.values() if j["person"] == me and j["status"] == "painting")


def public(job: dict) -> dict:
    """Pure logic. A job as the page sees it (with the area, for a picture going in a portal)."""
    return {k: job.get(k, "") for k in ("id", "description", "use", "apply", "area", "status", "error", "art_id")} | {
        "seconds": round(time.time() - job["started"])}


def settle(context) -> list[dict]:
    """On the main thread: this person's finished paintings become pictures in their store; one asked for as the
    background goes up as their theme's backdrop, one asked for an area's portal goes in that portal, and a crest asked
    for the Character card goes there (`character.crest`). Returns the jobs it settled."""
    store = getattr(context, "art", None)
    me = _person(context)
    with _LOCK:
        ready = [j for j in _JOBS.values() if j["person"] == me and not j["settled"] and j["status"] in ("painted", "failed")]
        for job in ready:
            job["settled"] = True
    done = []
    for job in ready:
        if job["status"] == "painted" and store is not None:
            item = store.add(Path(job["staged"]), job["description"], job["use"], job["prompt"], job["seed"], job["engine"])
            with _LOCK:
                job.update(status="done", art_id=item["id"])
            if job["apply"] and job.get("area"):
                try:
                    from core.portal_pictures import put_up

                    put_up(context, job["area"], item["id"])
                except ValueError as problem_:
                    log.warning("Art: couldn't put %s in the %s portal: %s", item["id"], job["area"], problem_)
            elif job["apply"] and job["use"] == "crest":
                from core import person_settings

                person_settings.put(context, "character.crest", item["id"])
            elif job["apply"]:
                try:
                    use_as_backdrop(context, item["id"])
                except ValueError as problem_:
                    log.warning("Art: couldn't put %s up as the backdrop: %s", item["id"], problem_)
            _tell(context, job, item)
        elif job["status"] == "failed":
            _tell(context, job, None)
        done.append(public(job))
    return done


def _tell(context, job: dict, item: Optional[dict]) -> None:
    """A note that the painting is ready, and where it went (the background, a portal, or the Theme Studio), or why
    not: a reply to what the person asked, so it goes straight to
    notifications rather than through the communication gate."""
    notifications = getattr(context, "notifications", None)
    if notifications is None:
        return
    try:
        if item is None:
            notifications.notify("Painting didn't finish", job["error"] or "The image engine stopped.")
        else:
            notifications.notify("Painting ready", f"{job['description'][:60]}" + (
                " is in its portal in the Nexus." if job["apply"] and job.get("area")
                else " is up as your background." if job["apply"] else " is in your art, in the Theme Studio."))
    except Exception:
        log.exception("Art: couldn't send the note")


def use_as_backdrop(context, art_id: str, strength: Optional[float] = None) -> str:
    """Puts a picture up as the person's backdrop (or takes it down with art_id ""): on their own theme in use, or on
    their own copy of the built-in one ("My Stark"), through theme.save so "undo" puts it back. ValueError when the
    picture isn't theirs."""
    from core.actions import ActionError
    from core.theme_actions import _save
    from core.themes import THEMES, all_themes, choices_of, theme_of

    store = getattr(context, "art", None)
    if art_id and (store is None or store.path(art_id) is None):
        raise ValueError("That picture isn't one of yours.")
    themes = all_themes(context)
    current = theme_of(context)
    theme = themes[current]
    picks = dict(choices_of(theme))
    picks["backdrop"] = art_id
    if strength is not None:
        picks["backdrop_strength"] = strength
    params = {"choices": picks, "base": current, "use": True, "name": theme["name"]}
    if current in THEMES:
        taken = {t["name"].lower() for t in themes.values()}
        params["name"], n = "My " + theme["name"], 2
        while params["name"].lower() in taken:
            params["name"], n = f"My {theme['name']} {n}", n + 1
    else:
        params["id"] = current
    try:
        return _save(context, params)
    except ActionError as problem_:
        raise ValueError(str(problem_)) from None


def status(context) -> dict:
    """The art screen's data: the engine (running or not, and how to start it), the person's pictures and their jobs."""
    settle(context)
    running, line = engine_for(context).available()
    store = getattr(context, "art", None)
    me = _person(context)
    with _LOCK:
        jobs = [public(j) for j in _JOBS.values() if j["person"] == me and time.time() - j["started"] < 3600]
    return {"engine": {"available": running, "line": line, "setup": "docs/ART_ENGINE.md"},
            "items": [{**{k: i[k] for k in ("id", "description", "use", "made_at", "width", "height")},
                       "image": f"/api/art/{i['id']}/image"} for i in (store.all() if store is not None else [])],
            "jobs": sorted(jobs, key=lambda j: -j["seconds"])[:8], "uses": list(USES)}


def find(context, words: str) -> Optional[dict]:
    """Pure-ish. The person's picture their words point at ("the castle one"), newest first, or None."""
    store = getattr(context, "art", None)
    if store is None:
        return None
    want = {w for w in re.findall(r"[a-z]+", (words or "").lower()) if len(w) > 2} - {"the", "one", "and", "with", "that"}
    best, score = None, 0
    for item in store.all():
        have = set(re.findall(r"[a-z]+", item["description"].lower()))
        hit = len(want & have)
        if hit > score:
            best, score = item, hit
    return best


# ------------------------------------------------------------------ actions
def _picture(context, params) -> dict:
    """The person's picture the params name; ActionError when it isn't theirs."""
    from core.actions import ActionError

    store = getattr(context, "art", None)
    item = store.get(str(params.get("id") or "")) if store is not None else None
    if item is None:
        raise ActionError("That picture isn't one of yours.")
    return item


def _describe_delete(context, params) -> str:
    """The sentence the approval card shows for `art.delete` (Propose); raises ActionError when it can't be done."""
    return f"Delete the picture of {_picture(context, params)['description'][:60]}"


def _delete(context, params) -> str:
    """Does `art.delete` once approved: off the list (its file kept aside for undo); a theme using it as its backdrop
    just shows none."""
    item = _picture(context, params)
    context.art.remove(item["id"])
    return f"Deleted the picture of {item['description'][:60]}."


def _register() -> None:
    """Adds art.delete to the action system (imported at the end of core/actions.py)."""
    from core.actions import ACTION_TYPES, ActionType

    ACTION_TYPES["art.delete"] = ActionType("art.delete", "Delete", {"id": "one of your pictures"}, _describe_delete,
                                            _delete, child_ok=True)
