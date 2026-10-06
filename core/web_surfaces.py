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
- `home(context)`: the Home dashboard (the concept's "Good morning",
  Today's Focus, a line of encouragement, quick actions, Upcoming and
  at-a-glance cards). Served as `/api/home`.

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


# The order of the concept's sidebar first, then the rest of MIA.
APPS: tuple[App, ...] = (
    App("dashboard", "Home", "🏠", "Your life. In sync.", "index.html"),
    App("greenhouse", "Greenhouse", "🌱", "Grow food. Grow freedom."),
    App("garage", "Garage", "🚗", "Keep it running. Keep it ready.", "garage.html"),
    App("kitchen", "Kitchen", "🍳", "Good food. Good mood.", "kitchen.html"),
    App("household", "Household", "🧺", "A home that runs itself."),
    App("workout", "Workout", "🏋", "Stronger body. Clearer mind.", "workout.html"),
    App("real_estate", "Real Estate", "🏘", "Cash flow. Equity. Freedom.", "real-estate.html"),
    App("missions", "Missions", "🏆", "Explore. Complete. Level up.", "missions.html"),
    App("skills", "Skills", "⚔", "Do the thing. Earn the level. Unlock the next thing.", "skills.html"),
    App("budget", "Money", "💰", "Know where it goes.", "finances.html"),
    App("maintenance", "Maintenance", "🔧", "Everything you own, cared for."),
    App("property", "Property", "🏠", "The house, the appliances, the tools."),
    App("workshop", "Workshop", "🔩", "Parts, jobs and products."),
    App("power", "Power", "🔋", "Energy, tracked."),
    App("character", "Character", "👤", "Your story so far."),
    App("observations", "Observations", "🔍", "What MIA noticed."),
    App("relationships", "People & Pets", "👥", "The ones who matter."),
    App("notes", "Notes", "📝", "Write it down."),
    App("classroom", "Classroom", "🎓", "Keep learning."),
    App("inbox", "Inbox", "📥", "Paperwork, handled."),
    App("expeditions", "Expeditions", "🏕", "Plan the trip."),
    App("memories", "Memories", "📸", "Remember the trip."),
    App("maps", "Maps", "🗺", "Know the ground."),
    App("navigation", "Navigation", "🧭", "Find the way."),
    App("knowledge", "Knowledge", "📚", "The offline library."),
    App("toolbox", "Toolbox", "🧰", "Quick tools."),
    App("lab", "The Lab", "🧪", "Experiments and sensors."),
    App("field_kit", "Field Kit", "🛠", "Devices and scripts."),
    App("files", "Files", "🗂", "Your files."),
    App("music", "Music", "🎵", "Your music."),
    App("assistant", "MIA Assistant", "🗨", "Talk it through."),
    App("settings", "Settings", "⚙", "Make MIA yours."),
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

    if app.module_id == "dashboard":
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


def home(context, now: Optional[datetime] = None) -> dict:
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
