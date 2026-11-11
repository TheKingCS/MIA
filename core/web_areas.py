"""
core.web_areas
================

MIA's eight destinations, their subdashboards and their hubs (DEC-0153,
Zac 2026-11-11, superseding DEC-0129's fifteen areas): Dashboard, Home,
Garage, Finances, Health + Fitness, AI Tools, Missions and Settings. A
subdashboard is an area with a `parent` (Home's Kitchen, Smart Devices,
Homestead, Recreation, Personal Tools and Learning; Finances' Businesses;
Settings' Security, accounts, data and System). Every app and page has one
owner: it is a member of exactly one area, and other areas reach it through
`shortcuts`, never a copy (`docs/NAVIGATION_ARCHITECTURE.md`).

- `AREAS`: each area's id, name, icon, line, members in order, hue, parent,
  shortcuts and, for the Dashboard, its own page. A member is an app's
  module id (core/web_surfaces.APPS) or a `Page` that isn't an app of its
  own (Projects, My Why, Guitar, Pets...).
- `OLD_IDS`: DEC-0129's area ids that no longer exist, to the area that
  took their place, so an old `hub.html?area=` link still lands.
- `resolve(area_id)` (pure): the area an id (new or old) opens, or None.
- `destinations()` / `children(area_id)` / `top_of(area_id)` (pure): the
  eight, a destination's subdashboards, the destination an area is in.
- `areas_of(member)` (pure): the area that owns an app or page (a list:
  empty or one), for the sidebar to open the right one.
- `hub(context, area_id)`: one hub's screen: its subdashboards and apps the
  person can open, its shortcuts, and the way back up.
- `sidebar(context)`: the eight for the frame's sidebar, each with its
  subdashboards and apps.

Only how things are found changes here: every app keeps its id, page and
store. The Nexus is no longer navigation (it is Living Worlds' screen,
core/web_nexus.py), reached from Living Worlds in Recreation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Union


@dataclass(frozen=True)
class Page:
    """A page in an area that isn't an app in core/web_surfaces.APPS: its id, name, icon, line and web page."""
    id: str
    name: str
    icon: str
    tagline: str
    page: str


@dataclass(frozen=True)
class Area:
    """One destination or subdashboard: its id, name, icon (from web/icons.js), a line about it, the members it owns
    in order (app module ids or Pages), its hue (DEC-0130: frame, light and glow only; never amber or red, which mean
    "needs you" and "error"), its parent destination ("" for one of the eight), shortcuts to members owned elsewhere
    (shown as links, never owned twice), and its own page when it isn't a hub (the Dashboard is index.html)."""
    id: str
    name: str
    icon: str
    tagline: str
    members: tuple[Union[str, Page], ...]
    hue: str = "#35d4ff"  # Muse's atmosphere values where she set one (H-0093): homestead stays cyan, never green
    parent: str = ""
    shortcuts: tuple[str, ...] = ()
    page: str = ""


PROJECTS = Page("projects", "Projects", "workshop", "Plans, budgets and the tasks in them.", "projects.html")
WHY = Page("why", "My Why", "character", "What it's all for.", "why.html")
CONNECTIONS = Page("connections", "Connections", "notes", "What MIA tied together, and what not to raise.", "connections.html")
DIRECTIONS = Page("directions", "My Directions", "character", "What you're steering by.", "directions.html")
GUITAR = Page("guitar", "Guitar", "classroom", "A learning path, stage by stage.", "guitar.html")
PETS = Page("pets", "Pets", "relationships", "Your animals, their care and vet visits.", "people.html?only=pets")
PLACES = Page("places", "My Places", "maps", "Places you go, and quests there.", "places.html")
# DEC-0153: Living Worlds opens the Nexus, the worlds' own screen; the worlds page is reached from it.
WORLDS = Page("worlds", "Living Worlds", "character", "Your worlds, campaigns and character, through the Nexus.",
              "nexus.html")
