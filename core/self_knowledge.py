"""
core.self_knowledge
=====================

What MIA can honestly say about herself — grounded in real data, never guessed. When the person asks "what are you?",
"what can you do?", "what are you working on?" or "what do you know about me?", her answer should come from the facts
(the system map, her Night School focus, the person's own stored directions and preferences), not from the model
improvising — the same "facts in code, the model only phrases" rule the rest of MIA follows, and the fix for the
self-description drift the capabilities doc warns about.

Each function returns a plain, first-person line or two MIA can speak or build on. `grounding_block()` puts them
into the system message of a how-to question about herself (`about_herself()`, core/assistant_chat.py), so her
spoken answers about herself come from these facts too. Everything is read defensively, so a
missing source is simply left out rather than crashing the answer.

The second half (2026-11-10, docs/CONVERSATION_REVIEW.md) is what she reads when she's asked about herself in
ordinary words: TOPICS is a table of pointers (source files, decisions, apps, live counts), `block_for()` reads
them at that moment into the model's system message with each line's source, `asks_about_her()` tells the turn
a question is hers alone, and `wants_described()` that it's to be answered in conversation, not by a tool. No
description of her is kept here, so none can go stale.
Her own designs too (2026-11-25, the fix report): what her decisions and specs name (`designs_in`, `design_asked`),
so "what is the Life Enrichment Protocol?" is answered from DEC-0161 and its spec, with its status; and the
conversations topic, so "how do I export this chat?" is answered from core/conversation_export.py.
Whether her code builds a design yet (`built_by`); one that nothing builds is said in code as a plan (`plan_reply`),
since the model, told it wasn't built, still called it a subsystem.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

_ABOUT_ME_TTL = 600  # seconds: her scale doesn't change mid-conversation, and reading it takes about half a second
_about_me_cache: dict = {"at": 0.0, "text": ""}

# A question about MIA herself, not about using one of her apps: how she works, learns, remembers, is built, what
# she's working on. "How do you add a bill?" is a how-to about an app, so it's left out.
_ABOUT_HER = re.compile(
    r"\b(?:how (?:do|does|did|can|will) (?:you|mia) (?:work|learn|think|remember|improve|grow|know|decide|get better)"
    r"|what (?:are|is) (?:you|mia) (?:working on|learning|studying|focused on|made of|built (?:on|from|with))"
    r"|how (?:are|is) (?:you|mia) (?:built|made|trained|learning|improving)"
    r"|(?:your|mia's) (?:memory|brain|model|training|focus|night school|loops|code|architecture|own code)"
    r"|(?:do|can|does) (?:you|mia) (?:learn|remember|think|improve|grow|train|get smarter))\b",
    re.IGNORECASE)


def _safe(fn, default=""):
    """Run a reader; on any failure return the default so a self-answer never crashes."""
    try:
        return fn()
    except Exception:  # noqa: BLE001 - a missing source is a quiet gap, not an error
        return default


def about_me() -> str:
    """A grounded, first-person description of what MIA is — the real scale, from the system map (DEC-0139)."""
    from core import system_map

    d = system_map.assemble()
    arch = d.get("architecture", {})
    files = sum(arch.values()) if arch else 0
    tools = d.get("capabilities", {}).get("tools")
    loops = d.get("loops", {}).get("active")
    decisions = len(d.get("decisions", []))
    sealed = d.get("stores", {}).get("sealed")
    parts = ["I'm MIA — a local-first personal assistant that runs on your own devices, so what I keep about you stays "
             "with you."]
    if files:
        detail = f"Under the hood I'm about {files} files of code"
        if tools:
            detail += f", roughly {tools} tools"
        if loops:
            detail += f", and {loops} improvement loops that watch how I work and push me to get better"
        parts.append(detail + ".")
    if decisions:
        parts.append(f"There are {decisions} decisions on record for why I'm built the way I am"
                     + (f", and {sealed} of the things I keep about you are encrypted on disk" if sealed else "") + ".")
    return " ".join(parts)


def my_focus() -> str:
    """What MIA is working on right now — her Night School directive (DEC-0100), or her build plan."""
    from core import night_school

    directive = _safe(lambda: night_school.settings().get("directive"), "")
    if directive:
        return "What I'm working on right now, every night: " + directive
    return "Right now I work through my build plan step by step each night, with a teacher setting my exercises."


def what_i_know_about_you(context) -> str:
    """A grounded sketch of what MIA understands about the person — from their stored directions and the picture of
    them (core/picture_of_you.py: memories by category, skills, learning, answer style). Honest about how much (or
    little) she knows."""
    bits = []
    book = getattr(context, "direction", None)
    live = _safe(lambda: book.active(), []) if book is not None else []
    if live:
        bits.append("You're steering your life by: " + "; ".join(d.title for d in live) + ".")
    from core import picture_of_you  # what she remembers, his skills, learning and answer style (DEC-0290)

    picture = _safe(lambda: picture_of_you.say(context), "")
    if picture and not picture.startswith("I don't hold much"):
        bits.append(picture)
    return " ".join(bits) or "Honestly, I'm still getting to know you — tell me what matters, and I'll remember."


def self_summary(context) -> str:
    """The three together: what she is, what she's working on, and what she knows about the person."""
    return "\n\n".join([about_me(), my_focus(), what_i_know_about_you(context)])


