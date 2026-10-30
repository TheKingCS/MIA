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

`capability_map()` gathers it; `overview()` and `can_i()` say it.
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
    "freedom": "The estimate assumes the last three months' pace; transfers between your own accounts can look like spending until the bank sync sorts them.",
    "compliance": "MIA keeps the list and reminds you; she never files, pays or signs anything, and a deadline isn't confirmed until you verify it.",
    "calendar": "",
    "greenhouse": "No sensors yet: readings are entered by hand.",
    "flock": "",
    "garage": "",
    "kitchen": "",
    "household": "No web screen yet: the desktop has it.",
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
    "power": "No web screen yet.",
    "character": "",
    "reward_shop": "",
    "observations": "No web screen yet.",
    "relationships": "",
    "notes": "",
    "classroom": "No web screen yet.",
    "inbox": "Email intake reads one mailbox you set up for MIA.",
    "expeditions": "",
    "vault": "",
    "memories": "No web screen yet.",
    "maps": "No web screen yet.",
    "navigation": "No web screen yet.",
    "knowledge": "No web screen yet.",
    "toolbox": "No web screen yet.",
    "lab": "No web screen yet.",
    "field_kit": "No web screen yet.",
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
    ("Health and growth", ("workout", "dungeon", "missions", "skills", "character", "reward_shop", "classroom")),
    ("Your days and people", ("calendar", "relationships", "notes", "inbox", "observations", "vault", "memories")),
    ("Making things", ("workshop", "lab", "field_kit", "toolbox")),
    ("Outdoors", ("expeditions", "maps", "navigation", "knowledge")),
    ("Everyday", ("music", "files", "passwords")),
)
# Not listed in the overview. MIA herself (Home, the chat, Apps, Settings,
# Diagnostics, the Fix-It Log) gets the closing line instead; Freedom stays out at the
# owner's request (2026-10-29), though "can you…?" still finds it.
OVERVIEW_SKIP = {"web_home", "assistant", "module_browser", "settings", "diagnostics", "issues", "freedom"}
# Each app in a few words, for the overview.
GIST = {
    "budget": "bills, income, spending and debts", "insurance": "your policies and quotes compared",
    "compliance": "tax deadlines, permits and renewals", "business": "quotes, orders and what customers owe",
    "real_estate": "property values and rental income", "kitchen": "recipes, the pantry and the grocery list",
    "household": "chores and routines", "greenhouse": "the garden and greenhouse", "flock": "your chickens and eggs",
    "garage": "vehicle and equipment upkeep", "security": "your home cameras", "power": "battery and energy",
    "workout": "workouts and records", "dungeon": "your work shifts, as loot you earn", "missions": "goals you're working toward", "skills": "a skill tree",
    "character": "a record of what you've done", "reward_shop": "rewards you earn",
    "classroom": "courses and lessons", "calendar": "your calendar", "relationships": "people, pets and birthdays",
    "notes": "notes and a journal", "inbox": "receipts and documents I file",
    "observations": "what I notice over time", "vault": "keeping your phone's photos safe",
    "memories": "trip recaps", "workshop": "builds, materials and goods you sell",
    "lab": "sensor experiments", "field_kit": "connected devices and scripts",
    "toolbox": "unit conversion and calculators", "expeditions": "trips, routes and gear",
    "maps": "offline maps and trail maps", "navigation": "waypoints, distances and sun and moon times",
    "knowledge": "offline reference", "music": "your music", "files": "your files",
    "passwords": "a password vault I never see into",
}


def _tools_by_domain(context) -> dict[str, list]:
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
        "Ask me what I can do, or just tell me what you're working on.",
    ]
    return " ".join(lines)


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
    return next((a for a in capability_map(context) if a["id"] == app_id), None)