TRAILS = Page("trails", "Trail Maps", "maps", "Official park and trail map PDFs, offline.", "trails.html")
TRACKS = Page("tracks", "Tracks", "expeditions", "Your walks, rides and drives from GPX files.", "tracks.html")
WORLD = Page("worldmap", "World Map", "memories", "Everywhere you've been.", "worldmap.html")
CHECKIN = Page("checkin", "Sunday Check-In", "calendar", "The week, looked back on.", "checkin.html")
PARTY = Page("party", "Party", "missions", "Raids and quests.", "party.html")
CHRONICLE = Page("chronicle", "The Chronicle", "character", "Your story, told back.", "chronicle.html")
WALLET = Page("id_wallet", "ID Wallet", "passwords", "IDs, passports, insurance cards and registrations.", "wallet.html")
SIGNINS = Page("signins", "Sign-Ins", "passwords", "Who signed in, from where.", "signins.html")
CONNECT = Page("connect", "Connect Apps", "settings", "Your accounts, linked.", "connect.html")
ABOUT = Page("about", "About MIA", "assistant", "What she is, what she's for, what she knows.", "about.html")
ANSWERS = Page("answers", "How MIA Answers", "assistant", "How long, laid out how, the tone: your way.", "answers.html")
STUDIO = Page("studio", "Theme Studio", "settings", "Make MIA look like you: themes, colours, light.", "studio.html")
TRADES = Page("trades", "Trade Master", "workshop", "Any job or diagnosis, walked through step by step.", "trades.html")
LOOKUP = Page("lookup", "Look It Up Online", "search", "Search the web through your own search engine.", "lookup.html")
PORTALS = Page("portals", "Portal Pictures", "apps", "Put your own paintings in the Nexus's portals.", "portals.html")
PROFILE = Page("profile", "Profile", "character", "You, and how MIA knows you.", "profile.html")
YOURDATA = Page("yourdata", "Your Data", "files", "What MIA keeps, and taking it out.", "yourdata.html")
CHANGES = Page("changes", "Recent Changes", "issues", "What changed, with Undo.", "changes.html")
SENSORS = Page("sensors", "Sensors", "lab", "Sensors that send their own readings.", "sensors.html")
NOTIFS = Page("notifications", "Notifications", "inbox", "What MIA told you.", "notifications.html")
HEALTH = Page("health", "Health", "workout", "Sleep, visits, medications and records.", "health.html")
PLAN = Page("plan", "My Plan", "plan", "Goals, the training week and meals.", "plan.html")
COMMS = Page("communications", "Communications", "inbox", "Email, MIA's messages and people to reach.",
             "communications.html")
# Maintenance by area (Zac, 2026-10-16: buildings and appliances live in Real Estate, vehicles and tools in Garage):
# the house's upkeep is Real Estate's Home & Appliances tab; vehicles' upkeep is the Garage app itself.
HOME_UPKEEP = Page("upkeep_home", "Home Upkeep", "maintenance", "The house and its appliances, cared for.",
                   "real-estate.html#home")
LABELS = Page("labels", "Labels", "workshop", "Print labels for what you make.", "label.html")
SHOWOFF = Page("showoff", "Show Off", "workshop", "What you've made, to share.", "showoff.html")
MADE = Page("made", "Made by MIA", "apps", "The screens she builds for you.", "made.html")
SYNC = Page("sync", "Getting To Know You", "profile", "Her questions about you, and your answers.", "sync.html")
COUNCIL = Page("council", "The Council", "assistant", "The agents who build MIA, talking.", "council.html")
DEV = Page("dev", "Development", "workshop", "What's being built, and by whom.", "dev.html")
MODEL = Page("model_test", "Model Check", "model", "How her model does on its test questions.", "model-test.html")