def about_herself(prompt: str) -> bool:
    """Pure logic. Whether a question is about MIA herself (how she works, learns, remembers, is built, what she's
    working on), as opposed to how to use one of her apps."""
    return bool(_ABOUT_HER.search(prompt or ""))


def _about_me_kept() -> str:
    """`about_me()` kept for _ABOUT_ME_TTL, for answers inside a turn (reading it takes about half a second); a
    failure isn't kept, so the next question tries again. The About page reads `about_me()` live."""
    if _about_me_cache["text"] and time.monotonic() - _about_me_cache["at"] < _ABOUT_ME_TTL:
        return _about_me_cache["text"]
    text = _safe(about_me)
    if text:
        _about_me_cache.update(at=time.monotonic(), text=text)
    return text


def grounding_block(context) -> str:
    """Her own facts for a how-to question about herself (DEC-0142), so the answer comes from the records rather than
    the model improvising about itself: what she is, what she's working on, and what she knows about the person. ""
    when nothing can be read."""
    facts = [x for x in (_about_me_kept(), _safe(my_focus), _safe(lambda: what_i_know_about_you(context))) if x]
    if not facts:
        return ""
    return ("What's true about you, from your own records. Answer about yourself from these, never from a guess:\n"
            + "\n".join(f"- {x}" for x in facts))


# ------------------------------------------------- her own records, read when she's asked (docs/CONVERSATION_REVIEW.md)
#
# Nothing below describes MIA. A Topic says what a person may ask about her and *where the answer is kept*: source
# files (their opening description is read), decisions (read from docs/DECISIONS.md with their status), apps (read
# from the registry with their status and limit) and live readers (counted from the records). So when the code or a
# decision changes, her answer changes with it, and a pointer that no longer exists fails a test instead of going
# stale (tests/test_self_knowledge.py).

ROOT = Path(__file__).resolve().parent.parent
BLOCK_CHARS = 3800  # the most of her own records one question brings into the model's turn
_FILE_CHARS = 420  # of one file's opening description
_DECISION_CHARS = 300  # of one decision
_opening_cache: dict = {}

_LEAD = r"(?:(?:so|and|ok|okay|hey|well|now|mia|please)[, ]+)*"
_HER = re.compile(r"\b(?:you|your|yours|yourself|you're|mia|mia's|we|our)\b")
_QUESTION = re.compile(r"^" + _LEAD + r"(?:what|what's|whats|how|when|where|why|who|which|do|does|did|is|are|was|were"
                       r"|can|could|tell|explain|describe)\b")
# "Can you show the list on my glasses?" asks her to do something; "can you tell me about..." asks about her.
_DOING = re.compile(r"^" + _LEAD + r"(?:can|could|will|would) you (?!tell|explain|describe|say|hear|learn|remember)")
# A question put to her about herself or what she has, as opposed to one about the person's own records.
_ABOUT_FORM = re.compile(
    r"^" + _LEAD + r"(?:do you (?:have|know about|know how|support|use|work with|include|come with)"
    r"|does mia (?:have|support|work with)|tell me (?:more )?about (?:your|how you|mia's)|what(?:'s| is| are) your"
    r"|how (?:do|does|did|can|would) (?:you|mia)\b|what (?:\w+ ){0,3}(?:can|do) you\b|explain (?:your|how you)"
    r"|describe (?:your|how you)|(?:can|could) you (?:tell me about|explain|describe))")
_DEFINE = re.compile(r"^" + _LEAD + r"what(?:'s| is| are) (?:the |a |an |your |mia's )?(.+?)\s*\??$")
_APP_WORD = re.compile(r"\b(?:app|apps|application|applications|module|modules|screen|page|feature)\b")
_RETIRED = re.compile(r"\b(?:not in use|no longer (?:used|in use)|retired|superseded|deprecated|replaced by)\b", re.I)
_APP_LIST = re.compile(r"\b(?:apps|applications|modules)\b")


@dataclass(frozen=True)
class Topic:
    """One thing a person may ask MIA about herself, and where its answer is kept. `asks` is matched on the lowered
    message; `files`, `decisions` and `apps` are pointers read when it's asked; `live` names reader functions here.
    `hers` is for a question only her own records can answer (her history, limits, design): the person's plans and
    lookups stand aside for it. `gate` is for a plain word ("glasses") that only counts in a question or with "you"."""

    name: str
    asks: "re.Pattern"
    files: tuple = ()
    decisions: tuple = ()
    apps: tuple = ()
    live: tuple = ()
    hers: bool = False
    gate: bool = False


def _t(name: str, asks: str, **kept) -> Topic:
    """A Topic with its pattern compiled."""
    return Topic(name, re.compile(asks), **kept)


