"""
core.life_areas
=================

The rest of a life, at a glance: the life state's `areas` section (DEC-0108's
interconnection audit, 2026-11-07). `core/context_assembler.py` has full
sections for money, property, assets, the kitchen, workouts, projects, goals
and missions; the other stores were missing from her picture of a life
entirely. Here each of them gets a small, uniform entry: a few counts and
what's next, read live from its store, never copied or stored.

Each area (`AREAS`) is `{status, source, counts, next}`:
- `status`: REAL (read straight from the store), or PLANNED when the store
  isn't on this MIA. An area that fails to read is logged and left with no
  counts, never breaking the life state.
- `counts`: numbers only (how many, how many open, how many this month).
- `next`: one line about what comes next (the next event, the next
  birthday), or None.

Names appear only where the full sections already show them (an event's
title, a trip's name); a memory's or a journal entry's words never do.
Areas about money (the shop's books, insurance, business, obligations,
business use) are left out for a child account, as `finances` is.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Callable, Optional

from core.logger import get_logger

log = get_logger(__name__)


@dataclass(frozen=True)
class Area:
    """One area of a life: its key in the section, the store it reads, whether it's hidden from a child, and how to
    read it (store, today) -> (counts, next)."""
    key: str
    store: str
    source: str
    read: Callable[[object, date], tuple[dict, Optional[str]]]
    adults_only: bool = False


def _iso(day: date) -> str:
    """A date as YYYY-MM-DD."""
    return day.isoformat()


def _calendar(store, today):
    """Events this week and the next one."""
    week = _iso(today + timedelta(days=7))
    ahead = sorted((e for e in store.all_events() if _iso(today) <= (e.date or "") <= week), key=lambda e: e.date)
    nxt = f"{ahead[0].title} on {ahead[0].date}" if ahead else None
    return {"events": len(store.all_events()), "this_week": len(ahead)}, nxt


def _inventory(store, today):
    """Items kept, and how many have none left."""
    items = store.all_items()
    return {"items": len(items), "out": sum(1 for i in items if (i.quantity or 0) <= 0)}, None


def _components(store, today):
    """Parts kept, and how many are used up."""
    parts = store.all_components()
    return {"parts": len(parts), "out": sum(1 for p in parts if (p.quantity or 0) <= 0)}, None


def _materials(store, today):
    """Materials kept, and how many are at or under their reorder point."""
    found = store.all_materials()
    low = [m for m in found if m.reorder_threshold > 0 and m.quantity_on_hand <= m.reorder_threshold]
    return {"materials": len(found), "low": len(low)}, (f"{low[0].name} is low" if low else None)


def _products(store, today):
    """Products, and how many are in stock."""
    found = store.all_products()
    return {"products": len(found), "in_stock": sum(1 for p in found if (p.quantity_in_stock or 0) > 0)}, None


def _jobs(store, today):
    """Workshop jobs, and how many are open."""
    found = store.all_jobs()
    return {"jobs": len(found), "open": sum(1 for j in found if j.status in ("Planned", "In Progress"))}, None


def _craft(store, today):
    """Workshop recipes."""
    return {"recipes": len(store.all_recipes())}, None


def _ledger(store, today):
    """The shop's sales and costs this month."""
    first = _iso(today.replace(day=1))
    return {"sales_month": round(store.total_revenue(first, _iso(today)), 2),
            "costs_month": round(store.total_expenses(first, _iso(today)), 2)}, None


def _business(store, today):
    """Customers, and orders not yet done."""
    open_orders = [o for o in store.orders if o.status not in ("Delivered", "Cancelled")]
    soonest = min((o for o in open_orders if o.due_date), key=lambda o: o.due_date, default=None)
    return ({"customers": len(store.customers), "open_orders": len(open_orders)},
            f"{soonest.title} due {soonest.due_date}" if soonest else None)


def _insurance(store, today):
    """Policies kept."""
    return {"policies": len(store.policies)}, None


def _obligations(store, today):
    """Obligations, and how many are still open."""
    from core.obligations import CLOSED

    found = store.obligations
    open_ = [o for o in found if o.status not in CLOSED]
    soonest = min((o for o in open_ if o.due_date), key=lambda o: o.due_date, default=None)
    return ({"obligations": len(found), "open": len(open_)},
            f"{soonest.title} due {soonest.due_date}" if soonest else None)


def _flock(store, today):
    """Flocks kept."""
    return {"flocks": len(store.flocks)}, None


def _grow(store, today):
    """Grow-lab batches, and how many are growing."""
    batches = store.batches
    return {"batches": len(batches), "growing": sum(1 for b in batches if b.status == "Growing")}, None


def _homestead(store, today):
    """The greenhouse and its systems, from their latest snapshots: how many systems report, and their critical
    alerts (the export's summary.critical_alert_count; one without it counts none), named as what's next when any are
    open (2026-11-09)."""
    latest = store.all_latest_snapshots()
    alerts = 0
    for snap in latest:
        summary = (snap.data or {}).get("summary") if isinstance(snap.data, dict) else None
        count = summary.get("critical_alert_count") if isinstance(summary, dict) else None
        alerts += count if isinstance(count, (int, float)) and not isinstance(count, bool) else 0
    return ({"systems": len(latest), "critical_alerts": alerts},
            f"{alerts:g} critical alert{'' if alerts == 1 else 's'} at the homestead" if alerts else None)