AREAS: tuple[Area, ...] = (
    # ---- the eight destinations (DEC-0153), in Zac's order
    Area("dashboard", "Dashboard", "dashboard", "What's happening, at a glance.", ("good_news", NOTIFS),
         hue="#35d4ff", page="index.html", shortcuts=("missions", "music", "calendar", "changes")),
    Area("home", "Home", "household", "The house, the homestead and everyday life.", ("household", HOME_UPKEEP),
         hue="#35d4ff"),
    Area("garage", "Garage", "garage", "Vehicles, tools and the work on them.", ("garage", "toolbox", TRADES),
         hue="#8fa7bf"),
    Area("finances", "Finances", "budget", "Money in, money out, and the businesses.",
         ("budget", "freedom", "insurance", "compliance"), hue="#3f7bff", shortcuts=("dungeon",)),
    Area("health", "Health and Fitness", "workout", "Training, food and how you feel.", (HEALTH, "workout", PLAN),
         hue="#ff8a3d", shortcuts=("kitchen",)),
    Area("ai_tools", "AI Tools", "assistant", "What MIA does with you: look, browse, read and write.",
         ("sight", "browser", LOOKUP, "inbox", COMMS, "assistant", MADE), hue="#6fc6ff"),
    Area("missions", "Missions", "missions", "Goals, projects, levels and rewards.",
         ("missions", PROJECTS, "dungeon", "skills", "character", "reward_shop", PARTY, CHRONICLE, WHY, DIRECTIONS),
         hue="#c86bff"),
    Area("settings", "Settings", "settings", "Make MIA yours, keep it safe, see how she's doing.",
         ("settings", STUDIO, ANSWERS, ABOUT, "module_browser"), hue="#dfe9f2"),
    # ---- Home's subdashboards
    Area("kitchen", "Kitchen", "kitchen", "Meals, recipes and the pantry.", ("kitchen",), hue="#e9d4a8", parent="home",
         shortcuts=("plan",)),
    Area("smart_devices", "Smart Devices", "power", "Cameras, power, sensors and what's plugged in.",
         ("security", "power", SENSORS, "lab", "field_kit"), hue="#bfefff", parent="home"),
    Area("homestead", "Homestead", "greenhouse", "What grows and who you feed.", ("greenhouse", "flock", PETS),
         hue="#35d4ff", parent="home"),
    Area("recreation", "Recreation", "expeditions", "Music, games, maps, trips and the worlds.",
         ("music", "play", "expeditions", "maps", "navigation", TRAILS, TRACKS, WORLD, PLACES, WORLDS, PORTALS),
         hue="#9b6bff", parent="home"),
    Area("personal_tools", "Personal Tools", "notes", "Your days, your words, your people and what you keep.",
         ("calendar", "notes", "life_notes", "operating_journal", "memories", "vault", "files", "relationships",
          CHECKIN, "observations", CONNECTIONS), hue="#ff8ad8", parent="home"),
    Area("learning", "Learning", "classroom", "Study, the library and what you're learning.",
         ("classroom", "knowledge", GUITAR), hue="#6a5cff", parent="home", shortcuts=("skills",)),
    # ---- Finances' subdashboard
    Area("businesses", "Businesses", "business", "Each business: its money, its work, its customers.",
         ("real_estate", "workshop", "business", LABELS, SHOWOFF), hue="#7f95ff", parent="finances",
         shortcuts=("compliance",)),
    # ---- Settings' subdashboards
    Area("security", "Security", "security", "Passwords, IDs and who signed in.", ("passwords", WALLET, SIGNINS),
         hue="#c0c8d4", parent="settings"),
    Area("accounts", "You and Your Accounts", "profile", "Who you are to MIA, and what's linked.",
         (PROFILE, SYNC, CONNECT), hue="#dfe9f2", parent="settings"),
    Area("your_data", "Your Data", "files", "What MIA keeps, what changed, and taking it out.", (YOURDATA, CHANGES),
         hue="#dfe9f2", parent="settings"),
    Area("system", "System", "diagnostics", "How she's doing, and the team that builds her.",
         ("diagnostics", "issues", COUNCIL, DEV, MODEL), hue="#dfe9f2", parent="settings"),
)
AREAS_BY_ID = {a.id: a for a in AREAS}
# DEC-0129's ids that are gone, to what took their place (bookmarks, saved phone pages, Search, old links).
OLD_IDS = {"plants_animals": "homestead", "personal": "personal_tools", "business": "businesses",
           "projects": "missions", "browser": "ai_tools", "communications": "ai_tools"}


def member_id(member) -> str:
    """Pure logic. A member's id: the app's module id, or the page's id."""
    return member if isinstance(member, str) else member.id