TOPICS: tuple = (
    _t("history",
       r"\bhow (?:you|mia) (?:were|was|got|came to be) (?:created|made|built|born|developed|started)?"
       r"|\b(?:how|when|where|why) (?:were|was|did) (?:you|mia) (?:\w+ )?(?:created|made|built|born|developed|start|begin|come)"
       r"|\b(?:your|mia's) (?:own )?(?:development|creation|origins?|history|beginnings?|earliest|first (?:record|commit|version|days?)"
       r"|story|evolution|milestones)\b"
       r"|\bearliest record\b|\bwho (?:made|built|created|designed|develops?|is building) (?:you|mia)\b"
       r"|\bhow (?:has|have) (?:your|you|mia)\b.*\b(?:evolved|changed|grown)\b|\bhow old are you\b",
       files=("core/dev_history.py", "docs/COLLABORATION.md", "core/dev_evolution.py"), live=("_history_facts",),
       hers=True),
    _t("limits",
       r"\b(?:your|mia's) (?:\w+ )?(?:limitations?|limits|weakness(?:es)?|shortcomings|blind spots)\b"
       r"|\bwhat (?:can't|cannot|can not) (?:you|mia) do\b|\bwhat are you (?:bad|not good) at\b",
       decisions=("DEC-0151", "DEC-0053", "DEC-0058"), apps=("issues",), live=("_limit_facts",), hers=True),
    _t("direction",
       r"\bwhat (?:are|is) (?:we|you|mia) (?:\w+ )?working (?:on|toward|towards)\b"
       r"|\bwhat(?:'s| is) next for (?:you|us|mia)\b"
       r"|\b(?:your|our|mia's) (?:\w+ )?(?:roadmap|next steps?|current focus|build plan)\b",
       files=("docs/CURRENT_STATE.md",), live=("_direction_facts",), hers=True),
    _t("architecture",
       r"\b(?:your|mia's) (?:own )?(?:architecture|code|codebase|source code|brain|engine|internals)\b"
       r"|\bhow (?:are|were|is|was) (?:you|mia) (?:built|made|designed|structured|put together)\b"
       r"|\bwhat (?:are|is) (?:you|mia) (?:made of|built (?:on|from|with)|written in)\b"
       r"|\bhow (?:do|does) (?:you|mia) (?:actually )?work\b(?! (?:with|on|for|in))|\bunder the hood\b",
       files=("docs/ARCHITECTURE.md", "core/system_map.py", "core/assistant_turn.py"), decisions=("DEC-0139", "DEC-0151"),
       live=("_architecture_facts",), hers=True),
    _t("learning",
       r"\bhow (?:do|does|can|will|did) (?:you|mia) (?:learn|improve|get better|get smarter|grow)"
       r"(?: yourself| over time| on your own| new things| from .*)?\s*[?.!]*$"
       r"|\b(?:your|mia's) (?:own )?(?:feedback|mistakes|learning|self[- ]improvement|improvement loops?)\b"
       r"|\bthumbs?[- ](?:up|down)\b|\bfix-?it log\b|\bnight school\b|\bwhen i (?:correct|rate) you\b"
       r"|\b(?:do|can) you learn\b",
       files=("core/failure_log.py", "core/response_style.py", "core/night_school.py", "core/loops.py"),
       decisions=("DEC-0049", "DEC-0138", "DEC-0100", "DEC-0058"), apps=("issues",), live=("_learning_facts",),
       hers=True, gate=True),
    _t("memory",
       r"\bhow (?:do|does|will|can) (?:you|mia) remember\b|\b(?:your|mia's) (?:own )?(?:memory|memories|context window)\b"
       r"|\bwhat do you (?:remember|know) about me\b|\bhow (?:much|long) (?:do|can) you remember\b",
       files=("core/conversation_state.py", "core/user_memory_manager.py", "core/life_notes.py"),
       decisions=("DEC-0054", "DEC-0052"), live=("_memory_facts",)),
    _t("voice",
       r"\bhow (?:do|does|can) (?:you|mia) (?:hear|listen|speak|talk)\b"
       r"|\b(?:your|mia's) (?:voice|microphone|mic|wake word|speech)\b|\bhow (?:do|can) i talk to (?:you|mia)\b"
       r"|\bcan you hear me\b|\b(?:conversation|command) mode\b",
       files=("core/voice_loop.py", "core/web_voice.py", "core/glasses_voice.py", "core/voice_manager.py")),
    _t("glasses", r"\b(?:glasses|ray-?bans?)\b",
       files=("core/glasses.py", "core/glasses_voice.py",
              "android-phone/app/src/main/java/com/mia/phone/GlassesCamera.kt",
              "android-phone/app/src/main/java/com/mia/phone/MetaGlasses.kt"),
       decisions=("DEC-0062", "DEC-0063", "DEC-0066"), apps=("sight",), live=("_glasses_facts",), gate=True),
    _t("chronicle", r"\bchronicles?\b",
       files=("core/chronicle_issue.py",), decisions=("DEC-0084", "DEC-0086"),
       live=("_two_chronicles", "_chronicle_facts"), gate=True),
    _t("devices",
       r"^(?=.*\b(?:discover|detect|find|connect|scan|support|control|work with|pair|read|see|know about|talk to)\b)"
       r".*\b(?:devices?|hardware|sensors?|usb|serial|bluetooth|wi-?fi|network|arduino|esp32|microcontrollers?)\b",
       files=("core/sensors.py", "core/device_framework.py"), apps=("field_kit", "security", "power"),
       live=("_device_facts",), gate=True),
    # Taking a conversation out of the chat: export, copy, summary (the fix report: "how do I copy this whole chat?"
    # was answered with a browser's select-all; the commands and the Copy button are core/conversation_export.py's).
    _t("conversations",
       r"\b(?:export|save|copy|download|send|share|print|back up|summari[sz]e)\b[^.?!]*\b(?:chat|conversation|"
       r"transcript)(?: logs?| history)?s?\b",
       files=("core/conversation_export.py",)),
    _t("greenhouse", r"\b(?:greenhouse|aquaponics|homestead)\b",
       files=("core/greenhouse_link.py", "core/homestead_manager.py"), decisions=("DEC-0150", "DEC-0145"),
       apps=("greenhouse",), live=("_greenhouse_facts",), gate=True),
)


