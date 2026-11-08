"""
core.web_guide
================

"Start Here" (Zac, 2026-11-07: "I don't see the browser on MIA or really
understand how to use much of anything we have built"): what MIA does, in
plain words, grouped by what a person wants to get done, each with the
words to say to her (a "Try saying" button opens Talk with them typed in)
and the page to open; and what's new, newest first.

STATIC content: written here, checked by tests (every page it opens exists
in web/, every app it names is in the app list), and kept true as things
change: when a feature changes how it's used, change its entry here too.

**Still empty** (2026-11-07, Zac: fill every app with his life so MIA is as
helpful as she can be, soon): `to_fill(context)`, the apps that hold nothing
yet for the signed-in person, each with the first thing to say (a sentence a
test checks reaches that app's add tool) or the page to open. Counted live
from the stores; nothing about what's in them is shown.
"""

from __future__ import annotations

# What a person wants to do -> how MIA helps, what to say, where to look.
TOPICS = (
    {"id": "talk", "title": "Talk to her", "icon": "mia",
     "how": "The glowing orb at the bottom right of every page opens Talk. Type or speak; she answers from your own "
            "records, and anything that changes something shows you a sentence to approve first. On the phone, "
            "the Talk button; on the glasses, a tap.",
     "say": ["What can you do?", "What's on today?", "Be funnier", "Undo that"], "page": "index.html"},
    {"id": "money", "title": "Money and receipts", "icon": "budget",
     "how": "Money shows bills, spending and what's due. Receipts sent to her (from your email, a photo, or Share "
            "from any phone app) land in the Inbox; emailed ones file themselves, stocking the pantry or marking the "
            "oil change done, and each has an Undo. Set up your email in the Inbox's Email section.",
     "say": ["What bills are due this week?", "Undo the Kroger receipt"], "page": "inbox.html"},
    {"id": "kitchen", "title": "Food and the pantry", "icon": "kitchen",
     "how": "Kitchen keeps recipes, the pantry and the grocery list; grocery receipts fill the pantry for you.",
     "say": ["What's in the pantry?", "Add milk to the grocery list", "What can I make for dinner?"],
     "page": "kitchen.html"},
    {"id": "building", "title": "Building things: plans and material lists", "icon": "knowledge",
     "how": "Knowledge has a Plans shelf: a shed, deck, fence, slab, chicken coop, shelving, a bookshelf, a lean-to, "
            "a compost bin, a cold frame, a picnic table, a firewood rack, stairs and a workbench, each worked out "
            "for any size. Or give her your own parts for a cut list. Save plan PDFs into reference_library\\plans "
            "and she finds them.",
     "say": ["What do I need to build a 10 by 12 shed?", "Materials for a chicken coop for 8 hens",
             "Cut list: 4 legs at 30 in 2x4; 1 top 24 by 48 in plywood", "Where can I get free plans?"],
     "page": "knowledge.html"},
    {"id": "browser", "title": "Her own web browser", "icon": "knowledge",
     "how": "Her browser lives inside MIA: on the Browser page, type a website or a search and press Open, and you "
            "watch it live. Click on the picture to click there, scroll it, and type in the box under it; she works "
            "in the same view, so you see each step she takes. She reads and searches by herself, but anything that "
            "submits, buys, signs in or sends waits for your OK, and she only types words you said. To teach her a "
            "task, open where it starts, name it under \"Learn a task\", do it in the picture, then \"Done, keep it\".",
     "say": ["Open the county website", "Read the page", "Learn this: pay the water bill", "Do pay the water bill"],
     "page": "browser.html"},
    {"id": "home", "title": "House, garage and homestead", "icon": "garage",
     "how": "Garage tracks vehicles and equipment and what upkeep is due; Chickens counts eggs; Greenhouse, "
            "Household chores and Security cameras each have their page.",
     "say": ["What maintenance is due?", "Collected 6 eggs today", "Did I do the chores today?"],
     "page": "garage.html"},
    {"id": "learn", "title": "Learning something", "icon": "classroom",
     "how": "Tell her what you want to learn and why; she plans stages, gives lessons and homework, and checks you "
            "off by real evidence. Guitar is built in; anything else she drafts and starts on your yes.",
     "say": ["I want to learn guitar", "I want to learn to weld", "What's my next guitar lesson?"],
     "page": "classroom.html"},
    {"id": "remember", "title": "Remembering for you", "icon": "notes",
     "how": "Say a promise or a decision out loud and she offers to keep it (Kept). Notes and the Journal hold what "
            "you write; the Memory Vault keeps your phone's photos safe on the PC.",
     "say": ["I promised Sam I'd fix his gate by Friday", "Add a note: call the vet Monday"],
     "page": "kept.html"},
    {"id": "body", "title": "Workouts and play", "icon": "workout",
     "how": "Workout logs sessions and personal bests; Play counts games and sports and how hard they were.",
     "say": ["Log a 30 minute workout", "What's my personal record on bench press?"], "page": "workout.html"},
    {"id": "outdoors", "title": "Outdoors and maps", "icon": "maps",
     "how": "Maps shows your waypoints on an offline map; Expeditions plans trips and packing.",
     "say": ["Add a waypoint called Spring here", "Plan a trip to the river next Saturday"], "page": "maps.html"},
    {"id": "wrong", "title": "When she gets it wrong", "icon": "issues",
     "how": "Say \"undo that\" right after a change, or use Undo on the screen that shows it. Thumbs down on an "
            "answer, or tell her what she should have done; the Fix-It Log keeps what went wrong until it's fixed.",
     "say": ["Undo that", "What did you change recently?"], "page": "issues.html"},
)

