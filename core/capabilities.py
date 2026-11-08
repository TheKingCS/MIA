"""
core.capabilities
===================

What MIA can do, built from the code (DEC-0041; the intelligence spec's
Phase 2B, docs/INTELLIGENCE_AUDIT.md). Never a hand-written brochure:

- **Apps** come from `core/web_surfaces.APPS`: name, what it's for,
  where it runs (the web and the desktop, the web only, the desktop only:
  no web screen yet), and whether this person can open it (a child's
  apps are fewer).
- **Tools** come from the Assistant's own registry: for each app, the
  things MIA can look up and the things she can change by being asked,
  from the tool domains the app lists.
- **Changes on screens** come from the action contract
  (`core/actions.ACTION_TYPES`): how many kinds of change each screen can
  propose for approval.
- **Limits** are the one curated part, `LIMITS` below: what an app
  can't do yet, in a sentence. A test fails when an app has no entry
  (an empty string means "none worth saying").

- **The overview** groups the apps into `AREAS`, each app said in a few
  words (`GIST`), the other curated part: "what can you do?" answered in
  a breath, not 42 descriptions. A test fails when an app is in no area.

- **Specialties** (`specialty_list()`, Zac 2026-11-08): what she's trained
  for and built to do (aquaponics greenhouse scientist, specialists, Night
  School, teacher, builder, planner, experimenter, game master, model
  maker, browser, painter), each line read from the module that makes it
  true and left out when that module or its data isn't there.

`capability_map()` gathers it; `overview()`, `introduction()`,
`specialties()` and `can_i()` say it.
"""

from __future__ import annotations

import re
from typing import Optional

# What each app can't do yet (DEC-0041: every app has an entry; "" = nothing worth saying).
LIMITS = {
    "web_home": "",
    "dashboard": "Retired: Home shows what it showed.",
    "issues": "MIA finds and groups the problems; fixing her code is Claude's job, tested before it ships, never hers.",
    "dungeon": "Loot is pay before taxes, worked out from your hours; what reaches the bank comes from the bank sync. Shift differentials and tips aren't counted yet.",
    "operating_journal": "Lines MIA can't see in your records (sleep, mood, focus) are yours to rate; she never judges the gap.",
    "play": "Training load needs how hard it was; without it she counts a middle effort and asks next time.",
    "life_notes": "Kept only on your yes, from plain first-person words (\"I promised...\", \"we're going with...\"); some slip by, so tell her again.",
    "browser": "Her own Edge window on your PC, none of your sign-ins: anything that submits, buys, sends, signs in or deletes waits for your OK, and she never types passwords or card numbers; a taught task stops when a site changes.",
    "sight": "Looks on your PC with a local model: a judgment from the picture, said as one; never who a person is; the photo isn't kept.",
    "good_news": "Reads its 16 sources once a day, only when you switch it on; stories are picked by rules in code, so one can slip through that isn't quite good news: say it was misleading.",
    "freedom": "The estimate assumes the last three months' pace; transfers between your own accounts can look like spending until the bank sync sorts them.",
    "compliance": "MIA keeps the list and reminds you; she never files, pays or signs anything, and a deadline isn't confirmed until you verify it.",
    "calendar": "",
    "greenhouse": "No sensors yet: readings are entered by hand.",
    "flock": "",
    "garage": "",
    "kitchen": "",
    "household": "Routines are added by asking MIA; the web page ticks them off.",
    "workout": "",
    "real_estate": "Selling a property isn't tracked yet.",
    "missions": "",
    "skills": "",
    "budget": "Connecting and syncing banks needs the desktop on the home computer (the vault passphrase).",
    "maintenance": "Folded into Garage, Property and Greenhouse.",
    "property": "Folded into Real Estate.",
    "workshop": "Cups can't be compared to pounds (no densities).",
    "business": "",
    "insurance": "MIA compares the quotes you collect; she never shops or buys for you.",
    "security": "Cameras need a local stream (no cloud-only cameras).",
    "power": "Readings are entered by hand; no sensors are connected yet.",
    "character": "",
    "reward_shop": "",
    "observations": "Read only: each is resolved where it lives (the upkeep, the mission, the bill).",
    "relationships": "",
    "notes": "",
    "classroom": "Lesson notes, skill rewards and the textbook tutor are on the desktop.",
    "inbox": "Email intake reads one mailbox you set up for MIA.",
    "expeditions": "",
    "vault": "",
    "memories": "Recaps come from Expeditions' trips; the photos are on the Expeditions page.",
    "maps": "Vector areas are the ones cut onto the PC (names in Latin script); topo tiles are US-only.",
    "navigation": "Waypoints are added by voice or on the map; sun times are for the day, not live.",
    "knowledge": "Only packs copied onto this computer; articles read as plain text, without pictures.",
    "toolbox": "Alarms ring on the PC.",
    "lab": "Readings are entered by hand; no sensors are connected yet.",
    "field_kit": "Ejecting drives, running scripts and the port scan are on the PC.",
    "passwords": "MIA's assistant never sees a password; no autofill in other apps yet.",
    "files": "",
    "music": "",
    "assistant": "",
    "diagnostics": "No web screen yet.",
    "module_browser": "",
    "settings": "No web screen yet: the desktop has it.",
}