# MIA's own designs: what her decisions and specs name ("the Life Enrichment Protocol", "Smart Closet"), so "what is
# the Life Enrichment Protocol?" is answered from DEC-0161 and its spec, read when asked, with its status (the fix
# report: she said she had no such thing). A decision names its subject before " is ", ":" or a dash; a spec by its
# file name. Read again after ten minutes.
_DECISION_HEAD = re.compile(r"^### (DEC-\d{4}): (.+)$", re.M)
_SUBJECT_END = re.compile(r"\s+(?:is|are|was|becomes|gets|stays|goes|has|keeps|holds|works|lets|takes|runs)\s+|:\s|"
                          r"\s[-—]\s|\s\(")
_designs_cache: dict = {"at": 0.0, "found": None}


def _designs() -> dict:
    """{name (lowered, no leading "the"): {"decisions": [...], "spec": "docs/specs/X.md" or ""}} from docs/DECISIONS.md's
    headings and docs/specs' file names; subjects of two to six words only, so a long sentence isn't a name.
    Only proper names count from a decision's heading ("Smart Closet", never "Least privilege"), each kept with its
    own spelling."""
    now = time.monotonic()
    if _designs_cache["found"] is not None and now - _designs_cache["at"] < 600:
        return _designs_cache["found"]
    found: dict = {}
    try:
        text = (ROOT / "docs" / "DECISIONS.md").read_text(encoding="utf-8", errors="replace")
    except OSError:
        text = ""
    for dec, title in _DECISION_HEAD.findall(text):
        said = re.sub(r"^(?:The|A|An)\s+", "", _SUBJECT_END.split(title.strip(), maxsplit=1)[0].strip()).strip(" .,;")
        words = said.split()
        # A name of hers, written as one ("Life Enrichment Protocol", "Smart Closet"): every word capitalized but the
        # small ones; never a phrase ("Least privilege", "critical path", "her face": the third review, 2026-11-25).
        proper = all(w[:1].isupper() or w.lower() in ("of", "and", "the", "for", "a", "an", "in", "on", "to")
                     for w in words) and words and words[0][:1].isupper()
        subject = said.lower()
        if proper and 2 <= len(words) <= 6 and not re.search(r"\b(?:mia|claude|zac|we|he|she|it|they)\b", subject):
            found.setdefault(subject, {"decisions": [], "spec": "", "name": said})["decisions"].append(dec)
    for spec in sorted((ROOT / "docs" / "specs").glob("*.md")):
        name = spec.stem.lower().replace("_", " ")
        if 2 <= len(name.split()) <= 6:
            found.setdefault(name, {"decisions": [], "spec": "", "name": name.title()})["spec"] = f"docs/specs/{spec.name}"
    _designs_cache.update(at=now, found=found)
    return found


def designs_in(text: str) -> list:
    """Pure logic, with her documents. The designs a lowered message names, longest first, two at most:
    [(name, {"decisions", "spec"})]."""
    said = f" {_norm(text)} "
    named = [(n, d) for n, d in _designs().items() if re.search(rf"(?<![\w-]){re.escape(n)}(?![\w-])", said)]
    return sorted(named, key=lambda x: len(x[0]), reverse=True)[:2]


def built_by(name: str) -> str:
    """Pure logic, with her code. The core file that builds a design of hers ("smart closet": core/smart_closet.py,
    or a file whose opening names it), or "" when nothing does yet."""
    stem = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    if (ROOT / "core" / f"{stem}.py").exists():
        return f"core/{stem}.py"
    for path in sorted((ROOT / "core").glob("*.py")):
        if name.lower() in _opening(f"core/{path.name}", 1500).lower():
            return f"core/{path.name}"
    return ""


def plan_reply(prompt: str) -> Optional[str]:
    """In code: "what is the Life Enrichment Protocol?" about a design of hers nothing builds yet. That it's a plan,
    not something she can do now, then what it's for, from its decision, said to him ("you", "my"); None for a design
    that's built (the model describes it from her records) or a question that isn't one (live check, 2026-11-25: told
    it wasn't built, the model still called it "a major MIA subsystem").
    Only a design its own decision calls a plan (a direction, proposed, planned); any other is the model's, with her
    records."""
    from core import self_docs

    found = design_asked(_norm(prompt))
    if len(found) != 1 or built_by(found[0][0]):
        return None
    name, design = found[0]
    decision = _safe(lambda: self_docs.decision(design["decisions"][0], 600), None) if design["decisions"] else None
    # Only a design its own decision calls a plan (a direction, proposed, planned): any other is left to the model
    # with her records, never called unbuilt on a guess (the third review: built features were called plans).
    if not re.search(r"\b(?:direction|proposed|planned|plan|not built|future)\b",
                     str((decision or {}).get("status", "")).lower()):
        return None
    proper = design.get("name") or name
    gist = re.sub(r"\s+", " ", str((decision or {}).get("gist", ""))).strip()
    first = re.split(r"(?<=[.!?])\s", gist, maxsplit=1)[0] if gist else ""
    first = re.sub(r"\bthe person's\b", "your", re.sub(r"\bthe person\b", "you", first))
    first = re.sub(r"\bMIA's\b", "my", first)
    status = (decision or {}).get("status", "").lower()
    where = (f" It's approved as a direction ({design['decisions'][0]})" if "approved" in status
             else f" It's proposed ({design['decisions'][0]})" if design["decisions"] else " It's written up")
    where += f", and its plan is in {design['spec']}." if design["spec"] else "."
    return (f"The {proper} is one of my plans, not something I can do yet. " + (first + " " if first else "")
            + where.strip())


