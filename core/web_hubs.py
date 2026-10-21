"""
core.web_hubs
===============

The destinations that replace the long app list (DEC-0044,
docs/UX_SYSTEM_AUDIT.md): **My Hero's Path**, **World** and **System**.
Each gathers what its apps already know, with a live line per app, so
the person sees their world and goes to an app only for detail. Nothing
new is stored; every number comes from the code its own screen uses.
Presence (core/presence.py) is Home; Conversation is the Assistant.

- `path_page()`: level, the active missions and their next step, skills
  growing this week, recent wins, and the Path's screens.
- `world_page()`: every area of life (the Apps page's groups) with each
  app's live status: what needs you there (from Presence), or its own
  headline (Freedom's days, the eggs today, goods on hand).
- `system_page()`: the model (asked of the runtime), what MIA can do,
  the home computer link, connections, and the advanced screens.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

# The Path's own screens, in the order a person reads them.
PATH_APPS = ("missions", "skills", "character", "reward_shop")
PATH_PAGES = (("chronicle.html", "Chronicle", "📜", "Your story, week by week."),
              ("party.html", "Party", "🤝", "Raids and the household together."),
              ("worldmap.html", "World Map", "🗺", "Where you've been."))
# System's screens (the advanced ones; still reachable from World too).
SYSTEM_PAGES = (("settings.html", "Settings", "⚙", "Make MIA yours."),
                ("apps.html", "Manage Apps", "🧩", "Show, hide and star apps; what MIA can do in each."),
                ("profile.html", "Profile", "👤", "Your account, email and recovery."),
                ("passwords.html", "Passwords", "🔐", "Your vault."),
                ("files.html", "Files", "🗂", "Your files."),
                ("model-test.html", "Model Test", "🧪", "Measure a model on MIA's questions."),
                ("glasses.html", "Glasses", "🕶", "The glasses' screens."))


def _safe(name: str, gather, default):
    try:
        return gather()
    except Exception:
        log.exception("Hubs: %s failed", name)
        return default


# ---------------------------------------------------------------- My Hero's Path


def path_page(context, today: Optional[date] = None) -> dict:
    from core.presence import _missions
    from core.web_progress import level_block, skills_page
    from core.web_surfaces import APPS, _profile, _visible, dashboard

    today = today or date.today()
    _pid, profile = _profile(context)
    skills = _safe("skills", lambda: skills_page(context, today), {})
    rows = skills.get("skills") or []
    growing = sorted((r for r in rows if r.get("this_week")), key=lambda r: -r["this_week"])[:4]
    from core.life_events import WINS

    # Life State's "latest" is every recent event; the Path shows only the wins.
    wins = [e for e in _safe("wins", lambda: dashboard(context).get("wins") or [], []) if e.get("type") in WINS]
    by_id = {a.module_id: a for a in APPS}
    screens = [{"name": by_id[i].name, "icon": by_id[i].icon, "href": by_id[i].page, "line": by_id[i].tagline}
               for i in PATH_APPS if i in by_id and by_id[i].page and _visible(context, by_id[i])]
    screens += [{"name": n, "icon": ic, "href": h, "line": t} for h, n, ic, t in PATH_PAGES]
    return {
        "me": level_block(profile) if profile is not None else None,
        "missions": [i.as_dict() for i in _safe("missions", lambda: _missions(context, today), [])],
        "active_count": _safe("count", lambda: sum(1 for m in context.missions.all_missions() if m.status == "active"), 0)
        if getattr(context, "missions", None) is not None else 0,
        "focus_skill": skills.get("focus"),
        "growing": [{"name": r["name"], "icon": r.get("icon", ""), "level": r["level"], "this_week": r["this_week"]}
                    for r in growing],
        "wins": wins[:5],
        "screens": screens,
    }


# ---------------------------------------------------------------- World


def _headlines(context, today: date) -> dict[str, str]:
    """An app's own one-line status, where it has one worth a glance."""
    out: dict[str, str] = {}

    def freedom():
        from core.freedom import freedom_page

        p = freedom_page(context, today)
        if p.get("available") and p["plan"]["goal"]:
            plan = p["plan"]
            out["freedom"] = (f"About {plan['days']:,} days to go · {plan['progress_pct']:g}% of the fund"
                              if plan["days"] is not None else f"{plan['progress_pct']:g}% of the fund")

    def flock():
        from core.flock import figures

        book = getattr(context, "flock", None)
        if book is not None and book.flocks:
            x = [figures(f, book.entries, today) for f in book.flocks]
            out["flock"] = f"{sum(i['today'] for i in x):g} eggs today · {sum(i['week'] for i in x):g} this week"

    def workshop():
        from core.web_craft import goods_section

        goods = [g for g in goods_section(context, today)["goods"] if g["on_hand"]]
        if goods:
            out["workshop"] = "On hand: " + ", ".join(f"{g['on_hand_text']} {g['name']}" for g in goods[:3])

    def compliance():
        from core.obligations import CLOSED, state

        book = getattr(context, "obligations", None)
        if book is not None and book.obligations:
            states = [state(o, today) for o in book.obligations if o.status not in CLOSED]
            parts = [f"{n} {w}" for n, w in ((sum(s['where'] == 'overdue' for s in states), "overdue"),
                                              (sum(s['where'] == 'upcoming' for s in states), "due in 30 days"),
                                              (sum(not s['verified'] for s in states), "to verify")) if n]
            out["compliance"] = " · ".join(parts) or "Nothing due soon"

    for name, fn in (("freedom", freedom), ("flock", flock), ("workshop", workshop), ("compliance", compliance)):
        _safe(name, fn, None)
    return out