# The overview, area by area (each app in exactly one, or in OVERVIEW_SKIP).
AREAS = (
    ("Money", ("budget", "insurance", "compliance", "business", "real_estate")),
    ("Home and land", ("kitchen", "household", "greenhouse", "flock", "garage", "security", "power")),
    ("Health and growth", ("workout", "play", "operating_journal", "dungeon", "missions", "skills", "character", "reward_shop",
                           "classroom")),
    ("Your days and people", ("calendar", "relationships", "notes", "life_notes", "inbox", "observations", "vault",
                              "memories")),
    ("Making things", ("workshop", "lab", "field_kit", "toolbox")),
    ("Outdoors", ("expeditions", "maps", "navigation", "knowledge")),
    ("Everyday", ("music", "good_news", "sight", "files", "passwords")),
)
# Not listed in the overview. MIA herself (Home, the chat, Apps, Settings,
# Diagnostics, the Fix-It Log) gets the closing line instead; Freedom stays out at the
# owner's request (2026-10-29), though "can you…?" still finds it.
OVERVIEW_SKIP = {"web_home", "assistant", "module_browser", "settings", "diagnostics", "issues", "freedom",
                 "browser"}  # her browser is part of her, like the chat (DEC-0117)
# Each app in a few words, for the overview.
GIST = {
    "budget": "bills, income, spending and debts", "insurance": "your policies and quotes compared",
    "compliance": "tax deadlines, permits and renewals", "business": "quotes, orders and what customers owe",
    "real_estate": "property values and rental income", "kitchen": "recipes, the pantry and the grocery list",
    "household": "chores and routines", "greenhouse": "the garden and greenhouse", "flock": "your chickens and eggs",
    "garage": "vehicle and equipment upkeep", "security": "your home cameras", "power": "battery and energy",
    "workout": "workouts and records", "play": "games and sports",
    "operating_journal": "how you mean to live", "good_news": "daily good news", "sight": "looking at a photo", "dungeon": "your work shifts, as loot you earn", "missions": "goals you're working toward", "skills": "a skill tree",
    "character": "a record of what you've done", "reward_shop": "rewards you earn",
    "classroom": "courses and lessons", "calendar": "your calendar", "relationships": "people, pets and birthdays",
    "notes": "notes and a journal", "life_notes": "your promises", "inbox": "receipts and documents I file",
    "observations": "what I notice over time", "vault": "keeping your phone's photos safe",
    "memories": "trip recaps", "workshop": "builds, materials and goods you sell",
    "lab": "sensor experiments", "field_kit": "connected devices and scripts",
    "toolbox": "unit conversion and calculators", "expeditions": "trips, routes and gear",
    "maps": "offline maps and trail maps", "navigation": "waypoints, distances and sun and moon times",
    "knowledge": "offline reference", "music": "your music", "files": "your files",
    "passwords": "a password vault I never see into",
}


