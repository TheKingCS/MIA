"""
core.focus_presets
====================

What each person sees first (2026-10-01, accounts stage 2): MIA has
dozens of apps, and a student, a homesteader and a small-business owner
each need a different handful up front. A **focus** puts the most useful
apps first and tucks the unlikely ones away. It never blocks anything:
a tucked-away app still opens from the Modules screen, Ctrl+K search and
the Assistant, and any app can be shown or hidden one at a time.

Each person's own choice (core/person_settings.py): `apps.focus`,
`apps.featured` (shown first, in order) and `apps.hidden`.

`recommend()` turns the setup questions (gui/onboarding_dialog.py) into
a focus plus a few extra apps. Pure logic: the model isn't involved.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from core import person_settings


@dataclass(frozen=True)
class Focus:
    focus_id: str
    name: str
    description: str
    featured: tuple[str, ...]
    hidden: tuple[str, ...] = ()


# Never tucked away: the way around MIA and back to every app.
ALWAYS_VISIBLE = ("dashboard", "assistant", "settings", "module_browser")

# Rarely useful outside a workshop, field or developer setting.
_SPECIALIST = ("lab", "field_kit", "diagnostics", "power", "expeditions", "navigation", "observations")

FOCUSES: dict[str, Focus] = {f.focus_id: f for f in (
    Focus("personal", "Personal", "Your notes, goals, money and day.",
          ("assistant", "notes", "missions", "budget", "inbox", "memories", "workout", "skills"),
          _SPECIALIST + ("workshop", "real_estate", "property", "garage", "greenhouse")),
    Focus("home_family", "Home & Family", "The household: chores, meals, upkeep, people and bills.",
          ("assistant", "household", "kitchen", "maintenance", "budget", "relationships", "inbox", "notes"),
          _SPECIALIST + ("workshop",)),
    Focus("homestead", "Homestead", "Land, animals, garden, equipment, power and the shop.",
          ("assistant", "property", "greenhouse", "maintenance", "garage", "workshop", "power", "kitchen", "budget",
           "observations"),
          ("diagnostics",)),
    Focus("business", "Business", "Money, documents, jobs, rentals and equipment.",
          ("assistant", "budget", "inbox", "notes", "missions", "real_estate", "workshop", "garage", "maintenance"),
          _SPECIALIST + ("character", "classroom")),
    Focus("student", "Student", "Classes, studying, goals and habits.",
          ("assistant", "classroom", "notes", "missions", "skills", "workout", "budget", "music"),
          _SPECIALIST + ("real_estate", "property", "garage", "workshop", "maintenance")),
)}

DEFAULT_FOCUS = "personal"

# ------------------------------------------------------------------ setup questions

GOALS: tuple[tuple[str, str], ...] = (
    ("home", "Home and family life"),
    ("land", "Land, garden or animals"),
    ("business", "A business or side gig"),
    ("school", "School or studying"),
    ("money", "Money and bills"),
    ("health", "Health and fitness"),
    ("building", "Building and fixing things"),
    ("thinking", "Thinking things through (journal, goals, reasons)"),
)

_GOAL_FOCUS = {"home": "home_family", "land": "homestead", "business": "business", "school": "student"}
_GOAL_APPS = {
    "home": ("household", "kitchen", "maintenance"),
    "land": ("greenhouse", "property"),
    "business": ("budget", "inbox"),
    "school": ("classroom",),
    "money": ("budget",),
    "health": ("workout",),
    "building": ("workshop", "toolbox", "garage"),
    "thinking": ("notes", "missions"),
}
# Skill categories (core/skill_manager.py) each goal points at, for the
# Skills screen's ordering (Profile.interests).
_GOAL_INTERESTS = {
    "home": ("Social",), "land": ("Homestead", "Outdoor"), "school": ("Mind",), "health": ("Body",),
    "building": ("Construction", "Maker"), "thinking": ("Mind",),
}
# When several focuses fit equally, the more specific one wins.
_TIE_ORDER = ("homestead", "business", "student", "home_family", "personal")

SPEAK_UP = (("rarely", "Rarely (2 a day at most)", 2), ("normal", "Now and then (5 a day)", 5),
            ("often", "Often (8 a day)", 8))


@dataclass
class Recommendation:
    focus_id: str
    featured: list[str]
    hidden: list[str]

    @property
    def focus(self) -> Focus:
        return FOCUSES[self.focus_id]


def recommend(goals: Iterable[str]) -> Recommendation:
    """Pure logic. The focus that fits the chosen goals, its apps first,
    then the apps each goal adds. Nothing a goal asks for stays hidden."""
    goals = [g for g in goals if g in dict(GOALS)]
    votes: dict[str, int] = {}
    for goal in goals:
        if goal in _GOAL_FOCUS:
            votes[_GOAL_FOCUS[goal]] = votes.get(_GOAL_FOCUS[goal], 0) + 1
    focus_id = DEFAULT_FOCUS
    if votes:
        best = max(votes.values())
        focus_id = next(f for f in _TIE_ORDER if votes.get(f) == best)
    focus = FOCUSES[focus_id]
    featured = list(focus.featured)
    for goal in goals:
        for app in _GOAL_APPS.get(goal, ()):
            if app not in featured:
                featured.append(app)
    hidden = [app for app in focus.hidden if app not in featured]
    return Recommendation(focus_id, featured, hidden)


def interests_for(goals: Iterable[str], categories: Iterable[str]) -> list[str]:
    """Pure logic. The skill categories the chosen goals point at, among
    the ones that exist."""
    available = list(categories)
    wanted = [c for g in goals for c in _GOAL_INTERESTS.get(g, ())]
    return [c for c in available if c in wanted]


def describe(recommendation: Recommendation, names: dict[str, str]) -> str:
    """Pure logic. What MIA says she'll do with the answers."""
    first = [names[m] for m in recommendation.featured if m in names and m not in ALWAYS_VISIBLE][:6]
    tucked = [names[m] for m in recommendation.hidden if m in names]
    text = f"I'll set you up for {recommendation.focus.name}: {recommendation.focus.description}"
    if first:
        text += f" First on your Apps screen: {', '.join(first)}."
    if tucked:
        still = "it still opens" if len(tucked) == 1 else "they still open"
        text += f" I tucked away {', '.join(tucked)}; {still} from the Modules screen or if you ask me."
    return text + " You can change any of this in Settings, My Apps."