_TELL_ABOUT = re.compile(r"^(?:tell me (?:more )?about|what do you know about|explain|describe)\s+(.+?)\s*\??$")


def design_asked(text: str) -> list:
    """Pure logic, with her documents. The designs a lowered message asks her to describe: one that's the whole subject
    of "what is ...?" or "tell me about ..." ("what is the Life Enrichment Protocol?"), exactly; never with "my" or
    anything else beside it, and never a design's words in passing."""
    defined = _DEFINE.match(text) or _TELL_ABOUT.match(text)
    if not defined:
        return []
    rest = re.sub(r"^(?:the|a|an|your|mia's)\s+", "", defined.group(1).strip(" ?.!"))
    return [(n, d) for n, d in designs_in(rest) if n == rest]  # the design is exactly what's asked about


def _norm(prompt: str) -> str:
    """A message lowered, with typed apostrophes made plain, for matching."""
    return (prompt or "").lower().replace("’", "'").strip()


def topics_for(prompt: str) -> list:
    """Pure logic. The topics about herself a message touches, in TOPICS order. A gated topic's plain word only
    counts in a question or beside "you"/"your"/"MIA"."""
    text = _norm(prompt)
    if not text:
        return []
    gated = bool(_HER.search(text) or _QUESTION.match(text))
    return [t for t in TOPICS if (gated or not t.gate) and t.asks.search(text)]


def asks_about_her(prompt: str) -> bool:
    """Pure logic. Whether a message is a question only MIA's own records can answer (her history, her limits, what
    she's being built toward, her design, how she learns). The turn then leaves the person's question plans and
    lookups aside (core/assistant_turn.py): "when did your development begin?" isn't about their progress. One of
    her own designs as the subject ("what's the smart closet?", `design_asked`) is hers too; "what's in my smart
    closet?" isn't."""
    text = _norm(prompt)
    if not text or not _QUESTION.match(text) or _DOING.match(text):
        return False
    return any(t.hers for t in topics_for(text)) or bool(design_asked(text))


def _apps_named(context, text: str) -> list:
    """The apps a lowered message names (by their own name in the registry, beside "app", "screen" or "page"), two at
    most."""
    if not _APP_WORD.search(text):
        return []
    from core import capabilities

    found = []
    for app in _safe(lambda: capabilities.capability_map(context), []):
        name = app.get("name", "").lower()
        name = name[4:] if name.startswith("the ") else name
        if (not name or app.get("where") == "retired" or _APP_WORD.fullmatch(name)
                or not re.search(r"\b" + re.escape(name) + r"\b", text)):
            continue
        found.append(app)
    return found[:2]


def _lists_apps(text: str) -> bool:
    """Whether a lowered message asks her which apps she has ("what apps do you have?")."""
    return bool(_APP_LIST.search(text) and _HER.search(text) and _QUESTION.match(text))


def wants_described(context, prompt: str) -> bool:
    """Whether a message asks MIA to describe herself or something she has ("do you have a greenhouse app?", "what is
    the Chronicle?", "how do you work with my glasses?") rather than to look up or change the person's records, so
    the turn answers it in conversation with her own records beside it instead of handing it to a tool. "What's X"
    names an app only when X is the app ("what's the greenhouse app?"), never when it ends with one ("what's due in
    the greenhouse?"). One of her own designs as the subject ("what is the Life Enrichment Protocol?",
    `designs_in`) is hers to describe too."""
    text = _norm(prompt)
    if not text or _DOING.match(text):
        return False
    if asks_about_her(prompt):
        return True
    if design_asked(text):
        return True  # "what is the Life Enrichment Protocol?": one of her own designs is what's asked about
    topics, apps = topics_for(text), _apps_named(context, text)
    if not topics and not apps:
        return _lists_apps(text) and bool(_ABOUT_FORM.match(text))
    if _ABOUT_FORM.match(text):
        return True
    defined = _DEFINE.match(text)
    if not defined:
        return False
    rest = defined.group(1)
    for t in topics:
        found = t.asks.search(rest)
        if found and found.start() == 0 and found.end() == len(rest):  # the topic is the whole subject
            return True
    # the app is the whole subject ("what's the greenhouse", "what is the greenhouse app"), never only its last word
    # ("what's due in the greenhouse?" asks about his greenhouse's upkeep, not the app)
    return any(re.fullmatch(rf"{re.escape(a.get('name', '').lower())}(?:\s+{_APP_WORD.pattern})?", rest)
               or (_APP_WORD.search(rest) and a.get("name", "").lower() in rest) for a in apps)


def _cut(text: str, chars: int) -> str:
    """Text within `chars`, ended at a sentence when one ends in the second half, else at a word."""
    text = " ".join((text or "").split())
    if len(text) <= chars:
        return text
    head = text[:chars]
    stop = max(head.rfind(". "), head.rfind("; "))
    return head[:stop + 1] if stop > chars // 2 else head.rsplit(" ", 1)[0] + "…"