def _tools_by_domain(context) -> dict[str, list]:
    """Every Assistant tool, grouped by its domain."""
    registry = getattr(context, "assistant_actions", None)
    out: dict[str, list] = {}
    if registry is None:
        return out
    for action in getattr(registry, "_actions", {}).values():
        out.setdefault(action.domain, []).append(action)
    return out


def _screen_changes() -> dict[str, int]:
    """How many kinds of change each record prefix proposes ("craft", "flock"...)."""
    from core.actions import ACTION_TYPES

    counts: dict[str, int] = {}
    for kind in ACTION_TYPES:
        prefix = kind.split(".", 1)[0].split("_", 1)[0]
        counts[prefix] = counts.get(prefix, 0) + 1
    return counts


def capability_map(context=None) -> list[dict]:
    """Every app: what it's for, where it runs, whether this person can
    open it, the tools MIA can use in it (look up / change), and its limits."""
    from core.assistant_actions import changes_records
    from core.web_surfaces import APPS, RETIRED, WEB_ONLY

    tools = _tools_by_domain(context) if context is not None else {}
    allowed = None
    if context is not None:
        try:
            from core.child_accounts import app_allowed

            allowed = lambda app_id: app_allowed(context, app_id)  # noqa: E731
        except ImportError:
            allowed = None
    out = []
    for app in APPS:
        mine = [a for domain in app.domains for a in tools.get(domain, [])]
        if app.module_id in RETIRED:
            where = "retired"
        elif app.module_id in WEB_ONLY:
            where = "web"
        elif app.page:
            where = "web and desktop"
        else:
            where = "desktop"
        out.append({
            "id": app.module_id, "name": app.name, "where": where,
            "what": re.sub(r"\s*\(DEC-\d{4}\)", "", app.description),  # a decision number means nothing said aloud
            "open_to_you": True if allowed is None else bool(allowed(app.module_id)),
            "look_up": sorted({a.name for a in mine if not changes_records(a.name)}),
            "change": sorted({a.name for a in mine if changes_records(a.name)}),
            "ask": app.ask, "limits": LIMITS.get(app.module_id, ""),
        })
    return out


def overview(context) -> str:
    """Plain words: what MIA does, area by area, from the code (see AREAS)."""
    apps = {a["id"]: a for a in capability_map(context) if a["where"] != "retired" and a["open_to_you"]}
    registry = getattr(context, "assistant_actions", None)
    count = len(getattr(registry, "_actions", {})) if registry is not None else 0
    lines = [f"I have {len(apps)} apps and {count} things I can look up or do when you ask."]
    tries = []
    for area, ids in AREAS:
        mine = [apps[i] for i in ids if i in apps]
        if not mine:
            continue
        lines.append(f"{area}: " + "; ".join(GIST[a["id"]] for a in mine) + ".")
        ask = next((a["ask"] for a in mine if a["ask"]), "")
        if ask and len(tries) < 3:
            tries.append(f"\"{ask.rstrip('.')}\"")
    lines.append("I can also change my own settings, check how the computer is doing, keep a log of where I go wrong so I get fixed, and undo my last change.")
    if tries:
        lines.append("Try " + ", ".join(tries[:-1]) + (" or " if len(tries) > 1 else "") + tries[-1] + ".")
    lines.append("Ask \"can you…?\" about anything and I'll say whether I can, and what's missing if I can't.")
    return " ".join(lines)


