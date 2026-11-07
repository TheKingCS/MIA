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