def _status_first(body: str) -> str:
    """A description with any sentence saying the thing is no longer in use moved to the front, so a cut never
    drops the one sentence that changes what the rest means."""
    sentences = re.split(r"(?<=[.!?]) +", body)
    retired = [s for s in sentences if _RETIRED.search(s)]
    return " ".join(retired + [s for s in sentences if s not in retired]) if retired else body


def _opening(rel: str, chars: int = _FILE_CHARS) -> str:
    """What a file says it is, in its own opening words: a Python file's opening docstring, a Kotlin file's first
    doc comment, a Markdown file's first paragraphs (after any note about the document itself). Kept until the
    file changes; "" when it can't be read.
    An HTML comment at the top of a document is skipped too."""
    path = ROOT / rel
    try:
        stamp = path.stat().st_mtime
    except OSError:
        return ""
    kept = _opening_cache.get(rel)
    if kept and kept[0] == stamp:
        return _cut(kept[1], chars)
    try:
        text = path.read_text(encoding="utf-8", errors="replace")[:12000]
    except OSError:
        return ""
    if rel.endswith(".py"):
        found = re.search(r"^\s*(?:\"\"\"|''')(.*?)(?:\"\"\"|''')", text, re.S)
        body = re.sub(r"^\s*[\w.]+\s*\n\s*=+\s*\n", "", found.group(1)) if found else ""
    elif rel.endswith(".kt"):
        found = re.search(r"/\*\*(.*?)\*/", text, re.S)
        body = re.sub(r"^\s*\*\s?", "", found.group(1), flags=re.M) if found else ""
    else:
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        # Headings, tables, quoted "see also" notes, HTML comments and an italic note about the document itself say
        # nothing of what it holds.
        said = [p for p in paragraphs if not p.startswith(("#", "```", "|", "---", ">", "<!--"))
                and not re.fullmatch(r"\*[^*].*[^*]\*", p, re.S)]
        body = " ".join(re.sub(r"\*\*|__", "", p).strip("*_ ") for p in said)
    body = _status_first(" ".join(body.split()))
    _opening_cache[rel] = (stamp, body[:1500])
    return _cut(body, chars)


def _decision_line(dec_id: str, chars: int = _DECISION_CHARS) -> str:
    """One decision as a line with its status, read from docs/DECISIONS.md; "" when there's no such decision."""
    from core import self_docs

    found = _safe(lambda: self_docs.decision(dec_id, chars), None)
    if not found:
        return ""
    return f"[decision {found['id']}, {found['status'] or 'no status'}] {found['title']}: {found['gist']}"


def _app_line(app: dict, state: dict) -> str:
    """One app as the registry has it: whether it works, what it's for, what she can do there, its limit, where it
    opens."""
    status = state.get("status") or "listed"
    line = f"[app registry, {status}] {app['name']}: {app.get('what', '').rstrip('.')}."
    if state.get("why") and status != "implemented":
        line += f" ({state['why']}.)"
    tools = [t.replace("_", " ") for t in list(app.get("look_up", [])) + list(app.get("change", []))]
    if tools:
        line += " When asked I can: " + ", ".join(tools[:6]) + (" and more." if len(tools) > 6 else ".")
    if app.get("limits"):
        line += " Limit: " + app["limits"].rstrip(".") + "."
    return line + f" Opens on: {app.get('where', 'this device')}."


def _app_lines(context, ids=(), apps=()) -> list:
    """Registry lines for the given app ids and already-found apps, each app once."""
    from core import capabilities

    rows = {a["id"]: a for a in _safe(lambda: capabilities.capability_map(context), [])}
    states = {s["id"]: s for s in _safe(lambda: capabilities.capability_status(context), [])}
    wanted = [rows[i] for i in ids if i in rows] + [a for a in apps if a.get("id") not in ids]
    return [_app_line(a, states.get(a["id"], {})) for a in wanted]


def _history_facts(context) -> list:
    """Her development, counted from the history she keeps (core/dev_history.py): the earliest commit she can read,
    how the work has gone month by month, and the first and latest decision. Never a person's name."""
    from core import dev_evolution, dev_history

    out = []
    commits = [r for r in _safe(lambda: dev_history.records(("commit",)), []) if dev_history.when(r)]
    if commits:
        first, last = min(commits, key=dev_history.when), max(commits, key=dev_history.when)
        out.append(f"[my commit log] The earliest record of my development I can read is a code commit on "
                   f"{dev_history.when(first)[:10]}: \"{first.get('title', '')}\". Nothing before that date is in my "
                   "records, so how the idea began before then is something I don't know.")
        out.append(f"[my commit log] {len(commits)} commits are on record since then; the latest I've read in is from "
                   f"{dev_history.when(last)[:10]}.")
    months = _safe(lambda: dev_evolution.timeline().get("months", []), [])
    if months:
        out.append("[my commit log and decisions] Work by month: " + "; ".join(
            f"{m['month']}: {m.get('commits', 0)} commits, {m.get('decisions', 0)} decisions" for m in months) + ".")
    decisions = sorted(_safe(lambda: dev_history.records(("decision",)), []), key=lambda r: r.get("ref", ""))
    if decisions:
        out.append(f"[my decisions] {len(decisions)} decisions are on record, from {decisions[0].get('ref')} "
                   f"\"{decisions[0].get('title', '')}\" to {decisions[-1].get('ref')} \"{decisions[-1].get('title', '')}\".")
    return out