def _directions(store, today):
    """The standing directions MIA holds, and how many are active (2026-11-09)."""
    found = list(store.directions)
    return {"directions": len(found), "active": sum(1 for d in found if d.active)}, None


def _workplaces(store, today):
    """Workplaces (The Dungeon), the shifts cleared this week, and the next planned shift (2026-11-09)."""
    week = [_iso(today - timedelta(days=n)) for n in range(7)]
    runs = list(store.runs)
    ahead = sorted((r for r in runs if r.status == "planned" and r.date >= _iso(today)), key=lambda r: r.date)
    names = {d.dungeon_id: d.name for d in store.dungeons}
    return ({"workplaces": len(store.dungeons),
             "shifts_this_week": sum(1 for r in runs if r.status == "cleared" and r.date in week)},
            f"{names.get(ahead[0].dungeon_id, 'A shift')} on {ahead[0].date}" if ahead else None)


def _worlds(store, today):
    """Fictional campaigns, and how many are going (2026-11-09)."""
    found = list(store.campaigns)
    return {"campaigns": len(found), "active": sum(1 for c in found if c.status == "active")}, None


def _questlines(store, today):
    """Questlines started and finished, and the one under way (2026-11-09)."""
    started = [q for q in store.quests if q.started_on]
    going = [q for q in started if not q.finished]
    return ({"started": len(started), "finished": len(started) - len(going)},
            f"{going[0].name}, chapter {going[0].current() + 1}" if going else None)


def _art(store, today):
    """Paintings made in the art studio (2026-11-09)."""
    return {"paintings": len(store.items)}, None


def _creations(store, today):
    """Screens and things MIA made for the person, and how many are published (2026-11-09)."""
    items = list(store.items)
    return {"creations": len(items), "published": sum(1 for c in items if c.get("status") == "published")}, None


def _plans(store, today):
    """Build plans kept on the Library's plans shelf (2026-11-09)."""
    return {"plans": len(store.plans)}, None


def _recreation(store, today):
    """Play logged, and how much of it this week (2026-11-09)."""
    week = _iso(today - timedelta(days=6))
    entries = list(store.entries)
    return {"played": len(entries), "this_week": sum(1 for e in entries if week <= str(e.get("date", "")) <= _iso(today))}, None


def _world_map(store, today):
    """Check-ins on the world map, and the squares of it cleared (2026-11-09)."""
    return {"checkins": len(store.checkins), "cleared": len(store.first_seen)}, None


def _bosses(store, today):
    """Boss battles: the bosses defeated (2026-11-09)."""
    return {"defeated": len(store.defeated)}, None


def _fitness(store, today):
    """The fitness plan: its training days in the week (2026-11-09)."""
    training = store.plan.get("training") or {}
    return {"training_days": len(training.get("days") or [])}, None


def _business_use(store, today):
    """Tools and vehicles with business use logged, and the jobs logged this year (2026-11-09)."""
    year = today.year
    assets = store.assets_with_business_use()
    return {"tools": len(assets), "jobs_this_year": sum(len(store.entries_for(a, year)) for a in assets)}, None


def _energy(store, today):
    """Energy sources."""
    return {"sources": len(store.all_energy_sources())}, None


def _expeditions(store, today):
    """Expeditions, and the next one coming up."""
    found = store.all_expeditions()
    ahead = sorted((e for e in found if (e.start_date or "") >= _iso(today)), key=lambda e: e.start_date)
    return ({"expeditions": len(found), "upcoming": len(ahead)},
            f"{ahead[0].name} on {ahead[0].start_date}" if ahead else None)


def _trips(store, today):
    """Trips, and how many are planned or under way."""
    found = store.all_trips()
    return {"trips": len(found), "planned": sum(1 for t in found if t.status == "planned"),
            "active": sum(1 for t in found if t.status == "active")}, None


def _waypoints(store, today):
    """Waypoints kept."""
    return {"waypoints": len(store.all_waypoints())}, None


def _places(store, today):
    """Places she knows."""
    return {"places": len(store.places)}, None


def _tracks(store, today):
    """GPS tracks kept."""
    return {"tracks": len(store.tracks)}, None


def _classroom(store, today):
    """Subjects being studied."""
    return {"subjects": len(store.all_subjects())}, None


def _textbooks(store, today):
    """Textbooks kept."""
    return {"books": len(store.all_books())}, None


def _scripts(store, today):
    """Scripts in the library."""
    return {"scripts": len(store.all_scripts())}, None


def _journal(store, today):
    """Journal entries, and how many this month (never their words)."""
    entries = store.all_entries()
    first = _iso(today.replace(day=1))
    return {"entries": len(entries), "this_month": sum(1 for e in entries if (e.created_at or "")[:10] >= first)}, None


def _memories(store, today):
    """Memories she keeps for the person (never their words)."""
    return {"memories": len(store.all_memories())}, None