def introduction(context) -> str:
    """Plain words: who MIA is, for "tell me about yourself" (2026-10-29:
    the model's own answer sounded like a therapist and pitched the
    freedom plan). Scripted in her voice (docs/design/MIA_VOICE.md), the
    numbers from the code, so it's instant and says what she really is."""
    from core.child_accounts import is_child

    apps = [a for a in capability_map(context) if a["where"] != "retired" and a["open_to_you"]]
    registry = getattr(context, "assistant_actions", None)
    count = len(getattr(registry, "_actions", {})) if registry is not None else 0
    child = is_child(context)
    life = ("your chores, your pets, your lessons, your trips and the things you build" if child else
            "your money, your home and land, your training, the things you make, your trips and the people "
            "you care about")
    lines = [
        "I'm MIA, your own assistant. I run on your computer and your phone, not in someone else's cloud.",
        f"I keep track of {life}, all in one place, so you don't have to hold it in your head.",
        f"That's {len(apps)} apps and {count} things I can look up or do the moment you ask, and every answer "
        "comes from your real records. If I don't know something, I'll tell you.",
        "I work offline. The internet is only for a few things, like the weather" +
        ("." if child else " and syncing your bank."),
        "I suggest, you decide: nothing changes unless you say so, and I can undo what I did." +
        ("" if child else " I never send an email or spend a cent on my own."),
        "What's yours stays yours: no one else sees it unless you share a household.",
        "Ask me what I can do or what I'm trained for, or just tell me what you're working on.",
    ]
    return " ".join(lines)


def _join(names: list) -> str:
    """Pure logic. "a, b and c" (or "a and b", or "a")."""
    names = [str(n) for n in names if n]
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1] if names else ""


def _soft(name: str) -> str:
    """Pure logic. A name mid-sentence: each word lowercased except acronyms ("Software and AI engineering" to
    "software and AI engineering")."""
    return " ".join(w if len(w) > 1 and w.isupper() else w.lower() for w in str(name).split())


def _first_person(directive: str) -> str:
    """Pure logic. The first sentence of a directive written to her ("Build yourself into a top-tier AI."), in her own
    voice ("build myself into a top-tier AI")."""
    first = re.split(r"(?<=[.!?])\s", directive.strip(), maxsplit=1)[0].rstrip(".!? ")
    first = re.sub(r"\byourself\b", "myself", first, flags=re.I)
    first = re.sub(r"\byour\b", "my", first, flags=re.I)
    return first[:1].lower() + first[1:] if first else ""