def _two_chronicles(context) -> list:
    """The two different things called "Chronicle", each in its own file's words, so one is never taken for the
    other."""
    mine, theirs = _opening("core/saga.py", 330), _opening("core/chronicle.py", 260)
    if not mine or not theirs:
        return []
    return ["[my code: two different things are called \"Chronicle\"] One is about me (core/saga.py): " + mine
            + " The other is about the person (core/chronicle.py): " + theirs
            + " Asked what \"the Chronicle\" is, name both and say which is which."]


def _chronicle_facts(context) -> list:
    """How much the Chronicle Archive (the story of how she was built, core/saga.py) holds right now."""
    from core import saga

    count = _safe(lambda: len(saga.events()), None)
    if count is None:
        return []
    if not count:
        return ["[my chronicle archive, counted now] The archive of my own story is built, but it holds no accepted "
                "events yet: nothing has been written into it."]
    return [f"[my chronicle archive, counted now] The archive of my own story holds {count} accepted "
            f"event{'s' if count != 1 else ''}."]


def _model_fact(context) -> str:
    """Which local model she's set to think with, from her settings, and what that means for facts about the world."""
    config = getattr(context, "config", None)
    model = _safe(lambda: config.get("llm.model"), "") if config is not None else ""
    return (f"[my settings] I think with a local language model{f' ({model})' if model else ''} on your own computer. "
            "What I say about the wider world comes from that model's memory, not a live source, so it can be wrong "
            "or out of date; what I say about your life comes from your records.")


def _limit_facts(context) -> list:
    """Her limits as the records have them: what's working, what doesn't work on the phone, the model she thinks
    with, what she runs on that isn't set up on this computer (looked at now), and what people asked for that
    she couldn't do."""
    from core import capabilities, capability_gaps, service_map

    out = [f"[app registry] {x}" for x in [_safe(lambda: capabilities.status_summary(context))] if x]
    for here in ("phone",):  # the glasses have their own topic
        rows = _safe(lambda: capabilities.capability_status(context, here=here), [])
        away = [r["name"] for r in rows if r.get("status") == "unavailable here"]
        if away:
            out.append(f"[app registry] Not available on the {here}: " + ", ".join(away[:12])
                       + (f" and {len(away) - 12} more" if len(away) > 12 else "") + ".")
        partial = [r["name"] for r in rows if r.get("status") not in ("implemented", "unavailable here")]
        if partial and here == "phone":
            out.append("[app registry] Not fully working: " + ", ".join(partial[:10]) + ".")
    out.append(_model_fact(context))
    missing = [s.name for s in service_map.SERVICES
               if _safe(lambda s=s: service_map.status(context, s)) == service_map.MISSING]
    if missing:
        out.append("[what I run on, checked now] Not set up or not running on this computer, so what needs them "
                   "doesn't work yet: " + ", ".join(missing) + ".")
    gaps = _safe(lambda: capability_gaps.summary(context), {})
    if gaps.get("gaps"):
        out.append(f"[my list of what I couldn't do] {gaps['gaps']} request{'s' if gaps['gaps'] != 1 else ''} I had no "
                   f"way to do; {gaps.get('repeated', 0)} asked more than once.")
    return out


def _direction_facts(context) -> list:
    """What she's being built toward right now: her nightly focus, and the latest decisions on record."""
    from core import dev_history

    out = [f"[my night school: the standing instruction I was given for my own nightly work, worded to me] {x}"
           for x in [_safe(my_focus)] if x]
    decisions = sorted(_safe(lambda: dev_history.records(("decision",)), []), key=lambda r: r.get("ref", ""))[-4:]
    if decisions:
        out.append("[my decisions] The latest decisions about me: " + "; ".join(
            f"{d.get('ref')} \"{d.get('title', '')}\" ({d.get('status', 'no status')})" for d in decisions) + ".")
    return out


def _architecture_facts(context) -> list:
    """Her real scale, from the system map, and the model she thinks with."""
    return [f"[my system map] {x}" for x in [_about_me_kept()] if x] + [_model_fact(context)]


def _learning_facts(context) -> list:
    """How much feedback she's holding right now: the problems noted in the Fix-It Log this month, and the answers
    rated."""
    out = []
    book = getattr(context, "failures", None)
    issues = _safe(lambda: book.issues(30), None) if book is not None else None
    if issues is not None:
        out.append(f"[my Fix-It Log, counted now] {len(issues)} kind{'s' if len(issues) != 1 else ''} of problem noted "
                   "in the last 30 days. I note and group them; changing my code is my developers' job, tested before "
                   "it ships, never mine.")
    out.append("[how feedback reaches me] A thumbs down, \"that's wrong\", a rephrased question or a quick undo is "
               "noted against the answer it was about. Nothing in that changes my character or values.")
    return out


def _memory_facts(context) -> list:
    """What she holds of a conversation word for word, and what she knows about the person."""
    from core import assistant_chat

    kept = _safe(lambda: assistant_chat._MAX_HISTORY_MESSAGES, 0)
    out = []
    if kept:
        out.append(f"[my code, core/assistant_chat.py] In a conversation I hold the last {kept} messages word for "
                   "word, plus a list of what you asked before those. Older wording I don't have.")
    known = _safe(lambda: what_i_know_about_you(context))
    return out + ([f"[your records] {known}"] if known else [])


