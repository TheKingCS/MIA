"""
core.service_map
==================

What MIA runs on, and what depends on what (T-0007; the personality and ecosystem plan's phase 3,
docs/PERSONALITY_AND_ECOSYSTEM_AUDIT.md section C; beside core/self_knowledge.py, which says what she is, this
says what she runs on), so she can answer "if Ollama stops, what breaks?", "what does
the browser need?" and "what am I missing?" from code, never a guess.

- **`SERVICES`**: each service, device or package she relies on (the local model, the embedding and vision models,
  speech in and out, OCR, the reference packs, her browser, private search, the internet, bank sync, the phone, the
  glasses, the greenhouse node, PlatformIO, an email account), what it powers in plain words, what still works
  without it, what it itself needs (`needs`: the embedding model runs in Ollama; bank sync needs the internet), and
  how to tell whether it's here (`check`).
- **The graph**: each service's dependencies as links in core/links.py's own shape (`Link(source, "DEPENDS_ON",
  target, derived=True)`, refs `service:<id>`), walked the way links.downstream walks a life's. Kept apart from the
  life graph on purpose: what MIA runs on isn't part of the person's Life State, and mixing them would fill its
  "what waits on what" with machinery.
- **Checks** look only: an executable on the PATH (`shutil.which`), a Python package installed
  (`importlib.util.find_spec`), a setting or a store on the context. Nothing here starts a process, opens a
  connection or loads a model; connectivity has its own monitor (core/connectivity.py), read when it's there.

Pure logic apart from those looks.
"""

from __future__ import annotations

import importlib.util
import re
import shutil
from dataclasses import dataclass
from typing import Optional

from core.links import Link

HERE, MISSING, UNKNOWN = "here", "missing", "unknown"


@dataclass(frozen=True)
class Service:
    """One thing MIA runs on: its id and name, what it powers, what still works without it, what it needs itself (other
    service ids), and how to check it's here ("which:<exe>", "import:<package>", "attr:<context attribute>",
    "config:<key>", "online", "ocr" or "pio" (their own finders), or "" when it can't be told from here)."""
    id: str
    name: str
    powers: str
    without: str
    needs: tuple[str, ...] = ()
    check: str = ""
    words: tuple[str, ...] = ()


SERVICES: tuple[Service, ...] = (
    Service("ollama", "Ollama (her local model)",
            "conversation and thinking in Talk, phrasing question-plan answers, drafting screens she makes, the "
            "Chronicles' lines and the council",
            "every record and action, quick commands, alarms and reminders, and the question plans said plainly "
            "from their fact sheets", (), "which:ollama", ("ollama", "the model", "her model", "llm", "local model")),
    Service("embeddings", "the embedding model (meaning)", "matching a question to its plan by meaning",
            "matching by each plan's own words, as on the phone", ("ollama",), "",
            ("embedding", "embeddings", "meaning model")),
    Service("vision", "the vision model", "Look: what's in a photo, inspecting a part", "reading a label's words "
            "with OCR, and everything else", ("ollama",), "", ("vision", "vision model", "look", "sight")),
    Service("tesseract", "Tesseract (OCR)", "reading a label or a document's words exactly",
            "Look's description from the vision model", (), "ocr", ("tesseract", "ocr")),
    Service("vosk", "Vosk (listening)", "speech in: talking to her out loud", "typing to her", (), "import:vosk",
            ("vosk", "listening", "speech recognition", "the microphone")),
    Service("piper", "Piper (her voice)", "speech out: her spoken replies and briefings", "her replies as text", (),
            "import:piper", ("piper", "her voice", "speaking", "text to speech")),
    Service("kiwix", "the reference packs (libzim)", "the offline Knowledge library and device help",
            "everything else; the packs copied onto the PC are what she can read", (), "import:libzim",
            ("kiwix", "libzim", "reference packs", "wikipedia", "the library")),
    Service("browser", "her browser (Playwright and Edge)", "browsing for you, with every commit waiting for your OK",
            "Look It Up Online through private search, and everything offline", (), "import:playwright",
            ("browser", "playwright", "edge")),
    Service("internet", "the internet", "the online features: bank sync, phone notifications, new map areas, "
            "trail maps from a link, phone access away from home",
            "everything offline: conversation, voice, every record and action, saved maps, reference packs",
            (), "online", ("internet", "the connection", "wifi", "wi-fi", "online")),
    Service("searxng", "private search (SearXNG)", "Look It Up Online", "her offline sources: the reference packs "
            "and her specialists' notes", ("internet",), "", ("searxng", "search",
                                                                                        "private search")),
    Service("plaid", "bank sync (Plaid)", "syncing bank and card accounts", "the last synced balances and every "
            "entry you make yourself", ("internet",), "import:plaid", ("plaid", "bank sync", "the bank")),
    Service("tailscale", "Tailscale", "reaching MIA from the phone away from home", "the phone on the home network",
            ("internet",), "which:tailscale", ("tailscale", "vpn")),
    Service("phone", "the phone app", "MIA on the phone: talking, checking off, approving", "MIA on this computer",
            (), "", ("phone", "the phone app", "android")),
    Service("glasses", "the glasses", "MIA on the glasses: glances and voice", "the phone and this computer",
            ("phone",), "", ("glasses", "meta glasses", "the display")),
    Service("greenhouse_node", "the greenhouse node", "watching the greenhouse: readings, alerts, the live dashboard",
            "the node itself and its safety MCU keep controlling the greenhouse; MIA just stops hearing from it",
            (), "attr:greenhouse_link.taken_over", ("greenhouse node", "the node", "the greenhouse pi")),
    Service("platformio", "PlatformIO", "flashing the greenhouse's safety MCU from this PC",
            "flashing it from another computer, and everything else", (), "pio",
            ("platformio", "pio", "flashing")),
    Service("email_account", "an email account for MIA", "reading the inbox she sorts, and sending the drafts you "
            "approve with Send", "drafting email (she never sends on her own), and everything else", ("internet",),
            "", ("email", "mail", "smtp", "the inbox")),
)
BY_ID = {s.id: s for s in SERVICES}