def specialty_list(context=None) -> list[tuple[str, str]]:
    """What MIA is trained for and built to do (Zac, 2026-11-08: she should know "all the cool things about her
    programming"), each a (title, line) read from the code that makes it true, never a brochure (DEC-0041). A
    specialty whose code or data isn't there is left out, so she never claims what she can't do; the person's own
    numbers (batches growing, experiments running) join when they exist."""
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    out: list[tuple[str, str]] = []

    def grow() -> str:
        """The grow lab (DEC-0030 D), and MIA Homestead when it's part of her (DEC-0145)."""
        from core import grow_lab

        measures = _join([label if label.isupper() or label == "pH" else label.lower()
                          for label, _ in grow_lab.MEASURES.values()])
        line = ("I run a greenhouse, aquaponics tanks and grow beds like a scientist: every planting is a batch with "
                "its yield and losses, experiments put batches side by side until you write the conclusion, and the "
                f"water is read against safe ranges you set ({measures}). I warn; I never run a pump on my own.")
        lab = getattr(context, "grow_lab", None)
        if lab is not None:
            growing = sum(b.status == "Growing" for b in lab.batches)
            running = sum(e.status == "Running" for e in lab.experiments)
            if growing or running:
                line += f" Right now: {growing} batch{'es' if growing != 1 else ''} growing, " \
                        f"{running} experiment{'s' if running != 1 else ''} running."
        home = root / "homestead"
        if (home / "drivers" / "simulator.py").exists():
            line += (" And MIA Homestead is part of me: a whole greenhouse and aquaponics control system, built and "
                     "proven in a simulator first" + (", with safety firmware of its own." if (home / "firmware").exists()
                                                       else "."))
        return line

    def specialists() -> str:
        """The knowledge workers (DEC-0109)."""
        from core.specialists import SPECIALISTS

        return (f"I keep {len(SPECIALISTS)} specialists, each with a workbook of sourced notes I study at night: "
                f"{_join([_soft(s.name) for s in SPECIALISTS])}. You can ask any of them a question.")

    def night_school() -> str:
        """Her curriculum (DEC-0107) and standing aim (DEC-0100)."""
        from core.curriculum import TRACKS
        from core.night_school import settings

        line = (f"Every night I go to Night School: {len(TRACKS)} tracks of computing, from "
                f"{_soft(TRACKS[0].name)} to {_soft(TRACKS[-1].name)}, a lesson at a time.")
        aim = _first_person(str(settings().get("directive") or ""))
        return line + (f" My standing aim: to {aim}." if aim else "")

    def teacher() -> str:
        """Learning paths (DEC-0112)."""
        from core import paths

        paths._builtins()
        built = [f"{_soft(p.name)} ({len(p.stages)} stages)" for p in paths.PROGRAMS.values()]
        return ("I teach anything you want to get good at as a learning path: stages, lessons, your practice logged, "
                "weekly homework, and checks I verify from your own records" +
                (f". Built in so far: {_join(built)}." if built else "."))

    def builder() -> str:
        """Plans with material and cut lists worked out in code (DEC-0118)."""
        from core.plan_library import BUILT_IN

        some = [_soft(p["title"]) for p in BUILT_IN[:4]]
        return (f"I'm a builder's helper: {len(BUILT_IN)} plans I size to you, like {_join(some)}, with the "
                "materials and cuts worked out in code, never guessed, and a cut list for anything of your own.")

    def planner() -> str:
        """The development engine (DEC-0144)."""
        from core.development_engine import homestead_catalog

        return (f"I plan a homestead from what you actually have: I weigh {len(homestead_catalog())} projects by cost, "
                "payoff and what each one unlocks, and name the one move worth making next.")

    def experimenter() -> str:
        """How she tests and improves herself: answer-style A/B (DEC-0138) and the improvement loops (DEC-0094)."""
        from core.loops import LOOPS
        from core.response_style import DIMENSIONS

        return (f"I'm built to experiment: I try two ways of answering you across {len(DIMENSIONS)} things "
                f"({_join(list(DIMENSIONS))}) and keep what you pick, I compare grow batches to learn what really "
                f"works, and {len(LOOPS)} improvement loops measure me and open work when I slip.")

    def game_master() -> str:
        """Living Worlds (DEC-0134) and the Dungeon (DEC-0046)."""
        import core.dungeon_master  # noqa: F401 - present means she can run a world
        import core.work_dungeon  # noqa: F401

        return ("I'm a game master: I run living fantasy worlds as their Dungeon Master (you act, I narrate, the dice "
                "decide, and nothing there ever touches your real life), and I turn your work week into a dungeon "
                "you clear for loot.")

    def model_maker() -> str:
        """Her model forge (DEC-0106)."""
        from core.model_forge import cards

        made = cards()
        if made:
            names = _join([str(c.get("name", "")) for c in made])
            return (f"I train small models of my own on my own records: {len(made)} so far ({names}), each measured "
                    "honestly and kept with a card saying what it is.")
        return "I can train small models of my own on my own records, each measured honestly and kept with a card."

    def browser() -> str:
        """Her browser (DEC-0117)."""
        import core.browser  # noqa: F401

        return ("I have a web browser of my own, without your sign-ins: I read, search and follow links myself, and "
                "anything that commits waits for your OK.")

    def painter() -> str:
        """Painting (DEC-0140): said as ready only when the engine is running."""
        from core.art_studio import status

        if status(context)["engine"]["available"]:
            return "I paint on your PC's own graphics card: describe a scene and I'll make it, even a page's background."
        return ("I can paint pictures, like a scene for a page's background, on your PC's own graphics card once its "
                "art engine is set up.")

    for title, fn in (("Aquaponics greenhouse scientist and manager", grow), ("Specialists", specialists),
                      ("Night School", night_school), ("Teacher", teacher), ("Builder", builder),
                      ("Homestead planner", planner), ("Experimenter", experimenter), ("Game master", game_master),
                      ("Model maker", model_maker), ("Browser", browser), ("Painter", painter)):
        try:
            line = fn()
        except Exception:  # noqa: BLE001 - a specialty that can't be read is left out, never claimed
            line = ""
        if line:
            out.append((title, line))
    return out