# Said phrases handled in code rather than by a tool (tests/test_web_guide.py checks every other one reaches a tool).
IN_CODE = {"I promised Sam I'd fix his gate by Friday"}  # core/life_notes.py offers to keep it after her reply

# Newest first: what changed lately, and where to see it.
NEW = (
    {"when": "2026-11-07", "what": "This Start Here page, and the sidebar grouped by area.", "page": "start.html"},
    {"when": "2026-11-07", "what": "The desktop opens on MIA's web screens; Ctrl+Shift+C shows the classic ones.",
     "page": "index.html"},
    {"when": "2026-11-07", "what": "Set up your email in the Inbox; receipts file themselves, with Undo.",
     "page": "inbox.html"},
    {"when": "2026-11-07", "what": "Her own browser, taught by showing, typing only your words.", "page": "browser.html"},
    {"when": "2026-11-07", "what": "Plans and material lists for 15 kinds of projects, and cut lists of your own.",
     "page": "knowledge.html"},
    {"when": "2026-11-07", "what": "She's funny sometimes; say \"be funnier\" or \"no jokes for now\".",
     "page": "index.html"},
    {"when": "2026-11-07", "what": "The phone app keeps your place when the phone locks.", "page": "index.html"},
)


def _none(context, store: str, method: str) -> bool:
    """Whether a store holds nothing (its list method returns empty); False when the store isn't here, so an app
    that can't be filled on this MIA isn't offered."""
    found = getattr(context, store, None)
    if found is None:
        return False
    try:
        return not getattr(found, method)()
    except Exception:
        return False


# The apps worth filling first, in order: (app, title, empty?, what to say, page). Said sentences reach the app's
# add tool (tests/test_web_guide.py).
FILL = (
    ("budget", "Your bills", lambda c: _none(c, "budget", "all_bills") and _none(c, "budget", "all_income_sources"),
     ["Add my electric bill, $120, due on the 3rd"], "money.html"),
    ("garage", "Your vehicles and equipment", lambda c: _none(c, "maintenance", "all_assets"),
     ["Add a vehicle: my 2019 pickup with 4,800 miles"], "garage.html"),
    ("calendar", "Your calendar", lambda c: _none(c, "calendar", "all_events"),
     ["Add the dentist on Tuesday at 3 to my calendar"], "calendar.html"),
    ("kitchen", "Your recipes", lambda c: _none(c, "kitchen", "all_recipes"), ["Add a recipe for turkey chili"],
     "kitchen.html"),
    ("relationships", "The people in your life", lambda c: _none(c, "relationships", "all_people"),
     ["Remember my sister Jordan's birthday is March 4"], "people.html"),
    ("workout", "Your workouts", lambda c: _none(c, "workout", "all_sessions"), ["I worked out for 45 minutes"],
     "workout.html"),
    ("flock", "Your chickens", lambda c: getattr(getattr(c, "flock", None), "flocks", None) == [], [], "flock.html"),
    ("real_estate", "Your rentals", lambda c: _none(c, "real_estate", "all_properties"),
     ["Add my rental on Oak Street, rent $1,150"], "real-estate.html"),
    ("insurance", "Your insurance", lambda c: getattr(getattr(c, "insurance", None), "policies", None) == [], [],
     "insurance.html"),
    ("power", "Your energy sources", lambda c: _none(c, "energy", "all_energy_sources"), [], "power.html"),
    ("expeditions", "Your trips", lambda c: _none(c, "trips", "all_trips") and _none(c, "expeditions", "all_expeditions"),
     ["Plan a trip to Ridge Loop on the 21st"], "expeditions.html"),
)


def to_fill(context) -> list[dict]:
    """The apps that hold nothing yet for this person, in FILL's order: each with its title, what to say and its
    page."""
    if context is None:
        return []
    return [{"app": app, "title": title, "say": list(say), "page": page}
            for app, title, empty, say, page in FILL if empty(context)]


def guide(context=None) -> dict:
    """The Start Here page's data: the topics (each with how, what to say and its page), what's new, and the apps
    still empty for this person (to_fill)."""
    return {"topics": [dict(t, say=list(t["say"])) for t in TOPICS], "new": [dict(n) for n in NEW],
            "to_fill": to_fill(context)}