# ------------------------------------------------------------------ arranging the Apps screen


def arrange(modules: list, featured: Iterable[str], hidden: Iterable[str]) -> list:
    """Pure logic. Featured apps first (in that order), then the rest in
    their usual order; hidden ones left out (never ALWAYS_VISIBLE)."""
    by_id = {m.module_id: m for m in modules}
    hidden = {h for h in hidden if h not in ALWAYS_VISIBLE}
    first = [by_id[f] for f in dict.fromkeys(featured) if f in by_id and f not in hidden]
    rest = [m for m in modules if m not in first and m.module_id not in hidden]
    return first + rest


def current(context) -> tuple[Optional[str], list[str], list[str]]:
    """This person's (focus id, featured, hidden); (None, [], []) before
    they've chosen anything, which shows every app as before."""
    return (person_settings.get(context, "apps.focus", None),
            list(person_settings.get(context, "apps.featured", []) or []),
            list(person_settings.get(context, "apps.hidden", []) or []))


def menu_modules(context, modules: list) -> list:
    _focus, featured, hidden = current(context)
    return arrange(modules, featured, hidden)


def hidden_modules(context, modules: list) -> list:
    _focus, _featured, hidden = current(context)
    return [m for m in modules if m.module_id in hidden and m.module_id not in ALWAYS_VISIBLE]


def _changed(context) -> None:
    events = getattr(context, "events", None)
    if events is not None:
        events.publish("apps.arrangement_changed")


def apply(context, recommendation: Recommendation) -> None:
    person_settings.put(context, "apps.focus", recommendation.focus_id)
    person_settings.put(context, "apps.featured", list(recommendation.featured))
    person_settings.put(context, "apps.hidden", list(recommendation.hidden))
    _changed(context)


def apply_focus(context, focus_id: str) -> Optional[Focus]:
    """Switch to a focus, keeping any app this person chose to show."""
    focus = FOCUSES.get(focus_id)
    if focus is None:
        return None
    apply(context, Recommendation(focus.focus_id, list(focus.featured), list(focus.hidden)))
    return focus


def set_app_visible(context, module_id: str, visible: bool) -> bool:
    """Show or tuck away one app. False for one that can't be hidden."""
    if not visible and module_id in ALWAYS_VISIBLE:
        return False
    hidden = [h for h in current(context)[2] if h != module_id]
    if not visible:
        hidden.append(module_id)
    person_settings.put(context, "apps.hidden", hidden)
    _changed(context)
    return True


def find_focus(text: str) -> Optional[Focus]:
    """Pure logic. The focus someone named: 'student', 'home and family',
    'homesteading', 'my business'..."""
    lowered = (text or "").lower()
    words = {
        "student": ("student", "school", "study", "studying", "college", "class"),
        "homestead": ("homestead", "farm", "land", "garden", "ranch"),
        "business": ("business", "work", "company", "side gig", "rental"),
        "home_family": ("home", "family", "household", "house"),
        "personal": ("personal", "just me", "myself", "everything", "default"),
    }
    for focus_id in ("student", "homestead", "business", "home_family", "personal"):
        if any(w in lowered for w in words[focus_id]):
            return FOCUSES[focus_id]
    return None