def specialties(context) -> str:
    """Plain words: what MIA is trained for and built to do, for "what are you trained for?", from
    `specialty_list` (so the answer is instant and true)."""
    rows = specialty_list(context)
    if not rows:
        return "I can't read my own specialties right now. Ask me what I can do instead."
    return "Here's what I'm trained for and built to do.\n" + "\n".join(f"{title}: {line}" for title, line in rows)


_WORD = re.compile(r"[a-z0-9']+")
_SKIP = {"can", "you", "your", "mia", "do", "does", "a", "an", "the", "my", "me", "i", "to", "for", "of", "and", "or",
         "it", "is", "are", "be", "with", "on", "in", "at", "how", "what", "help", "please", "able", "will", "would"}


_SUFFIXES = ("ings", "ing", "ies", "es", "ed", "er", "s")


def _stem(word: str) -> str:
    """Pure logic. A crude stem, enough to match "taxes" with "tax",
    "filings" with "file", "chickens" with "chicken"."""
    for suffix in _SUFFIXES:
        if len(word) > len(suffix) + 2 and word.endswith(suffix):
            word = word[: -len(suffix)]
            break
    return word[:-1] if len(word) > 3 and word.endswith("e") else word


def _words(text: str) -> set[str]:
    """Pure logic. A text's words, stemmed, the little ones left out."""
    return {_stem(w) for w in _WORD.findall(text.lower()) if w not in _SKIP}


def can_i(context, thing: str) -> str:
    """Plain words: whether MIA can do `thing`: the app and tools that
    match it best (by their own names and descriptions), with limits; or
    that nothing matches, never a guess."""
    want = _words(thing)
    if not want:
        return overview(context)
    registry = getattr(context, "assistant_actions", None)
    actions = getattr(registry, "_actions", {}) if registry is not None else {}
    scored = []
    for a in capability_map(context):
        if a["where"] == "retired":
            continue
        # The app's own name counts most, then what it's for, then its example and tools.
        tools_text = " ".join([a["ask"]] + [actions[t].description for t in a["look_up"] + a["change"] if t in actions])
        hit = 3 * len(want & _words(a["name"] + " " + a["id"])) + 2 * len(want & _words(a["what"])) +             len(want & _words(tools_text))
        if hit:
            scored.append((hit, a))
    if not scored:
        return (f"I can't find anything in MIA that does \"{thing.strip()}\". That's a feature MIA doesn't have yet, "
                "as far as my own app list shows.")
    scored.sort(key=lambda x: -x[0])
    best = [a for hit, a in scored if hit == scored[0][0]][:2]
    parts = []
    for a in best:
        how = []
        if a["change"]:
            how.append("I can change things there when you ask")
        if a["look_up"]:
            how.append("look things up")
        where = {"web": "on the web and the phone", "web and desktop": "on the web, the phone and the desktop",
                 "desktop": "on the desktop only for now"}[a["where"]]
        sentence = f"{a['name']} ({where}): {a['what'].rstrip('.')}."
        if how:
            sentence += " " + " and ".join(how).capitalize() + "."
        if not a["open_to_you"]:
            sentence += " It isn't one of your apps (ask a parent)."
        if a["limits"]:
            sentence += f" Limit: {a['limits']}"
        if a["ask"]:
            sentence += f" Try: \"{a['ask']}\""
        parts.append(sentence)
    return "Closest match in MIA: " + " ".join(parts)


def find_app(context, app_id: str) -> Optional[dict]:
    """One app's entry in the capability map, by id, or None."""
    return next((a for a in capability_map(context) if a["id"] == app_id), None)