def _glasses_facts(context) -> list:
    """Which of her apps work on the glasses, from the registry."""
    from core import capabilities

    rows = _safe(lambda: capabilities.capability_status(context, here="glasses"), [])
    if not rows:
        return []
    away = [r["name"] for r in rows if r.get("status") == "unavailable here"]
    return [f"[app registry] On the glasses {len(rows) - len(away)} of my {len(rows)} apps are available"
            + (("; not there: " + ", ".join(away[:10]) + (" and more" if len(away) > 10 else "")) if away else "") + "."]


def _device_facts(context) -> list:
    """What she can find on her own, in the words of the functions that do it: what's plugged into the computer
    (and, checked now, whether the storage half can run here), and the port scan of one address. Nothing of hers
    searches the network for devices, and she says so."""
    import inspect
    import shutil

    from core import device_framework, port_scanner

    def said(fn) -> str:
        """A function's own docstring on one line."""
        return " ".join((inspect.getdoc(fn) or "").split())

    out = []
    storage, serial = said(device_framework.list_block_devices), said(device_framework.list_serial_devices)
    if storage and serial:
        out.append("[my code, core/device_framework.py] What I find on my own is what's plugged into this computer. "
                   f"Storage: {_cut(storage, 160)} Serial boards: {_cut(serial, 160)}")
        if shutil.which("lsblk") is None:
            out.append("[this computer, checked now] The storage check runs lsblk, which this computer doesn't have, "
                       "so here I only find serial boards, not drives or cards.")
    scan = said(port_scanner.scan_ports)
    if scan:
        out.append("[my code, core/port_scanner.py] On the network I have one tool, a port scan of one address I'm "
                   f"given: {_cut(scan, 200)} Nothing of mine searches the network for devices: a sensor there "
                   "sends its readings to me, I don't go and find it.")
    return out


def _greenhouse_facts(context) -> list:
    """Whether she's watching a greenhouse node right now, from the link itself."""
    from core import greenhouse_link

    link = getattr(context, "greenhouse_link", None)
    if link is None:
        return []
    if getattr(link, "taken_over", False) and getattr(link, "state", None):
        return ["[greenhouse link, live] I'm watching the greenhouse node now: "
                + _safe(lambda: greenhouse_link.status_line(link.state))]
    return ["[greenhouse link, live] I'm not connected to a greenhouse node right now, so I have no live readings "
            "from one. Watching it is built; it starts when you tell me to take over the greenhouse."]


def block_for(context, prompt: str) -> str:
    """Her own records on what a message asks about her, for the model's system message: the matched topics' live
    facts, then the apps, the decisions with their status, and the opening words of the source files, every line
    saying where it comes from. Whole lines only, within BLOCK_CHARS. "" when the message isn't about her. A design
    of hers named in a question (`designs_in`) brings whether her code builds it yet (`built_by`), its decisions and
    its spec."""
    text = _norm(prompt)
    if not text or _DOING.match(text):  # "can you show the list on my glasses?" is a thing to do
        return ""
    topics, apps = topics_for(text), _apps_named(context, text)
    designs = design_asked(text)
    if not topics and not apps and not designs and not _lists_apps(text):
        return ""
    each = 3 if len(topics) <= 1 else 2
    live, app_ids, files, decisions = [], [], [], []
    for t in topics:
        for name in t.live:
            live += _safe(lambda: globals()[name](context), [])
        app_ids += [a for a in t.apps if a not in app_ids]
        files += [f for f in t.files[:each + 1] if f not in files]
        decisions += [d for d in t.decisions[:each] if d not in decisions]
    lines = [x for x in live if x] + _safe(lambda: _app_lines(context, app_ids, apps), [])
    if not topics and not apps and not designs:  # "what apps do you have?": the names, from the registry
        from core import capabilities

        names = [a["name"] for a in _safe(lambda: capabilities.capability_map(context), [])
                 if a.get("where") != "retired" and a.get("open_to_you", True)]
        if not names:
            return ""
        lines.append(f"[app registry] My {len(names)} apps: " + ", ".join(names) + ".")
    for name, design in designs:  # her own designs: whether it's built, the decision (its status), the spec's opening
        code = built_by(name)
        lines.append(f"[my code] The {name} is built: {code}." if code else
                    f"[my code] Nothing in my code builds the {name} yet: it's a plan, not something I can do now. "
                    "Say so plainly.")
        decisions += [d for d in design["decisions"][:2] if d not in decisions]
        if design["spec"] and design["spec"] not in files:
            files.append(design["spec"])
    lines += [x for x in (_decision_line(d) for d in decisions) if x]
    for rel in files:
        said = _opening(rel)
        if said:
            lines.append(f"[my code and documents, {rel}] {said}")
    if not lines:
        return ""
    head = ("About you, MIA: what your own records and code say, read just now. Each line starts with where it comes "
            "from. Answer from these in the first person (I, my), in your own voice, and only as much as was asked. "
            "What isn't in them you don't know: say what you do know and that you'd have to check the rest, and call "
            "a guess a guess. Never make up an app, a feature, a screen, a date, an example or a piece of your "
            "history. \"Proposed\", \"planned\" and \"not connected\" mean it isn't working yet: say so. When two "
            "different things share the name they asked about, say there are two and tell them apart. A few "
            "sentences, not a list, unless they ask for all of it.")
    kept, used = [], len(head)
    for line in lines:
        if used + len(line) + 3 > BLOCK_CHARS:
            continue
        kept.append("- " + line)
        used += len(line) + 3
    return head + "\n" + "\n".join(kept)
