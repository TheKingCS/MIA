"""
core.web_areas
================

MIA's areas and their hubs (DEC-0129, Zac 2026-11-08; Kitchen added as its
own area by DEC-0130): the sidebar is the Dashboard and then the areas (Home, Garage, Plants and Animals, Health
and Fitness, Recreation, Security, Browser, Settings and Diagnostics,
Finances, Business, Personal, Learning, Missions, Projects,
Communications). Each area has a hub screen (hub.html?area=<id>) with its
apps; an app that belongs to two areas (Calendar, Skills, Real Estate,
Compliance, Workshop, Kitchen's meal plans...) is in both hubs.

- `AREAS`: each area's id, name, icon, line, and its members in order.
  A member is an app's module id (core/web_surfaces.APPS) or a `Page`
  that isn't an app of its own (Projects, My Why, Guitar, Pets...).
- `areas_of(member)` (pure): the areas an app or page is in, for the
  sidebar to open the right one.
- `hub(context, area_id)`: one hub's screen: its apps the person can open,
  each with its line and page.
- `sidebar(context)`: the areas for the frame's sidebar, each with the
  apps and pages in it.

Only how things are found changes here: every app keeps its own page.
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
    """One area: its id, name, icon (from web/icons.js), a line about it, its members in order (app module ids or
    Pages), and its hue (DEC-0130: the portal's frame, light and ambient glow only; never amber or red, which mean
    "needs you" and "error")."""
    id: str
    name: str
    icon: str
    tagline: str
    members: tuple[Union[str, Page], ...]
    hue: str = "#35d4ff"  # Muse's atmosphere values where she set one (H-0093): homestead stays cyan, never green


PROJECTS = Page("projects", "Projects", "workshop", "Plans, budgets and the tasks in them.", "projects.html")
WHY = Page("why", "My Why", "character", "What it's all for.", "why.html")
GUITAR = Page("guitar", "Guitar", "classroom", "A learning path, stage by stage.", "guitar.html")
PETS = Page("pets", "Pets", "relationships", "Your animals, their care and vet visits.", "people.html?only=pets")
PLACES = Page("places", "My Places", "maps", "Places you go, and quests there.", "places.html")
WORLD = Page("worldmap", "World Map", "memories", "Everywhere you've been.", "worldmap.html")
CHECKIN = Page("checkin", "Sunday Check-In", "calendar", "The week, looked back on.", "checkin.html")
PARTY = Page("party", "Party", "missions", "Raids and quests.", "party.html")
CHRONICLE = Page("chronicle", "The Chronicle", "character", "Your story, told back.", "chronicle.html")
WALLET = Page("id_wallet", "ID Wallet", "passwords", "IDs, passports, insurance cards and registrations.", "wallet.html")
SIGNINS = Page("signins", "Sign-Ins", "passwords", "Who signed in, from where.", "signins.html")
CONNECT = Page("connect", "Connect Apps", "settings", "Your accounts, linked.", "connect.html")
STUDIO = Page("studio", "Theme Studio", "settings", "Make MIA look like you: themes, colours, light.", "studio.html")
PROFILE = Page("profile", "Profile", "character", "You, and how MIA knows you.", "profile.html")
YOURDATA = Page("yourdata", "Your Data", "files", "What MIA keeps, and taking it out.", "yourdata.html")
CHANGES = Page("changes", "Recent Changes", "issues", "What changed, with Undo.", "changes.html")
NOTIFS = Page("notifications", "Notifications", "inbox", "What MIA told you.", "notifications.html")
HEALTH = Page("health", "Health", "workout", "Sleep, visits, medications and records.", "health.html")
COMMS = Page("communications", "Communications", "inbox", "Email, MIA's messages and people to reach.",
             "communications.html")
# Maintenance by area (Zac, 2026-10-16: buildings and appliances live in Real Estate, vehicles and tools in Garage):
# the house's upkeep is Real Estate's Home & Appliances tab; vehicles' upkeep is the Garage app itself.
HOME_UPKEEP = Page("upkeep_home", "Home Upkeep", "maintenance", "The house and its appliances, cared for.",
                   "real-estate.html#home")
LABELS = Page("labels", "Labels", "workshop", "Print labels for what you make.", "label.html")
SHOWOFF = Page("showoff", "Show Off", "workshop", "What you've made, to share.", "showoff.html")

AREAS: tuple[Area, ...] = (
    Area("home", "Home", "household", "The house, the kitchen and what keeps it running.",
         ("household", "kitchen", HOME_UPKEEP, "power"), hue="#35d4ff"),
    Area("garage", "Garage", "garage", "Vehicles, tools and the work on them.",
         ("garage", "toolbox", "sight"), hue="#8fa7bf"),
    Area("plants_animals", "Plants and Animals", "greenhouse", "What grows and who you feed.",
         ("greenhouse", "flock", PETS), hue="#35d4ff"),
    Area("kitchen", "Kitchen", "kitchen", "Meals, recipes and the pantry.", ("kitchen",), hue="#e9d4a8"),
    Area("health", "Health and Fitness", "workout", "Training, food and how you feel.", (HEALTH, "workout", "kitchen"), hue="#ff8a3d"),
    Area("recreation", "Recreation", "expeditions", "Trips, maps, music and play.",
         ("expeditions", "maps", "navigation", "memories", WORLD, PLACES, "music", "play"), hue="#9b6bff"),
    Area("security", "Security", "security", "Cameras, passwords and sign-ins.",
         ("security", WALLET, "passwords", SIGNINS, "field_kit"), hue="#c0c8d4"),
    Area("browser", "Browser", "search", "She browses. You approve.", ("browser",), hue="#bfefff"),
    Area("system", "Settings and Diagnostics", "settings", "Make MIA yours, and see how she's doing.",
         ("settings", STUDIO, "diagnostics", "issues", CONNECT, PROFILE, YOURDATA, CHANGES, "module_browser"), hue="#dfe9f2"),
    Area("finances", "Finances", "budget", "Money in, money out, and the way out.",
         ("budget", "freedom", "dungeon", "insurance", "real_estate", "compliance", "inbox"), hue="#3f7bff"),
    Area("business", "Business", "business", "Customers, products and the paperwork.",
         ("business", "workshop", "real_estate", "compliance", LABELS, SHOWOFF), hue="#7f95ff"),
    Area("personal", "Personal", "notes", "Your days, your people, your words.",
         ("calendar", "notes", "life_notes", "operating_journal", "vault", "relationships", WHY, "observations",
          CHECKIN, "files", "good_news"), hue="#ff8ad8"),
    Area("learning", "Learning", "classroom", "Study, the library and skills.",
         ("classroom", "knowledge", GUITAR, "skills"), hue="#6a5cff"),
    Area("missions", "Missions", "missions", "Quests, levels and rewards.",
         ("missions", "skills", "character", "reward_shop", PARTY, CHRONICLE), hue="#c86bff"),
    Area("projects", "Projects", "workshop", "Things you're building.", (PROJECTS, "workshop", "lab"), hue="#b9a8ff"),
    Area("communications", "Communications", "inbox", "Email, MIA's messages and people.",
         (COMMS, "assistant", NOTIFS, "inbox"), hue="#6fc6ff"),
)
AREAS_BY_ID = {a.id: a for a in AREAS}


def member_id(member) -> str:
    """Pure logic. A member's id: the app's module id, or the page's id."""
    return member if isinstance(member, str) else member.id


