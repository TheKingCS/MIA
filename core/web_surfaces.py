"""
core.web_surfaces
===================

What the web front end's shell and Home show (2026-10-06, DEC-0017:
the web becomes all of MIA, function first, in the concept's look).
Assembled here, in code, so `web/` holds no logic (DEC-0013): which
apps a person sees, their level and XP, the greeting, Today's Focus,
the upcoming list and the at-a-glance cards.

- `shell(context)`: the sidebar (the person's apps, each with its life
  area, child-safe and respecting the apps they've tucked away; their
  favorites for the Pinned list; the areas with their hubs, DEC-0129,
  core/web_areas.py), their level and XP, today's date. Served as
  `/api/shell`.
- `dashboard(context)`: Home's data (the canvas's Home, DEC-0113): the
  greeting and date, the status strip (`home_strip`), the one thing MIA
  noticed across apps (`_top_finding`, from core/findings.py), Today's
  Focus and Upcoming with each row's kind (`due_kind`), quick actions and
  at-a-glance cards (Life State's, net worth on Money's, then Observations
  and the Inbox: `glance_counts`), and the life cards (DEC-0129,
  `life_cards`: what's playing, today's good news, recent pictures, the
  trip from `pick_trip` with its dates from `span_text`). Served as
  `/api/dashboard`; `web/index.html` shows it.
- `apps_page(context)`: every app, grouped, with what MIA can do in each.
  Served as `/api/apps`.

Apps appear in the sidebar once they have a web screen (`page`); the
rest are counted in `on_pc_only` until they arrive. `docs/WEB_PARITY.md`
tracks that. The core never imports `modules/`, so the app list is
here, by module id, in the Qt app's order and names.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)


@dataclass(frozen=True)
class App:
    """One app as the web knows it: its module id, name, icon, tagline, web page (None when it isn't on the web yet),
    description, life area, the Assistant tool domains that work in it, and an example of what to say.
    """
    module_id: str
    name: str
    icon: str
    tagline: str = ""
    page: Optional[str] = None  # the web screen, relative to /web/; None = not on the web yet
    description: str = ""  # the module's own `description` (tests keep them equal)
    group: str = ""  # the life area on the Apps page
    domains: tuple[str, ...] = ()  # the Assistant tool domains that work in it
    ask: str = ""  # an example of what to say to MIA about it


MONEY, HOME, LIFE, OUTDOORS, KNOW = ("Money & business", "Home, homestead & equipment", "Life, goals & self",
                                     "Outdoors & field", "Knowledge, tools & system")
GROUPS = (LIFE, MONEY, HOME, OUTDOORS, KNOW)

# The order of the concept's sidebar first, then the rest of MIA.
APPS: tuple[App, ...] = (
    App("web_home", "Home", "✨", "MIA, and a chat with her.", "index.html",
        "MIA herself: her presence, today's one thing, and a chat with her.", LIFE, (), "How are you, MIA?"),
    App("dashboard", "Dashboard", "📊", "Your life. In sync.", "dashboard.html",
        "Recent activity, active missions, memories, and upcoming items at a glance.", LIFE,
        ("today", "alarms", "projects", "life_events", "links", "why"), "What's on today?"),
    App("dungeon", "The Dungeon", "🏰", "Clear the run. Bank the loot.", "dungeon.html",
        "Work as a dungeon you loot every day: runs, hard mode, overtime bosses, projected and banked loot (DEC-0046).",
        MONEY, ("dungeon", "loop"), "How much loot this week?"),
    App("issues", "Fix-It Log", "🛠", "Where MIA stumbled, so it gets fixed.", "issues.html",
        "Where MIA got it wrong, broke or was slow, grouped and ranked, ready to be fixed; what she learned you mean (DEC-0049).",
        KNOW, ("issues",), "What's been going wrong?"),
    App("freedom", "Freedom", "🌄", "Your way out, in numbers.", "freedom.html",
        "What you're saving toward, how far along you are, and the day it's within reach (DEC-0038).", MONEY,
        ("freedom",), "When can I work from home?"),
    App("compliance", "Compliance", "📋", "Every deadline, on time.", "compliance.html",
        "Tax filings and payments, permits, licences and renewals, each with its official source (DEC-0040).",
        MONEY, ("compliance",), "What's due for taxes?"),
    App("calendar", "Calendar", "📅", "Everything with a date.", "calendar.html",
        "Your events, plus upkeep, bills, meals, training and birthdays, by day.", LIFE,
        ("calendar",), "What's on my calendar this week?"),
    App("greenhouse", "Greenhouse", "🌱", "Grow food. Grow freedom.", "greenhouse.html",
        "At-a-glance status for garden, greenhouse, and aquaponics assets.", HOME, ("maintenance",),
        "What needs doing in the greenhouse?"),
    App("flock", "Chickens", "🐔", "Eggs, every day.", "flock.html",
        "Your flock: eggs collected, the lay rate, feed cost per dozen, and cartons for the stand (DEC-0037).", HOME,
        ("flock",), "How many eggs this week?"),
    App("garage", "Garage", "🚗", "Keep it running. Keep it ready.", "garage.html",
        "At-a-glance status for vehicles and motorized equipment.", HOME, ("maintenance", "ownership"),
        "What upkeep is due on my vehicles?"),
    App("kitchen", "Kitchen", "🍳", "Good food. Good mood.", "kitchen.html",
        "Recipes, pantry, grocery list, and meal tracking.", HOME, ("kitchen", "groceries"),
        "What can I make with what's in the pantry?"),
    App("household", "Household", "🧺", "A home that runs itself.", "household.html",
        "Daily and weekly household routines — laundry, dishes, chores.", HOME, ("household",),
        "I did the dishes."),
    App("workout", "Workout", "🏋", "Stronger body. Clearer mind.", "workout.html",
        # "health" (2026-11-08): sleep, visits, medications and records (core/assistant_health_actions.py) live on
        # the Health page in the same area, which isn't an app of its own
        "Exercises, guided sessions, and progress.", LIFE, ("workout", "health"), "Log a 30 minute workout."),
    App("real_estate", "Real Estate", "🏘", "Cash flow. Equity. Freedom.", "real-estate.html",
        "Property values, equity, rental income, and linked maintenance.", MONEY, ("real_estate", "inventory"),
        "How are my rentals doing this month?"),
    App("missions", "Missions", "🏆", "Explore. Complete. Level up.", "missions.html",
        "Gamified goals and objectives, tied to a trip or general.", LIFE, ("missions",),
        "Add a mission to build a chicken coop."),
    App("skills", "Skills", "⚔", "Do the thing. Earn the level. Unlock the next thing.", "skills.html",
        "My Hero's Path — skill tree and character progression.", LIFE, ("skills",), "Which skills am I growing?"),
    App("budget", "Money", "💰", "Know where it goes.", "money.html",
        "Household bills, income, expenses, and tax-relevant totals.", MONEY,
        ("budget", "debts", "homestead_costs", "business_use", "business_tags"), "Which debt should I pay first?"),
    App("maintenance", "Maintenance", "🔧", "Everything you own, cared for.", "maintenance.html",
        "Recurring upkeep tracking for vehicles, equipment, appliances, property, and tools.", HOME,
        (), "I put 120 hours on the mower."),
    App("property", "Property", "🏠", "The house, the appliances, the tools.", "property.html",
        "At-a-glance status for the house, appliances, and tools.", HOME, (),
        "Do I have any furnace filters left?"),
    App("workshop", "Workshop", "🔩", "Parts, jobs and products.", "workshop.html",
        "Recipes and builds, materials, homestead goods in batches, market days, labels, and the shop's sales.", MONEY,
        ("components", "materials", "jobs", "products", "ledger", "goods"), "How much plywood do I have?"),
    App("business", "Orders & Quotes", "🧾", "Customers, quotes and orders.", "business.html",
        "Quotes from your recipes, customers, orders and payments, and a portfolio of what you've built (DEC-0030).",
        MONEY, ("ledger",), "How much profit did I make this month?"),
    App("insurance", "Insurance", "☂️", "Covered, for less.", "insurance.html",
        "Your policies in one place, what's worth a look, and quotes compared fairly (DEC-0034).", MONEY, ("insurance",),
        "When does my car insurance renew?"),
    App("security", "Security", "🛡️", "Your cameras, at home.", "security.html",
        "Your home cameras, watched live from MIA over your own network, no cloud (DEC-0033).", HOME, ("cameras",),
        "Are the cameras working?"),
    App("power", "Power", "🔋", "Energy, tracked.", "power.html",
        "Battery status and manual energy/utility tracking.", HOME, ("power",), "How's the battery?"),
    App("character", "Character", "👤", "Your story so far.", "character.html",
        "A living record of what you've actually done.", LIFE, ("character",), "What level am I?"),
    App("reward_shop", "Reward Shop", "🎁", "Spend what you earn.", "shop.html",
        "Real rewards you set, bought with the credits you earn (DEC-0028).", LIFE, ("reward_shop",), "What can I buy with my credits?"),
    App("observations", "Observations", "🔍", "What MIA noticed.", "observations.html",
        "What MIA has noticed across your maintenance and missions.", LIFE, (), "What have you noticed lately?"),
    App("relationships", "People", "👥", "The ones who matter.", "people.html",
        "Relationship profiles and pet profiles.", LIFE, ("relationships",), "When is the next birthday?"),
    App("notes", "Journal", "📓", "Write it down.", "journal.html",
        "Dated, searchable, taggable journal entries.", LIFE, ("notes", "journal", "private_journal"),
        "Make a note: call the plumber Friday."),
    App("classroom", "Classroom", "🎓", "Keep learning.", "classroom.html",
        "Your own subjects, courses, and lessons.", LIFE, ("classroom", "textbooks", "learning"), "How is my learning progress?"),
    App("inbox", "Inbox", "📥", "Paperwork, handled.", "inbox.html",
        "Receipts, manuals and documents MIA files for you.", MONEY, ("inbox", "email"),
        "What's waiting in my inbox?"),
    App("expeditions", "Expeditions", "🏕", "Plan the trip.", "expeditions.html",
        "Expedition Mode: trip routes, gear, weather, and logged speed/distance for any outing.", OUTDOORS,
        ("expeditions",), "Plan a weekend camping trip."),
    App("vault", "Memory Vault", "🗄", "Your photos, kept safe.", "vault.html",
        "Your phone's photos and videos, kept safe on your home computer, so the phone can let them go (DEC-0030).",
        LIFE, ("vault",), "Are my photos backed up?"),
    App("memories", "Memories", "📸", "Remember the trip.", "memories.html",
        "Trip recaps, stats, and photos from your Expeditions.", OUTDOORS, ("expeditions",), "Show me my last trip."),
    App("maps", "Maps", "🗺", "Know the ground.", "maps.html",
        "Waypoints, a real offline basemap, and official trail maps.", OUTDOORS, ("maps",),
        "Which trail maps do I have?"),
    App("navigation", "Navigation", "🧭", "Find the way.", "navigation.html",
        "Waypoints, distance/bearing, and sun/moon reference.", OUTDOORS, ("waypoints",),
        "How far is camp from the trailhead?"),
    App("knowledge", "Knowledge", "📚", "The offline library.", "knowledge.html",
        "Offline reference material and personal knowledge base.", KNOW, ("knowledge", "plans", "plan_buying", "plan_saving"), "How do I purify water?"),
    App("toolbox", "Toolbox", "🧰", "Quick tools.", "toolbox.html",
        "Calculators, unit conversion, and other quick tools.", KNOW, ("toolbox",), "Convert 5 gallons to liters."),
    App("lab", "The Lab", "🧪", "Experiments and sensors.", "lab.html",
        "Sensor testing, experiments, calibration, and graphs.", KNOW, ("lab",), "Start a temperature experiment."),
    App("field_kit", "Field Kit", "🛠", "Devices and scripts.", "field-kit.html",
        "Detect and manage connected devices; run your own scripts.", KNOW, ("field_kit", "security"),
        "What devices are connected?"),
    App("passwords", "Passwords", "🔐", "Every login, locked.", "passwords.html",
        "Your logins in a vault only your master password opens; MIA's assistant never sees them (DEC-0035).", KNOW,
        (), ""),
    App("files", "Files", "🗂", "Your files.", "files.html", "Browse and manage local files and data.", KNOW, ("files",),
        "What's in my MIA folder?"),
    App("music", "Music", "🎵", "Your music.", "music.html", "Local audio library, playlists, and playback.", KNOW,
        ("music",), "Play something relaxing."),
    App("operating_journal", "Operating Journal", "🧭", "How you mean to live, and how you do.", "operating.html",
        "Your values, priorities, ideal day and week and rules, each checked against your records or rated by you "
        "(DEC-0097).", LIFE, ("operating_journal",), "Am I living how I said I want to?"),
    App("life_notes", "Kept", "📌", "What you said you'd do.", "kept.html",
        "The promises, decisions, ideas and goals set aside you asked MIA to keep, from what you said (DEC-0054).",
        LIFE, ("life_notes",), "What did I promise?"),
    App("play", "Play", "🏓", "Games and sports, counted.", "play.html",
        "Games and sports you play: who with, how long, how hard, and your training load (DEC-0098).", LIFE, ("play",),
        "Played pickleball for an hour, it was hard."),
    App("good_news", "Good News Radio", "📻", "What went right today.", "news.html",
        "Good news from credible sources, each story saying how it's known, read by four radio personalities "
        "(DEC-0096).", KNOW, (), "What's the good news?"),
    App("sight", "Look", "👁", "Show MIA something.", "look.html",
        "A photo and a question (what is this, read this label, inspect this part), answered on your PC; never who "
        "a person is (build plan step 15).", KNOW, (), "What is this?"),
    App("assistant", "MIA Assistant", "🗨", "Always here. Always with you.", "assistant.html",
        "Conversational assistant and local AI.", KNOW, ("communication", "undo", "system", "memory"), "Undo that."),
    App("browser", "Browser", "🌐", "She browses. You approve.", "browser.html",
        "MIA's own web browser: what she's on, the steps waiting for your OK with their screenshots, and the tasks you "
        "taught her by showing (DEC-0117).", KNOW, ("browser",), "Open the county website."),
    App("diagnostics", "Diagnostics", "🩺", "How MIA is doing.", None,
        "System health, logs, and hardware status.", KNOW, (), "How is my system health?"),
    App("module_browser", "Apps", "🧩", "Everything MIA can do.", "apps.html",
        "View, enable/disable, install, and rescan modules.", KNOW, ()),
    App("settings", "Settings", "⚙", "Make MIA yours.", None,
        "Configure MIA — theme, user info, module options.", KNOW, ("accessibility", "apps", "starters", "humor", "backup"),
        "Make the text bigger."),
)
APPS_BY_ID = {a.module_id: a for a in APPS}
# Apps that exist only as web screens (no PySide6 module of their own).
WEB_ONLY = frozenset({"calendar", "reward_shop", "business", "security", "vault", "insurance", "passwords", "flock", "freedom", "compliance", "dungeon", "issues",
                      "operating_journal", "play", "good_news", "sight", "life_notes", "browser"})
# Apps folded into others (Zac, 2026-10-16): Garage holds vehicles, equipment
# and tools; Real Estate holds buildings and appliances; the Calendar shows all
# upkeep. Shown nowhere; the desktop keeps their modules loaded only because
# Garage and Greenhouse open Maintenance to add and edit things.
# Zac, 2026-10-16: the Dashboard said what Home says; Home took its Upcoming
# list and the Dashboard went (its /api/dashboard data still feeds Home).
RETIRED = frozenset({"maintenance", "property", "dashboard"})

# Never personal: general encouragement, one a day (STATIC).
SAYINGS = (
    "Small steps every day create big results.",
    "Progress isn't about being perfect. It's about showing up.",
    "Do the next right thing.",
    "Take care of the things that take care of you.",
    "One thing at a time. Then the next.",
    "A little done is more than a lot planned.",
    "Rest counts too.",
)

# Where each quick action goes: MIA Assistant (web/assistant.html), with
# a question asked straight away (ask=) or a sentence started (draft=).
QUICK_ACTIONS = (
    {"id": "quick_add", "label": "Quick Add", "icon": "➕", "talk": "Add ", "href": "assistant.html?draft=Add%20"},
    {"id": "voice", "label": "Voice", "icon": "🎙", "talk": "", "href": "assistant.html?voice=1"},
    {"id": "calendar", "label": "Calendar", "icon": "📅", "talk": "What's on my calendar this week?",
     "href": "calendar.html"},
    {"id": "journal", "label": "Journal", "icon": "📓", "talk": "I want to journal.",
     "href": "assistant.html?draft=I%20want%20to%20journal."},
    {"id": "assistant", "label": "MIA Assistant", "icon": "🗨", "talk": "", "href": "assistant.html"},
)


def _visible(context, app: App) -> bool:
    """Whether an app shows in this person's sidebar: Home always; never a retired app; for a child only the
    allowed ones; never one their focus tucks away (shown when settings can't be read).
    """
    from core.child_accounts import app_allowed

    if app.module_id == "web_home":
        return True
    if app.module_id in RETIRED:
        return False
    try:
        if not app_allowed(context, app.module_id):
            return False
        from core.focus_presets import ALWAYS_VISIBLE, current

        hidden = set(current(context)[2]) - set(ALWAYS_VISIBLE)
        return app.module_id not in hidden
    except Exception:  # a headless context without settings: show it
        log.debug("App visibility unavailable for %s", app.module_id, exc_info=True)
        return True


def _level(profile) -> dict:
    """A profile's level, total XP, and how far into the level it is."""
    from core.leveling import compute_level_progress

    total = int(getattr(profile, "total_xp", 0) or 0)
    level, into, needed = compute_level_progress(total)
    return {"level": level, "total_xp": total, "xp_into_level": into, "xp_for_level": needed}


def _profile(context):
    """The signed-in person's id and profile (None when there's none)."""
    from core.person_settings import person_id

    pid = person_id(context)
    profiles = getattr(context, "profiles", None)
    return pid, (profiles.get_profile(pid) if profiles is not None and pid else None)


def date_text(day: date) -> str:
    """Pure logic. "Tue, Sep 16, 2026"."""
    return f"{day:%a}, {day:%b} {day.day}, {day.year}"


def greeting(hour: int, name: Optional[str]) -> str:
    """Pure logic. The concept's "Good morning, <name>"."""
    part = "Good morning" if 4 <= hour < 12 else "Good afternoon" if 12 <= hour < 17 else "Good evening"
    return f"{part}, {name}" if name else part


def shell(context, today: Optional[date] = None) -> dict:
    """The shared frame's data (/api/shell): the person and their level, the date, the apps they can open on the web
    (each with its life area and its ask, shown as "Say: …" on its screen), the sidebar's areas with their hubs
    (DEC-0129, core/web_areas.py), their favorites, the ones still on the PC only, the screens MIA made, the owner's
    pages, sound, places, and the person's display style (DEC-0135: spatial or cards).
    """
    from core.child_accounts import is_child

    today = today or date.today()
    pid, profile = _profile(context)
    child = bool(pid and is_child(context, pid))
    apps = [a for a in APPS if _visible(context, a)]
    return {
        "person": {"profile_id": pid, "name": getattr(profile, "name", None), "child": child,
                   **_level(profile)},
        "date": date_text(today),
        # Each app's ask (DEC-0125): the frame shows it under the page's title as "Say: …", its voice twin.
        "apps": [{"id": a.module_id, "name": a.name, "icon": a.icon, "tagline": a.tagline, "page": a.page,
                  "group": a.group, "ask": a.ask} for a in apps if a.page],
        # The sidebar's order (2026-11-07): Start Here and the favorites, then each life area under its heading.
        "groups": list(GROUPS),
        # DEC-0129 (2026-11-08): the sidebar's areas, each with its hub and the apps and pages in it (core/web_areas.py).
        "areas": _areas(context),
        "favorites": _favorites(context),
        "on_pc_only": [a.name for a in apps if not a.page],
        "made": _made(context),
        "owner": _owner_pages(context, pid),
        "weather": {"status": "PLANNED", "text": None},
        "sound": _sound(context),
        "places": _places(context),
        # DEC-0135: the person's look; the page decides "auto" itself (only it knows it's on a phone)
        "display": _display(context),
    }


def _areas(context) -> list:
    """The sidebar's areas (core/web_areas.sidebar), [] if they can't be put together."""
    try:
        from core.web_areas import sidebar

        return sidebar(context)
    except Exception:
        log.exception("Shell: areas failed")
        return []


def _favorites(context) -> list:
    """This person's starred apps, for the top of the sidebar ([] when settings can't be read)."""
    try:
        from core.focus_presets import favorite_apps

        return favorite_apps(context)
    except Exception:
        log.debug("Favorites unavailable", exc_info=True)
        return []


def _owner_pages(context, pid) -> list:
    """Pages only the PC's owner has (the first account): the council (build plan step 16) and the PC's check-up."""
    from core.person_settings import _is_first_account

    try:
        if pid and _is_first_account(context, pid):
            return [{"id": "council", "name": "The Council", "icon": "assistant", "page": "council.html"},
                    {"id": "diagnostics", "name": "Diagnostics", "icon": "assistant", "page": "diagnostics.html"}]
    except Exception:
        log.debug("Shell: owner pages unavailable", exc_info=True)
    return []


def _made(context) -> list:
    """Screens MIA made for this person and they published (core/creations.py, DEC-0091), for the sidebar."""
    store = getattr(context, "creations", None)
    if store is None:
        return []
    try:
        return [{"id": c["id"], "name": c["title"], "icon": store.shown(c["id"])["spec"].get("icon", "apps"),
                 "page": f"made.html?id={c['id']}"} for c in store.published()]
    except Exception:
        log.exception("Shell: creations failed")
        return []


def _places(context) -> list:
    """Location quests the phone watches for (core/places.py), only when switched on."""
    try:
        from core.places import watched

        return watched(context)
    except Exception:
        log.exception("Shell: places failed")
        return []


def _display(context) -> dict:
    """The person's display style (core/display_style.py): {"style": "auto" | "spatial" | "cards"}."""
    from core.display_style import style_of

    try:
        return {"style": style_of(context)}
    except Exception:
        log.exception("Shell: display style failed")
        return {"style": "auto"}


def _sound(context) -> dict:
    """The person's sound settings (web/sound.js plays them)."""
    from core import person_settings

    return {"on": bool(person_settings.get(context, "sound.on", True)),
            "voice": bool(person_settings.get(context, "sound.voice", False))}


def plural(n: int, word: str, many: str = "") -> str:
    """Pure logic. "1 recipe", "3 recipes", "1 property", "2 properties"."""
    return f"{n} {word if n == 1 else (many or word + 's')}"


def _glance(state: dict) -> list[dict]:
    """Pure logic. The at-a-glance cards, from Life State v2 (Money with its net worth when it's known)."""
    from core.region import money

    cards = []

    def card(app_id, title, line, tone="calm"):
        app = APPS_BY_ID[app_id]
        cards.append({"app": app_id, "icon": app.icon, "title": title, "line": line, "tone": tone, "page": app.page})

    finances = state.get("finances") or {}
    if finances.get("available") and not finances.get("hidden"):
        bills = finances.get("bills_due") or []
        plan = finances.get("monthly_plan") or {}
        parts = []
        if bills:
            first = bills[0]
            when = "today" if first.get("days") == 0 else f"in {first['days']}d" if first.get("days", 0) > 0 \
                else f"{-first['days']}d late"
            parts.append(f"{first['name']} {money(first['amount'])} {when}")
        if plan.get("gap") is not None:
            parts.append(f"{money(plan['gap'])} left each month after bills")
        worth = (finances.get("net_worth") or {}).get("total")
        if worth is not None:
            parts.append(f"net worth {money(worth)}")
        if parts:
            late = any((b.get("days") or 0) < 0 for b in bills)
            card("budget", "Money", " · ".join(parts), "attention" if late else "calm")
    assets = (state.get("assets") or {}).get("items") or []
    overdue = sum(a.get("tasks_overdue") or 0 for a in assets)
    if assets:
        nxt = next((a for a in assets if a.get("next_task")), None)
        line = f"{len(assets)} tracked"
        if overdue:
            line += f" · {overdue} overdue"
        if nxt:
            line += f" · next: {nxt['next_task']['title']} ({nxt['name']})"
        card("garage", "Equipment", line, "attention" if overdue else "calm")
    props = (state.get("properties") or {}).get("items") or []
    if props:
        equity = sum(p.get("equity") or 0 for p in props)
        card("real_estate", "Real Estate", f"{plural(len(props), 'property', 'properties')} · {money(equity)} equity")
    kitchen = state.get("kitchen") or {}
    if kitchen.get("status") not in (None, "PLANNED") and (kitchen.get("pantry_items") or kitchen.get("recipes")):
        expiring = kitchen.get("expiring_soon") or []
        grocery = [g for g in kitchen.get("grocery_list") or [] if not g.get("checked")]
        bits = [plural(kitchen.get("recipes") or 0, "recipe"), f"{len(grocery)} on the grocery list"]
        if expiring:
            bits.append(f"{expiring[0]['name']} expires in {expiring[0]['days']}d")
        card("kitchen", "Kitchen", " · ".join(bits), "attention" if expiring else "calm")
    workout = state.get("workout") or {}
    if workout.get("status") not in (None, "PLANNED"):
        last = workout.get("last_session")
        line = f"{plural(workout.get('sessions') or 0, 'session')} this week"
        if last:
            line += f" · last: {last.get('template') or 'a session'} ({last.get('date')})"
        card("workout", "Workout", line)
    ms = state.get("missions_and_skills") or {}
    if ms.get("status") not in (None, "PLANNED"):
        streaks = ms.get("streaks") or []
        line = f"{ms.get('active_missions') or 0} active"
        if streaks:
            best = max(streaks, key=lambda s: s.get("days") or s.get("streak") or 0)
            line += f" · best streak {best.get('days') or best.get('streak') or 0}d"
        card("missions", "Missions", line)
    return cards


def glance_counts(observations: dict, waiting: list) -> list[dict]:
    """Pure logic. The glance cards that come from outside Life State: Observations (what MIA noticed: the findings
    across apps and the open insights, Needs You in amber, never red) and the Inbox (captures waiting to be filed,
    the oldest named). No card for either when there's nothing; each card is shaped as `_glance`'s are."""
    cards = []

    def card(app_id, title, line, tone):
        app = APPS_BY_ID[app_id]
        cards.append({"app": app_id, "icon": app.icon, "title": title, "line": line, "tone": tone, "page": app.page})

    found = observations.get("findings") or []
    insights = [i for g in observations.get("insights") or [] for i in g.get("items") or []]
    if found or insights:
        needs = sum(1 for f in found if f.get("kind") == "Needs You")
        first = (found or insights)[0]
        line = plural(len(found) + len(insights), "thing") + " noticed"
        line += (f" · {needs} need{'s' if needs == 1 else ''} you" if needs else "") + f" · {first['title']}"
        card("observations", "Observations", line, "attention" if needs else "calm")
    if waiting:
        oldest = waiting[0]
        card("inbox", "Inbox", plural(len(waiting), "capture") + " to file · " + oldest, "attention")
    return cards


def _more_glance(context, today: date) -> list[dict]:
    """Home's Observations and Inbox glance cards (`glance_counts`), read from their stores; a store that fails to
    read gives no card, never an error."""
    from core.observations_web import screen

    try:
        observations = screen(context, today)
    except Exception:
        log.exception("Home: observations failed")
        observations = {}
    inbox = getattr(context, "inbox", None)
    try:
        waiting = [i.subject or i.vendor or (i.files[0] if i.files else "a capture") for i in inbox.pending()] \
            if inbox is not None else []
    except Exception:
        log.exception("Home: inbox failed")
        waiting = []
    return glance_counts(observations, waiting)


def dashboard(context, now: Optional[datetime] = None) -> dict:
    """Home's data: the greeting, the date, what needs doing today (from the life state's due items, each with its
    kind), what's coming, the status strip, the one thing MIA noticed across apps, quick actions, the glance (Life
    State's cards, then Observations and the Inbox), recent wins (only real wins, never spending), something to remember,
    and the life cards (life_cards: music, good news, recent pictures, the trip).
    """
    from core.context_assembler import assemble_life_state_v2

    now = now or datetime.now()
    today = now.date()
    _pid, profile = _profile(context)
    state = assemble_life_state_v2(context, today)
    due = (state.get("due") or {}).get("items") or []
    page_of = {a.module_id: a.page for a in APPS}
    page_of.update({"maintenance": "calendar.html"})

    def item(d):
        return {**d, "page": page_of.get(d.get("module_id")), **due_kind(d.get("when"))}

    focus = [item(d) for d in due if d.get("when") in ("overdue", "today", "waiting")][:8]
    upcoming = [item(d) for d in due if d.get("when") == "soon"][:6]
    wins = [e for e in ((state.get("recent_wins") or {}).get("latest") or []) if e.get("type") in _WINS][:5]
    return {
        "greeting": greeting(now.hour, getattr(profile, "name", None)),
        "subtitle": "Another day to build the life you want.",
        "date": date_text(today),
        "focus": focus,
        "upcoming": upcoming,
        # The canvas's status strip (DEC-0113): counts the engine already has, never a guess.
        "strip": home_strip(focus, upcoming, wins, today),
        "finding": _top_finding(context, today),
        "saying": SAYINGS[today.toordinal() % len(SAYINGS)],
        "quick_actions": list(QUICK_ACTIONS),
        "glance": _glance(state) + _more_glance(context, today),
        # "latest" is every event; only these are wins (no "Spent $40" on Home).
        "wins": wins,
        "child": bool((state.get("person") or {}).get("child")),
        "remember": _remember(context, today),
        # DEC-0129 (Zac, 2026-11-08): what's playing, today's good news, recent pictures, the current or next trip.
        "life": life_cards(context, today),
    }


PICTURES = 6  # recent pictures on the Dashboard


def span_text(start: str, end: str) -> str:
    """Pure logic. A trip's dates in words: "Nov 14", "Nov 14 – 16", "Nov 30 – Dec 2" ("" when there's no start)."""
    try:
        a = date.fromisoformat((start or "")[:10])
    except ValueError:
        return ""
    try:
        b = date.fromisoformat((end or "")[:10])
    except ValueError:
        b = a
    first = f"{a:%b} {a.day}"
    if b <= a:
        return first
    return f"{first} – {b.day}" if (a.year, a.month) == (b.year, b.month) else f"{first} – {b:%b} {b.day}"


def pick_trip(trips: list, today: date) -> Optional[dict]:
    """Pure logic. The trip for the Dashboard: one under way, else the next planned (soonest), else one that ended in
    the last two weeks; None when there's none. {id, name, status, when, words}."""
    def card(t, words: str) -> dict:
        return {"id": t.trip_id, "name": t.name, "status": t.status, "when": span_text(t.start_date, t.end_date),
                "words": words}

    active = [t for t in trips if t.status == "active"]
    if active:
        return card(active[0], "Under way")
    ahead = sorted((t for t in trips if t.status == "planned" and t.start_date and t.start_date >= today.isoformat()),
                   key=lambda t: t.start_date)
    if ahead:
        days = (date.fromisoformat(ahead[0].start_date) - today).days
        return card(ahead[0], "Today" if days == 0 else "Tomorrow" if days == 1 else f"In {days} days")
    done = sorted((t for t in trips if t.status == "completed" and (t.end_date or t.start_date)),
                  key=lambda t: t.end_date or t.start_date, reverse=True)
    if done:
        ended = date.fromisoformat((done[0].end_date or done[0].start_date)[:10])
        if (today - ended).days <= 14:
            return card(done[0], "Just back")
    return None


def life_cards(context, today: date) -> dict:
    """The Dashboard's life cards (DEC-0129): {music: what's playing or None, news: today's first good-news story or
    None, pictures: the newest photos kept at home, trip: pick_trip}. Each source is optional; a failure leaves its
    card out."""
    out = {"music": None, "news": None, "pictures": [], "trip": None}
    try:
        music = getattr(context, "music", None)
        now = music.now_playing() if music is not None else None
        if now is not None:
            out["music"] = {"title": now.title, "artist": now.artist, "playing": bool(now.is_playing)}
    except Exception:
        log.exception("Dashboard: music failed")
    try:
        from core.good_news import screen as news_screen

        news = news_screen(context)
        if news.get("on") and news.get("stories"):
            first = news["stories"][0]
            out["news"] = {"title": first["title"], "tag": first.get("tag", ""), "count": len(news["stories"])}
    except Exception:
        log.exception("Dashboard: good news failed")
    try:
        vault = getattr(context, "memory_vault", None)
        if vault is not None:
            photos = sorted((i for i in vault.items.values() if i.get("kind") == "photo" and i.get("on_pc")),
                            key=lambda i: i.get("taken_at") or "", reverse=True)[:PICTURES]
            out["pictures"] = [{"sha": i["sha"], "url": f"/api/vault/photo/{i['sha']}", "when": (i.get("taken_at") or "")[:10]}
                               for i in photos]
    except Exception:
        log.exception("Dashboard: pictures failed")
    try:
        trips = getattr(context, "trips", None)
        out["trip"] = pick_trip(trips.all_trips(), today) if trips is not None else None
    except Exception:
        log.exception("Dashboard: trip failed")
    return out


from core.life_events import WINS as _WINS  # noqa: E402

# What kind of thing a due item is, as the label on its row (DEC-0113: every row says what it is). Overdue is amber,
# "needs you", not red: a late chore is a nudge, never a failure (DEC-0014).
DUE_KINDS = {"overdue": ("Overdue", "attention"), "today": ("Today", "accent"), "waiting": ("Waiting", "quiet"),
             "soon": ("Soon", "quiet")}


def due_kind(when: Optional[str]) -> dict:
    """Pure logic. The label and tone for a due item's row, from its `when`: {"kind": "Overdue", "tone": "attention"}."""
    label, tone = DUE_KINDS.get(when or "", ("", "quiet"))
    return {"kind": label, "tone": tone}


def home_strip(focus: list, upcoming: list, wins: list, today: date) -> list[dict]:
    """Pure logic. Home's three tiles: what needs you now, what's coming in the next days, and what got done today
    (only real wins, from the life events). Each is a count the engine already has.
    """
    done_today = sum(1 for w in wins if str(w.get("at") or "").startswith(today.isoformat()))
    return [
        {"label": "Needs You", "value": len(focus), "tone": "attention" if focus else "ok"},
        {"label": "Coming Up", "value": len(upcoming), "tone": "accent"},
        {"label": "Done Today", "value": done_today, "tone": "ok"},
    ]


def _top_finding(context, today: date) -> Optional[dict]:
    """The one thing MIA noticed across apps that Home leads with (core/findings.py), with why, how sure, the app it
    belongs to (its page) and the next step; None when there's nothing, or a findings rule fails.
    """
    try:
        from core.findings import findings

        found = findings(context, today)
    except Exception:
        log.exception("Home: findings failed")
        return None
    if not found:
        return None
    f = found[0]
    app = APPS_BY_ID.get(f.app)
    return {"title": f.title, "claim": f.claim, "why": f.why, "next": f.next_step, "sure": f.sureness,
            "app": f.app, "app_name": app.name if app else "", "page": app.page if app else None}


def _remember(context, today: date) -> list[dict]:
    """MIA Remembers (DEC-0029): what you told her, as it's about to matter."""
    from core.memory_callbacks import callbacks

    try:
        return callbacks(context, today)[:3]
    except Exception:
        log.exception("Home: memory callbacks failed")
        return []



def _first_sentence(text: str) -> str:
    """Pure logic. A tool's description, as one line for a person."""
    text = " ".join((text or "").split())
    for end in (". ", "? "):
        if end in text:
            text = text[: text.index(end) + 1]
    return text.rstrip()


_VERBS = {"get": "See", "list": "See", "show": "See", "check": "Check", "lookup": "Look up", "search": "Search",
          "rm": "Remove", "del": "Delete"}
_WORDS = {"xp": "XP", "apr": "APR", "mia": "MIA", "pdf": "PDF", "id": "ID", "rsvp": "RSVP", "url": "URL"}


def tool_label(name: str) -> str:
    """Pure logic. A tool's name, said for a person: "add_maintenance_task"
    -> "Add maintenance task", "get_life_events" -> "See life events"."""
    words = [w for w in (name or "").split("_") if w]
    if not words:
        return ""
    first = _VERBS.get(words[0], words[0].capitalize())
    return " ".join([first] + [_WORDS.get(w, w) for w in words[1:]])


def apps_page(context) -> dict:
    """The Apps page (DEC-0017): every app MIA has, grouped by life area,
    with what it's for, whether it's on the web yet, whether it's shown in
    this person's sidebar, and what MIA can do in it (the Assistant tools
    of its domains, so even an app without a web screen yet is reachable
    by talking to MIA). Child-safe: a child sees only their apps and tools."""
    from core.child_accounts import app_allowed, tool_allowed
    from core.focus_presets import ALWAYS_VISIBLE, favorite_apps

    favorites = favorite_apps(context)
    registry = getattr(context, "assistant_actions", None)
    actions = list(getattr(registry, "_actions", {}).values()) if registry is not None else []
    by_domain: dict[str, list] = {}
    for action in actions:
        by_domain.setdefault(action.domain, []).append(action)

    def tools_of(app: App) -> list[dict]:
        found = []
        for domain in app.domains:
            if not tool_allowed(context, domain):
                continue
            for action in sorted(by_domain.get(domain, ()), key=lambda a: a.name):
                found.append({"name": action.name, "does": tool_label(action.name),
                              "detail": _first_sentence(action.description)})
        return found

    groups = []
    for group in GROUPS:
        apps = []
        for app in APPS:
            if app.group != group or app.module_id in RETIRED or not app_allowed(context, app.module_id):
                continue
            apps.append({
                "id": app.module_id, "name": app.name, "icon": app.icon, "tagline": app.tagline,
                "description": app.description, "page": app.page, "on_web": bool(app.page),
                "shown": _visible(context, app), "can_hide": app.module_id not in ALWAYS_VISIBLE,
                "ask": app.ask, "tools": tools_of(app),
                "favorite": app.module_id in favorites,
            })
        if apps:
            groups.append({"name": group, "apps": apps})
    total_apps = sum(len(g["apps"]) for g in groups)
    allowed = {a["id"] for g in groups for a in g["apps"]}
    return {
        "groups": groups,
        "favorites": [f for f in favorites if f in allowed],
        "counts": {"apps": total_apps, "on_web": sum(a["on_web"] for g in groups for a in g["apps"]),
                   "tools": len({t["name"] for g in groups for a in g["apps"] for t in a["tools"]})},
    }