def resolve(area_id: str) -> Optional[Area]:
    """Pure logic. The area an id opens: its own, or the one that took an old id's place; None for neither."""
    return AREAS_BY_ID.get(area_id) or AREAS_BY_ID.get(OLD_IDS.get(area_id or "", ""))


def destinations() -> list[Area]:
    """Pure logic. The eight destinations, in order."""
    return [a for a in AREAS if not a.parent]


def children(area_id: str) -> list[Area]:
    """Pure logic. A destination's subdashboards, in order."""
    return [a for a in AREAS if a.parent == area_id]


def top_of(area_id: str) -> str:
    """Pure logic. The destination an area is in (itself for one of the eight; "" for an unknown id)."""
    area = resolve(area_id)
    return (area.parent or area.id) if area else ""


def areas_of(member: str) -> list[str]:
    """Pure logic. The id of the area that owns an app or page, as a list ([] for none; never more than one,
    tests/test_web_areas.py holds that)."""
    return [a.id for a in AREAS if any(member_id(m) == member for m in a.members)]


def _page(area: Area) -> str:
    """An area's address: its own page (the Dashboard), else its hub."""
    return area.page or f"hub.html?area={area.id}"


def _entries(context, members) -> list[dict]:
    """Members the person can open, as {id, name, icon, tagline, page}: apps through the same visibility the sidebar
    uses (a child's or an app without a web page is left out), pages as they are. A member id that is a page (a
    shortcut) is looked up among every area's pages."""
    from core.web_surfaces import APPS_BY_ID, _visible

    pages = {m.id: m for a in AREAS for m in a.members if isinstance(m, Page)}
    out = []
    for m in members:
        if isinstance(m, str) and m in pages:
            m = pages[m]
        if isinstance(m, Page):
            out.append({"id": m.id, "name": m.name, "icon": m.icon, "tagline": m.tagline, "page": m.page})
            continue
        app = APPS_BY_ID.get(m)
        if app is None or not app.page or not _visible(context, app):
            continue
        out.append({"id": app.module_id, "name": app.name, "icon": app.icon, "tagline": app.tagline,
                    "page": app.page, "ask": app.ask})
    return out


def _sub_entry(area: Area) -> dict:
    """A subdashboard as a tile or a sidebar row."""
    return {"id": area.id, "name": area.name, "icon": area.icon, "tagline": area.tagline, "page": _page(area),
            "sub": True}


def sidebar(context) -> list[dict]:
    """The sidebar's eight: [{id, name, icon, page, members, subs: [{id, name, icon, page, members}]}], each with
    the apps it owns and its subdashboards with theirs; an empty subdashboard is left out, and so is a destination
    with nothing in it."""
    out = []
    for area in destinations():
        subs = []
        for sub in children(area.id):
            members = _entries(context, sub.members)
            if members:
                subs.append({**_sub_entry(sub), "members": members})
        members = _entries(context, area.members)
        if members or subs or area.page:
            out.append({"id": area.id, "name": area.name, "icon": area.icon, "page": _page(area), "members": members,
                        "subs": subs})
    return out


def hub(context, area_id: str) -> Optional[dict]:
    """One hub's screen: {id, name, icon, tagline, hue, apps (its subdashboards first, then what it owns), shortcuts,
    back: {name, page} one level up, areas: the eight, environment: its own space or None}; None for an id that
    isn't an area (old ids open the area that took their place)."""
    area = resolve(area_id)
    if area is None:
        return None
    from core.web_environments import environment

    up = AREAS_BY_ID.get(area.parent)
    back = {"name": up.name, "page": _page(up)} if up else {"name": "Dashboard", "page": "index.html"}
    subs = [_sub_entry(s) for s in children(area.id) if _entries(context, s.members)]
    return {"id": area.id, "name": area.name, "icon": area.icon, "tagline": area.tagline, "hue": area.hue,
            "apps": subs + _entries(context, area.members), "shortcuts": _entries(context, area.shortcuts),
            "back": back, "parent": area.parent,
            "areas": [{"id": a.id, "name": a.name, "page": _page(a)} for a in destinations()],
            # DEC-0130 M3: the area's own space (core/web_environments.py), None while it still uses its tiles
            "environment": environment(context, area.id)}