def world_page(context, today: Optional[date] = None) -> dict:
    """Every area of life, each app with what needs you there or its headline."""
    from core.presence import presence
    from core.web_surfaces import apps_page

    today = today or date.today()
    now = _safe("presence", lambda: presence(context, today)["now"], [])
    needs: dict[str, list] = {}
    for item in now:
        needs.setdefault(item["app"], []).append(item)
    heads = _headlines(context, today)
    apps = apps_page(context)
    areas = []
    for group in apps["groups"]:
        cards = []
        for a in group["apps"]:
            if a["id"] in ("web_home", "assistant"):  # Presence and Conversation are places, not apps
                continue
            mine = needs.get(a["id"], [])
            line = (f"{len(mine)} {'thing needs' if len(mine) == 1 else 'things need'} you: {mine[0]['title']}"
                    if mine else heads.get(a["id"], a["tagline"]))
            cards.append({"id": a["id"], "name": a["name"], "icon": a["icon"], "href": a["page"],
                          "on_web": a["on_web"], "line": line, "needs": len(mine), "favorite": a["favorite"],
                          "ask": a["ask"]})
        cards.sort(key=lambda c: (-c["needs"], not c["favorite"], not c["on_web"]))
        areas.append({"name": group["name"], "cards": cards, "needs": sum(c["needs"] for c in cards)})
    return {"as_of": today.isoformat(), "areas": areas, "favorites": apps["favorites"]}


# ---------------------------------------------------------------- System


def system_page(context, today: Optional[date] = None) -> dict:
    from core.capabilities import capability_map

    model = _safe("model", lambda: _model(context), {"line": "Couldn't ask the model right now.", "where": ""})
    caps = _safe("capabilities", lambda: capability_map(context), [])
    registry = getattr(context, "assistant_actions", None)
    llm = getattr(context, "llm", None)
    home = getattr(llm, "home", None) if llm is not None else None
    connections = []
    budget = getattr(context, "budget", None)
    plaid = getattr(context, "plaid", None)
    if plaid is not None:
        connections.append({"name": "Banks (Plaid)", "state": "set up" if _safe("plaid", lambda: plaid.is_configured(), False)
                            else "not set up yet", "href": "money.html"})
    elif budget is not None:
        connections.append({"name": "Banks (Plaid)", "state": "on the home computer", "href": "money.html"})
    connections.append({"name": "Home computer", "state": ("linked: " + (getattr(home, "url", "") or "")) if home is not None
                        else "this is it, or not linked", "href": "settings.html"})
    return {
        "model": model,
        "capabilities": {"apps": sum(1 for c in caps if c["where"] != "retired"),
                         "web": sum(1 for c in caps if c["where"] in ("web", "web and desktop")),
                         "desktop_only": [c["name"] for c in caps if c["where"] == "desktop"],
                         "tools": len(getattr(registry, "_actions", {})) if registry is not None else 0},
        "connections": connections,
        "screens": [{"name": n, "icon": ic, "href": h, "line": t} for h, n, ic, t in SYSTEM_PAGES],
    }


def _model(context) -> dict:
    from core.model_registry import assistant_info, describe

    info = assistant_info(context)
    return {"line": describe(info), "where": info.get("where", ""), "model": (info.get("now") or {}).get("model", "")}