def _notes(store, today):
    """Promises, decisions and ideas kept, and how many promises are open."""
    return {"notes": len(store.notes), "open_promises": len(store.of_kind("commitment", open_only=True))}, None


def _rewards(store, today):
    """Rewards in the shop."""
    return {"rewards": len(store.all_rewards())}, None


def _loop(store, today):
    """Rhythms in the normal week."""
    return {"rhythms": sum(1 for r in store.rhythms if r.active)}, None


def _operating(store, today):
    """Lines in the Operating Journal."""
    return {"lines": len(store.lines)}, None


def _paths(store, today):
    """Learning paths started, and the checks passed across them."""
    passed = sum(1 for p in store.paths.values() for a in p.get("attempts", []) if a.get("passed"))
    return {"paths": len(store.paths), "checks_passed": passed}, None


def _record_sets(store, today):
    """Record sets, and the records in them."""
    return {"sets": len(store.sets), "records": sum(len(s.get("records") or []) for s in store.sets)}, None


AREAS: tuple[Area, ...] = (
    Area("calendar", "calendar", "core/calendar_manager.py", _calendar),
    Area("inventory", "inventory", "core/inventory_manager.py", _inventory),
    Area("parts", "components", "core/component_manager.py", _components),
    Area("materials", "materials", "core/material_manager.py", _materials),
    Area("products", "products", "core/product_manager.py", _products),
    Area("workshop_jobs", "jobs", "core/job_manager.py", _jobs),
    Area("workshop_recipes", "craft_recipes", "core/craft_recipes.py", _craft),
    Area("shop_books", "ledger", "core/ledger_manager.py", _ledger, adults_only=True),
    Area("business", "business", "core/business_book.py", _business, adults_only=True),
    Area("insurance", "insurance", "core/insurance.py", _insurance, adults_only=True),
    Area("obligations", "obligations", "core/obligations.py", _obligations, adults_only=True),
    Area("flock", "flock", "core/flock.py", _flock),
    Area("grow_lab", "grow_lab", "core/grow_lab.py", _grow),
    Area("energy", "energy", "core/energy_manager.py", _energy),
    Area("homestead", "homestead", "core/homestead_manager.py", _homestead),
    Area("directions", "direction", "core/direction.py", _directions),
    Area("workplaces", "dungeon", "core/work_dungeon.py", _workplaces),
    Area("worlds", "living_worlds", "core/living_worlds.py", _worlds),
    Area("questlines", "quest_book", "core/questlines.py", _questlines),
    Area("art", "art", "core/art_studio.py", _art),
    Area("creations", "creations", "core/creations.py", _creations),
    Area("plans", "plans", "core/plan_library.py", _plans),
    Area("play", "recreation", "core/recreation.py", _recreation),
    Area("world_map", "world_map", "core/world_map.py", _world_map),
    Area("bosses", "boss_book", "core/boss_battles.py", _bosses),
    Area("fitness", "fitness", "core/fitness_manager.py", _fitness),
    Area("business_use", "business_use", "core/business_use.py", _business_use, adults_only=True),
    Area("expeditions", "expeditions", "core/expedition_manager.py", _expeditions),
    Area("trips", "trips", "core/trip_manager.py", _trips),
    Area("waypoints", "waypoints", "core/waypoint_manager.py", _waypoints),
    Area("places", "places", "core/places.py", _places),
    Area("tracks", "gps_tracks", "core/gps_tracks.py", _tracks),
    Area("classroom", "classroom", "core/classroom_manager.py", _classroom),
    Area("textbooks", "textbooks", "core/textbook_manager.py", _textbooks),
    Area("scripts", "scripts", "core/script_library_manager.py", _scripts),
    Area("journal", "journal", "core/journal_manager.py", _journal),
    Area("memories", "user_memories", "core/user_memory_manager.py", _memories),
    Area("notes", "life_notes", "core/life_notes.py", _notes),
    Area("rewards", "reward_shop", "core/reward_shop.py", _rewards),
    Area("loop", "loop", "core/the_loop.py", _loop),
    Area("operating_journal", "operating_journal", "core/operating_journal.py", _operating),
    Area("learning", "paths", "core/paths.py", _paths),
    Area("record_sets", "record_sets", "core/record_sets.py", _record_sets),
    Area("my_record_sets", "my_record_sets", "core/record_sets.py", _record_sets),
)


def areas(context, today: date, child: bool = False) -> dict:
    """Every area of a life the other sections don't hold, read now: {key: {status, source, counts, next}}. A child
    never gets the money areas; a store that isn't here is PLANNED; one that fails to read is logged and empty."""
    out = {}
    for area in AREAS:
        if child and area.adults_only:
            continue
        store = getattr(context, area.store, None)
        if store is None:
            out[area.key] = {"status": "PLANNED", "source": area.source, "counts": {}, "next": None}
            continue
        try:
            counts, nxt = area.read(store, today)
        except Exception:
            log.exception("The life state's %s area couldn't be read.", area.key)
            counts, nxt = {}, None
        out[area.key] = {"status": "REAL", "source": area.source, "counts": counts, "next": nxt}
    return out