def links() -> list[Link]:
    """Pure logic. Each service's dependencies as derived DEPENDS_ON links (refs service:<id>), core/links.py's
    shape."""
    return [Link(f"service:{s.id}", "DEPENDS_ON", f"service:{need}", derived=True) for s in SERVICES for need in s.needs]


def depends_on(service_id: str) -> list[str]:
    """Pure logic. Every service that stops working when this one does, directly or through a chain (the vision
    model when Ollama stops), in the order a walk finds them."""
    waiting: dict[str, list[str]] = {}
    for link in links():
        waiting.setdefault(link.target, []).append(link.source)
    found, queue = [], list(waiting.get(f"service:{service_id}", []))
    while queue:
        ref = queue.pop(0)
        if ref in found:
            continue
        found.append(ref)
        queue += waiting.get(ref, [])
    return [ref.split(":", 1)[1] for ref in found]


def needs_of(service_id: str) -> list[str]:
    """Pure logic. Everything a service needs, directly or through a chain (bank sync: the internet)."""
    out, queue = [], list(BY_ID[service_id].needs) if service_id in BY_ID else []
    while queue:
        need = queue.pop(0)
        if need not in out:
            out.append(need)
            queue += list(BY_ID[need].needs) if need in BY_ID else []
    return out


def find(words: str) -> Optional[Service]:
    """The service the words name (its longest matching word), or None."""
    said = " " + " ".join(str(words or "").lower().split()) + " "
    best, score = None, 0
    for s in SERVICES:
        for w in s.words + (s.id.replace("_", " "),):
            if f" {w} " in said or (len(w) > 4 and w in said):
                if len(w) > score:
                    best, score = s, len(w)
    return best


def status(context, service: Service) -> str:
    """Whether a service is here (HERE, MISSING or UNKNOWN), by looking only: never starting or connecting anything."""
    kind, _, arg = service.check.partition(":")
    try:
        if kind == "which":
            return HERE if shutil.which(arg) else MISSING
        if kind == "import":
            return HERE if importlib.util.find_spec(arg) is not None else MISSING
        if kind == "attr":
            obj = context
            for part in arg.split("."):
                obj = getattr(obj, part, None)
            return HERE if obj else MISSING
        if kind == "config":
            config = getattr(context, "config", None)
            return HERE if config is not None and config.get(arg) else MISSING
        if kind == "ocr":  # its own finder: the setting, the PATH, or Windows' install folder
            from core import ocr

            return HERE if ocr.available(getattr(context, "config", None)) else MISSING
        if kind == "pio":  # its own finder: pio on the PATH, or the Python package
            from core.greenhouse_provision import platformio

            return HERE if platformio() else MISSING
        if kind == "online":
            monitor = getattr(context, "connectivity", None)
            state = getattr(monitor, "status", "unknown") if monitor is not None else "unknown"
            return {"online": HERE, "offline": MISSING}.get(state, UNKNOWN)
    except Exception:
        return UNKNOWN
    return UNKNOWN


def what_breaks(service_id: str) -> str:
    """In words: what stops when a service does (its own work and every service waiting on it) and what still
    works."""
    s = BY_ID[service_id]
    chain = [BY_ID[d] for d in depends_on(service_id)]
    said = f"If {s.name} stops: {s.powers} stop"
    if chain:
        said += "; and with it " + "; ".join(f"{c.name} ({c.powers})" for c in chain)
    return said + f". Still working: {s.without}."


def summary(context) -> str:
    """In words: which services are here and which aren't (the ones that can't be told from here left out)."""
    here, missing = [], []
    for s in SERVICES:
        state = status(context, s)
        (here if state == HERE else missing if state == MISSING else []).append(s.name)
    parts = []
    if here:
        parts.append("Here and ready: " + ", ".join(here) + ".")
    if missing:
        parts.append("Not set up or not running: " + ", ".join(missing) + ".")
    return " ".join(parts) or "I can't tell from here what's running."


_BREAKS = re.compile(r"\bwhat (?:breaks|stops|stops working|happens|goes down) (?:if|when) (.+?)\??$")
_NEEDS = re.compile(r"\bwhat does (.+?) (?:need|depend on|run on)\??$")
_DOWN = re.compile(r"\bwhat (?:are you|am i) missing\b|\bwhat(?:'s| is) (?:not )?(?:running|set up|missing)\b|"
                   r"\bwhat do you run on\b")


def reply(context, text: str) -> Optional[str]:
    """What MIA says, in code, to "what breaks if <a service> stops?", "what does <a service> need?" and "what am
    I missing?" / "what do you run on?"; None when the words aren't for it."""
    said = " ".join(str(text or "").lower().replace("’", "'").split())
    m = _BREAKS.search(said)
    if m:
        s = find(m.group(1))
        return what_breaks(s.id) if s is not None else None
    m = _NEEDS.search(said)
    if m:
        s = find(m.group(1))
        if s is None:
            return None
        needs = [BY_ID[n].name for n in needs_of(s.id)]
        return (f"{s.name[0].upper() + s.name[1:]} needs " + ", ".join(needs) + "." if needs
                else f"{s.name[0].upper() + s.name[1:]} runs on its own, on this computer.")
    if _DOWN.search(said):
        return summary(context)
    return None