def areas_of(member: str) -> list[str]:
    """Pure logic. The ids of the areas an app or page is in, in sidebar order."""
    return [a.id for a in AREAS if any(member_id(m) == member for m in a.members)]


def _entries(context, area: Area) -> list[dict]:
    """An area's members the person can open, as {id, name, icon, tagline, page}: apps through the same visibility
    the sidebar uses (a child's or an app without a web page is left out), pages as they are."""
    from core.web_surfaces import APPS_BY_ID, _visible

    out = []
    for m in area.members:
        if isinstance(m, Page):
            out.append({"id": m.id, "name": m.name, "icon": m.icon, "tagline": m.tagline, "page": m.page})
            continue
        app = APPS_BY_ID.get(m)
        if app is None or not app.page or not _visible(context, app):
            continue
        out.append({"id": app.module_id, "name": app.name, "icon": app.icon, "tagline": app.tagline,
                    "page": app.page, "ask": app.ask})
    return out


def sidebar(context) -> list[dict]:
    """The sidebar's areas: [{id, name, icon, page: its hub, members: [...]}], empty areas left out."""
    out = []
    for area in AREAS:
        members = _entries(context, area)
        if members:
            out.append({"id": area.id, "name": area.name, "icon": area.icon, "page": f"hub.html?area={area.id}",
                        "members": members})
    return out


def hub(context, area_id: str) -> Optional[dict]:
    """One area's hub screen: {id, name, icon, tagline, hue, apps, areas, environment: its own space or None}; None for
    an area that doesn't exist."""
    area = AREAS_BY_ID.get(area_id)
    if area is None:
        return None
    from core.web_environments import environment

    return {"id": area.id, "name": area.name, "icon": area.icon, "tagline": area.tagline, "hue": area.hue,
            "apps": _entries(context, area), "areas": [{"id": a.id, "name": a.name} for a in AREAS],
            # DEC-0130 M3: the area's own space (core/web_environments.py), None while it still uses its tiles
            "environment": environment(context, area.id)}
