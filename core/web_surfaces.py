"""
core.web_surfaces
===================

What the web front end's shell and Home show (2026-10-06, DEC-0017:
the web becomes all of MIA, function first, in the concept's look).
Assembled here, in code, so `web/` holds no logic (DEC-0013): which
apps a person sees, their level and XP, the greeting, Today's Focus,
the upcoming list and the at-a-glance cards.

- `shell(context)`: the sidebar (the person's apps, child-safe and
  respecting the apps they've tucked away), their level and XP, today's
  date. Served as `/api/shell`.
- `dashboard(context)`: the Dashboard (the concept's "Good morning",
  Today's Focus, a line of encouragement, quick actions, Upcoming and
  at-a-glance cards). Served as `/api/dashboard`. Home itself
  (`web/index.html`) is MIA's presence and a chat with her (Zac,
  2026-10-06), reading Life State.
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
        ("today", "calendar", "alarms", "projects", "life_events", "links", "why"), "What's on today?"),
    App("greenhouse", "Greenhouse", "🌱", "Grow food. Grow freedom.", None,
        "At-a-glance status for garden, greenhouse, and aquaponics assets.", HOME, ("maintenance",),
        "What needs doing in the greenhouse?"),
    App("garage", "Garage", "🚗", "Keep it running. Keep it ready.", "garage.html",
        "At-a-glance status for vehicles and motorized equipment.", HOME, ("maintenance",),
        "What's overdue on my vehicles?"),
    App("kitchen", "Kitchen", "🍳", "Good food. Good mood.", "kitchen.html",
        "Recipes, pantry, grocery list, and meal tracking.", HOME, ("kitchen", "groceries"),
        "What can I make with what's in the pantry?"),
    App("household", "Household", "🧺", "A home that runs itself.", None,
        "Daily and weekly household routines — laundry, dishes, chores.", HOME, ("household",),
        "I did the dishes."),
    App("workout", "Workout", "🏋", "Stronger body. Clearer mind.", "workout.html",
        "Exercises, templates, guided sessions, and progress.", LIFE, ("workout",), "Log a 30 minute workout."),
    App("real_estate", "Real Estate", "🏘", "Cash flow. Equity. Freedom.", "real-estate.html",
        "Property values, equity, rental income, and linked maintenance.", MONEY, ("real_estate",),
        "How are my rentals doing this month?"),
    App("missions", "Missions", "🏆", "Explore. Complete. Level up.", "missions.html",
        "Gamified goals and objectives, tied to a trip or general.", LIFE, ("missions",),
        "Add a mission to build a chicken coop."),
    App("skills", "Skills", "⚔", "Do the thing. Earn the level. Unlock the next thing.", "skills.html",
        "My Hero's Path — skill tree and character progression.", LIFE, (), "Which skills am I growing?"),
    App("budget", "Money", "💰", "Know where it goes.", "finances.html",
        "Household bills, income, expenses, and tax-relevant totals.", MONEY,
        ("budget", "debts", "homestead_costs", "business_use", "business_tags"), "Which debt should I pay first?"),
    App("maintenance", "Maintenance", "🔧", "Everything you own, cared for.", None,
        "Recurring upkeep tracking for vehicles, equipment, appliances, property, and tools.", HOME,
        ("maintenance", "ownership"), "I put 120 hours on the mower."),
    App("property", "Property", "🏠", "The house, the appliances, the tools.", None,
        "At-a-glance status for the house, appliances, and tools.", HOME, ("inventory",),
        "Do I have any furnace filters left?"),
    App("workshop", "Workshop", "🔩", "Parts, jobs and products.", None,
        "Component inventory, fabrication materials/jobs/products, and a sales ledger.", MONEY,
        ("components", "materials", "jobs", "products", "ledger"), "How much plywood do I have?"),
    App("power", "Power", "🔋", "Energy, tracked.", None,
        "Battery status and manual energy/utility tracking.", HOME, ("power",), "How's the battery?"),
    App("character", "Character", "👤", "Your story so far.", None,
        "A living record of what you've actually done.", LIFE, (), "What have I done this week?"),
    App("observations", "Observations", "🔍", "What MIA noticed.", None,
        "What MIA has noticed across your maintenance and missions.", LIFE, (), "What have you noticed lately?"),
    App("relationships", "People & Pets", "👥", "The ones who matter.", None,
        "Relationship profiles and pet profiles.", LIFE, ("relationships",), "When is the next birthday?"),
    App("notes", "Notes", "📝", "Write it down.", None,
        "Dated, searchable, taggable journal entries.", LIFE, ("notes", "journal", "private_journal"),
        "Make a note: call the plumber Friday."),
    App("classroom", "Classroom", "🎓", "Keep learning.", None,
        "Your own subjects, courses, and lessons.", LIFE, ("classroom", "textbooks"), "Quiz me on chapter 2."),
    App("inbox", "Inbox", "📥", "Paperwork, handled.", None,
        "Receipts, manuals and documents MIA files for you.", MONEY, ("inbox", "email"),
        "What's waiting in my inbox?"),
    App("expeditions", "Expeditions", "🏕", "Plan the trip.", None,
        "Expedition Mode: trip routes, gear, weather, and logged speed/distance for any outing.", OUTDOORS,
        ("expeditions",), "Plan a weekend camping trip."),
    App("memories", "Memories", "📸", "Remember the trip.", None,
        "Trip recaps, stats, and photos from your Expeditions.", OUTDOORS, (), "Show me my last trip."),
    App("maps", "Maps", "🗺", "Know the ground.", None,
        "Waypoints, a real offline basemap, and official trail maps.", OUTDOORS, ("maps",),
        "Which trail maps do I have?"),
    App("navigation", "Navigation", "🧭", "Find the way.", None,
        "Waypoints, distance/bearing, and sun/moon reference.", OUTDOORS, ("waypoints",),
        "How far is camp from the trailhead?"),
    App("knowledge", "Knowledge", "📚", "The offline library.", None,
        "Offline reference material and personal knowledge base.", KNOW, (), "How do I purify water?"),
    App("toolbox", "Toolbox", "🧰", "Quick tools.", None,
        "Calculators, unit conversion, and other quick tools.", KNOW, ("toolbox",), "Convert 5 gallons to liters."),
    App("lab", "The Lab", "🧪", "Experiments and sensors.", None,
        "Sensor testing, experiments, calibration, and graphs.", KNOW, ("lab",), "Start a temperature experiment."),
    App("field_kit", "Field Kit", "🛠", "Devices and scripts.", None,
        "Detect and manage connected devices; run your own scripts.", KNOW, ("field_kit", "security"),
        "What devices are connected?"),
    App("files", "Files", "🗂", "Your files.", None, "Browse and manage local files and data.", KNOW, ()),
    App("music", "Music", "🎵", "Your music.", None, "Local audio library, playlists, and playback.", KNOW,
        ("music",), "Play something relaxing."),
    App("assistant", "MIA Assistant", "🗨", "Talk it through.", None,
        "Conversational assistant and local AI.", KNOW, ("communication", "undo", "system"), "Undo that."),
    App("diagnostics", "Diagnostics", "🩺", "How MIA is doing.", None,
        "System health, logs, and hardware status.", KNOW, (), "How is the computer doing?"),
    App("module_browser", "Apps", "🧩", "Everything MIA can do.", "apps.html",
        "View, enable/disable, install, and rescan modules.", KNOW, ()),
    App("settings", "Settings", "⚙", "Make MIA yours.", None,
        "Configure MIA — theme, user info, module options.", KNOW, ("accessibility", "apps", "starters"),
        "Make the text bigger."),
)
APPS_BY_ID = {a.module_id: a for a in APPS}

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

QUICK_ACTIONS = (
    {"id": "quick_add", "label": "Quick Add", "icon": "➕", "talk": "Add "},
    {"id": "voice", "label": "Voice", "icon": "🎙", "talk": ""},
    {"id": "calendar", "label": "Calendar", "icon": "📅", "talk": "What's on my calendar this week?"},
    {"id": "journal", "label": "Journal", "icon": "📓", "talk": "I want to journal."},
    {"id": "assistant", "label": "MIA Assistant", "icon": "🗨", "talk": ""},
)


def _visible(context, app: App) -> bool:
    from core.child_accounts import app_allowed

    if app.module_id == "web_home":
        return True
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
    from core.leveling import compute_level_progress

    total = int(getattr(profile, "total_xp", 0) or 0)
    level, into, needed = compute_level_progress(total)
    return {"level": level, "total_xp": total, "xp_into_level": into, "xp_for_level": needed}


def _profile(context):
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
    from core.child_accounts import is_child

    today = today or date.today()
    pid, profile = _profile(context)
    child = bool(pid and is_child(context, pid))
    apps = [a for a in APPS if _visible(context, a)]
    return {
        "person": {"profile_id": pid, "name": getattr(profile, "name", None), "child": child,
                   **_level(profile)},
        "date": date_text(today),
        "apps": [{"id": a.module_id, "name": a.name, "icon": a.icon, "tagline": a.tagline, "page": a.page}
                 for a in apps if a.page],
        "on_pc_only": [a.name for a in apps if not a.page],
        "weather": {"status": "PLANNED", "text": None},
    }


def plural(n: int, word: str, many: str = "") -> str:
    """Pure logic. "1 recipe", "3 recipes", "1 property", "2 properties"."""
    return f"{n} {word if n == 1 else (many or word + 's')}"


def _glance(state: dict) -> list[dict]:
    """Pure logic. The at-a-glance cards, from Life State v2."""
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


def dashboard(context, now: Optional[datetime] = None) -> dict:
    from core.context_assembler import assemble_life_state_v2

    now = now or datetime.now()
    today = now.date()
    _pid, profile = _profile(context)
    state = assemble_life_state_v2(context, today)
    due = (state.get("due") or {}).get("items") or []
    page_of = {a.module_id: a.page for a in APPS}
    page_of.update({"budget": "finances.html", "maintenance": "garage.html"})

    def item(d):
        return {**d, "page": page_of.get(d.get("module_id"))}

    return {
        "greeting": greeting(now.hour, getattr(profile, "name", None)),
        "subtitle": "Another day to build the life you want.",
        "date": date_text(today),
        "focus": [item(d) for d in due if d.get("when") in ("overdue", "today", "waiting")][:8],
        "upcoming": [item(d) for d in due if d.get("when") == "soon"][:6],
        "saying": SAYINGS[today.toordinal() % len(SAYINGS)],
        "quick_actions": list(QUICK_ACTIONS),
        "glance": _glance(state),
        "wins": ((state.get("recent_wins") or {}).get("latest") or [])[:5],
        "child": bool((state.get("person") or {}).get("child")),
    }


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
    from core.focus_presets import ALWAYS_VISIBLE

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
            if app.group != group or not app_allowed(context, app.module_id):
                continue
            apps.append({
                "id": app.module_id, "name": app.name, "icon": app.icon, "tagline": app.tagline,
                "description": app.description, "page": app.page, "on_web": bool(app.page),
                "shown": _visible(context, app), "can_hide": app.module_id not in ALWAYS_VISIBLE,
                "ask": app.ask, "tools": tools_of(app),
            })
        if apps:
            groups.append({"name": group, "apps": apps})
    total_apps = sum(len(g["apps"]) for g in groups)
    return {
        "groups": groups,
        "counts": {"apps": total_apps, "on_web": sum(a["on_web"] for g in groups for a in g["apps"]),
                   "tools": len({t["name"] for g in groups for a in g["apps"] for t in a["tools"]})},
    }
