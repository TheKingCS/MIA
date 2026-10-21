"""
core.web_more
===============

The Journal, Workshop, Expeditions, Music and Files screens on the web
(Zac, 2026-10-16: on the phone they "are empty right now and just bring
up a chat with MIA"). Each assembler reads its stores and returns what
its screen shows; every change is an action in core/more_actions.py.

- `journal_page`: your journal entries (newest first), their tags, and
  how many private (Talk It Out) entries you have; those stay encrypted
  and are read only with your passphrase, never here.
- `workshop_page`: parts, materials (low ones first), products, jobs
  (with what they used and made, and their cost), sales and costs.
- `expeditions_page`: expeditions, each with its trips (status, packing
  list, distance, journal entries).
- `music_page`: the music library and playlists; songs play in the
  browser, streamed from MIA (/api/music/track/<id>/audio).
- `files_page`: the person's own files folder (core/my_files.py).
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)


def _forms() -> dict:
    from core.more_actions import forms

    return forms()


def _when(iso: str) -> str:
    return (iso or "")[:10]


# ------------------------------------------------------------------ journal


def preview(body: str, limit: int = 140) -> str:
    """Pure logic. The first words of an entry, on one line."""
    text = " ".join(str(body or "").split())
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + "…"


def journal_page(context, today: Optional[date] = None) -> dict:
    today = today or date.today()
    journal = getattr(context, "journal", None)
    if journal is None:
        return {"available": False}
    trips = getattr(context, "trips", None)
    trip_names = {t.trip_id: t.name for t in trips.all_trips()} if trips is not None else {}
    entries, tags = [], {}
    for e in sorted(journal.all_entries(), key=lambda e: e.created_at or e.updated_at, reverse=True):
        for tag in e.tags:
            tags[tag] = tags.get(tag, 0) + 1
        entries.append({"id": e.entry_id, "title": e.title, "body": e.body, "preview": preview(e.body),
                        "tags": list(e.tags), "conditions": e.conditions, "date": _when(e.created_at),
                        "updated": _when(e.updated_at), "trip": trip_names.get(e.trip_id or "", ""),
                        "values": {"title": e.title, "body": e.body, "tags": ", ".join(e.tags), "conditions": e.conditions}})
    private = getattr(context, "private_journal", None)
    this_month = today.replace(day=1).isoformat()
    return {
        "available": True, "as_of": today.isoformat(),
        "entries": entries,
        "tags": [{"tag": t, "count": n} for t, n in sorted(tags.items(), key=lambda kv: (-kv[1], kv[0]))],
        "counts": {"entries": len(entries), "this_month": sum(1 for e in entries if e["date"] >= this_month),
                   "tags": len(tags)},
        "private": {"set_up": bool(private and private.is_set_up()),
                    "count": private.entry_count() if private is not None else 0},
        "forms": {"journal": _forms()["journal"]},
    }


# ------------------------------------------------------------------ workshop


def workshop_page(context, today: Optional[date] = None) -> dict:
    from core.region import money

    today = today or date.today()
    stores = {name: getattr(context, name, None) for name in ("components", "materials", "products", "jobs", "ledger")}
    if all(s is None for s in stores.values()):
        return {"available": False}
    parts = [{"id": c.component_id, "name": c.name, "detail": " · ".join(x for x in (c.category, c.value, c.package) if x),
              "quantity": c.quantity, "location": c.location, "empty": c.quantity <= 0,
              "values": {f: getattr(c, f) for f in ("name", "category", "value", "package", "quantity", "location", "notes")}}
             for c in sorted(stores["components"].all_components(), key=lambda c: c.name.lower())] if stores["components"] else []
    materials = []
    if stores["materials"]:
        for m in stores["materials"].all_materials():
            low = m.reorder_threshold > 0 and m.quantity_on_hand <= m.reorder_threshold
            materials.append({"id": m.material_id, "name": m.name, "unit": m.unit, "on_hand": m.quantity_on_hand,
                              "reorder_at": m.reorder_threshold, "low": low, "cost": money(m.unit_cost) if m.unit_cost else "",
                              "supplier": m.supplier, "location": m.location,
                              "values": {f: getattr(m, f) for f in ("name", "unit", "quantity_on_hand", "reorder_threshold",
                                                                     "unit_cost", "supplier", "location", "notes")}})
        materials.sort(key=lambda m: (not m["low"], m["name"].lower()))
    products = [{"id": p.product_id, "name": p.name, "price": money(p.base_price) if p.base_price else "",
                 "stock": p.quantity_in_stock, "description": p.description,
                 "listings": [{"platform": li.platform, "price": money(li.price), "status": li.status} for li in p.listings],
                 "values": {f: getattr(p, f) for f in ("name", "base_price", "quantity_in_stock", "description", "notes")}}
                for p in sorted(stores["products"].all_products(), key=lambda p: p.name.lower())] if stores["products"] else []
    from core.web_craft import craft_section, goods_section

    craft = craft_section(context)
    goods = goods_section(context, today)
    jobs = []
    if stores["jobs"]:
        material_names = {m["id"]: (m["name"], m["unit"]) for m in materials}
        product_names = {p["id"]: p["name"] for p in products}
        order = {"In Progress": 0, "Planned": 1, "Complete": 2, "Cancelled": 3}
        for j in sorted(stores["jobs"].all_jobs(), key=lambda j: (order.get(j.status, 9), j.name.lower())):
            if j.recipe_id:  # a recipe build: shown in Builds (core/web_craft.py)
                continue
            cost = stores["jobs"].total_cost(j.job_id)
            jobs.append({"id": j.job_id, "name": j.name, "status": j.status, "description": j.description,
                         "hours": j.labor_hours, "cost": money(cost) if cost else "",
                         "used": [f"{u.quantity_used:g} {material_names.get(u.material_id, ('a material', ''))[1]} "
                                  f"{material_names.get(u.material_id, ('a material', ''))[0]}".replace("  ", " ")
                                  for u in j.material_consumption],
                         "made": [f"{p.quantity_produced:g} {product_names.get(p.product_id, 'products')}"
                                  for p in j.products_produced],
                         "values": {f: getattr(j, f) for f in ("name", "status", "labor_hours", "description", "notes")}})
    money_rows, totals = [], {"sales": money(0), "costs": money(0), "profit": money(0), "profit_value": 0.0}
    ledger = stores["ledger"]
    if ledger is not None:
        for r in ledger.all_revenue():
            money_rows.append({"id": r.entry_id, "kind": "sale", "amount": money(r.amount), "value": r.amount,
                               "what": r.description or "Sale", "date": r.date})
        for x in ledger.all_expenses():
            money_rows.append({"id": x.entry_id, "kind": "cost", "amount": money(x.amount), "value": -x.amount,
                               "what": x.description or x.category, "category": x.category, "date": x.date})
        money_rows.sort(key=lambda r: r["date"] or "", reverse=True)
        sales, costs = ledger.total_revenue(), ledger.total_expenses()
        totals = {"sales": money(sales), "costs": money(costs), "profit": money(sales - costs), "profit_value": sales - costs}
    return {
        "available": True, "as_of": today.isoformat(),
        "parts": parts, "materials": materials, "products": products, "jobs": jobs,
        "money": money_rows[:60], "totals": totals,
        "counts": {"parts": len(parts), "materials": len(materials), "low": sum(1 for m in materials if m["low"]),
                   "products": len(products), "open_jobs": sum(1 for j in jobs if j["status"] in ("Planned", "In Progress"))
                   + sum(1 for b in craft["builds"] if not b["finished"]), "recipes": len(craft["recipes"]),
                   "goods": round(sum(g["on_hand"] for g in goods["goods"]), 4),
                   "sell_first": sum(g["sell_first"] for g in goods["goods"])},
        "picks": {"materials": [{"id": m["id"], "name": m["name"]} for m in materials],
                  "products": [{"id": p["id"], "name": p["name"]} for p in products]},
        "forms": {**{k: v for k, v in _forms().items() if k in ("component", "material", "product", "job", "sale",
                                                                "shop_expense", "product_sale")}, **craft["forms"]},
        "recipes": craft["recipes"], "builds": craft["builds"], "receipts": craft["receipts"],
        **goods,
    }


# ------------------------------------------------------------------ expeditions


def expeditions_page(context, today: Optional[date] = None) -> dict:
    today = today or date.today()
    expeditions, trips = getattr(context, "expeditions", None), getattr(context, "trips", None)
    if expeditions is None or trips is None:
        return {"available": False}
    journal = getattr(context, "journal", None)
    iso = today.isoformat()

    def trip_card(t) -> dict:
        try:
            distance = trips.total_distance_km(t.trip_id) or trips.planned_route_distance_km(t.trip_id)
        except Exception:
            distance = None
        notes = journal.entries_for_trip(t.trip_id) if journal is not None else []
        return {"id": t.trip_id, "name": t.name, "status": t.status, "activity": t.activity_type,
                "start": t.start_date, "end": t.end_date, "notes": t.notes,
                "gear": [{"index": i, "label": g.label, "packed": g.packed} for i, g in enumerate(t.gear)],
                "packed": sum(1 for g in t.gear if g.packed), "distance_km": round(distance, 1) if distance else None,
                "photos": len(t.photo_filenames), "journal": [{"id": e.entry_id, "title": e.title} for e in notes],
                "values": {"name": t.name, "activity_type": t.activity_type, "start_date": t.start_date,
                           "end_date": t.end_date, "notes": t.notes}}

    cards = []
    for e in expeditions.all_expeditions():
        its = sorted(trips.trips_for_expedition(e.expedition_id), key=lambda t: (t.start_date or "9999", t.name.lower()))
        end = e.end_date or e.start_date
        when = ("now" if (e.start_date and e.start_date <= iso <= (end or e.start_date)) or any(t.status == "active" for t in its)
                else "past" if end and end < iso else "upcoming")
        from core.expedition_media import media

        try:
            gallery = media(context, e.expedition_id)
        except Exception:
            log.exception("Expeditions: media for %s", e.expedition_id)
            gallery = []
        cards.append({"id": e.expedition_id, "name": e.name, "media": gallery, "location": e.location, "start": e.start_date,
                      "end": e.end_date, "notes": e.notes, "when": when,
                      "days_away": (date.fromisoformat(e.start_date) - today).days if e.start_date and when == "upcoming" else None,
                      "trips": [trip_card(t) for t in its],
                      "values": {"name": e.name, "location": e.location, "start_date": e.start_date,
                                 "end_date": e.end_date, "notes": e.notes}})
    # Happening now, then coming up (soonest first), then past (latest first).
    current = sorted((c for c in cards if c["when"] != "past"),
                     key=lambda c: (c["when"] != "now", c["start"] or "9999", c["name"].lower()))
    past = sorted((c for c in cards if c["when"] == "past"), key=lambda c: c["start"] or "", reverse=True)
    cards = current + past
    return {
        "available": True, "as_of": iso, "expeditions": cards,
        "counts": {"upcoming": sum(1 for c in cards if c["when"] == "upcoming"),
                   "now": sum(1 for c in cards if c["when"] == "now"),
                   "trips": sum(len(c["trips"]) for c in cards)},
        "forms": {k: v for k, v in _forms().items() if k in ("expedition", "trip")},
    }


# ------------------------------------------------------------------ music


def duration_text(seconds) -> str:
    """Pure logic. 245 -> "4:05"."""
    if not seconds:
        return ""
    seconds = int(round(float(seconds)))
    return f"{seconds // 3600}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}" if seconds >= 3600 else f"{seconds // 60}:{seconds % 60:02d}"


def music_page(context) -> dict:
    music = getattr(context, "music", None)
    if music is None:
        return {"available": False}
    tracks = [{"id": t.track_id, "title": t.title or "Untitled", "artist": t.artist or "", "album": t.album or "",
               "genre": t.genre or "", "duration": duration_text(t.duration_seconds), "seconds": t.duration_seconds or 0,
               "uploaded": music.uploaded(t)}
              for t in sorted(music.all_tracks(), key=lambda t: ((t.artist or "~").lower(), (t.album or "").lower(),
                                                                t.track_number or 0, (t.title or "").lower()))]
    known = {t["id"] for t in tracks}
    playlists = [{"id": p.playlist_id, "name": p.name, "track_ids": [i for i in p.track_ids if i in known]}
                 for p in sorted(music.all_playlists(), key=lambda p: p.name.lower())]
    artists: dict[str, int] = {}
    for t in tracks:
        artists[t["artist"] or "Unknown artist"] = artists.get(t["artist"] or "Unknown artist", 0) + 1
    try:
        root = music.root_path
        root_text, root_found = str(root), root.exists()
    except Exception:
        root_text, root_found = "", False
    return {"available": True, "tracks": tracks, "playlists": playlists,
            "artists": [{"name": a, "count": n} for a, n in sorted(artists.items(), key=lambda kv: kv[0].lower())],
            "library": {"folder": root_text, "found": root_found, "count": len(tracks),
                        "minutes": round(sum(t["seconds"] for t in tracks) / 60)}}


def track_path(context, track_id: str):
    """The audio file for a library track (it is always a file the library
    scan found, never a path a request names)."""
    from pathlib import Path

    music = getattr(context, "music", None)
    track = music.get_track(track_id) if music is not None else None
    if track is None:
        return None
    path = Path(track.file_path)
    return path if path.is_file() else None


# ------------------------------------------------------------------ files


def files_page(context, folder: str = "") -> dict:
    from core.my_files import MyFiles

    try:
        files = MyFiles.for_context(context)
    except ValueError:
        return {"available": False}
    try:
        listing = files.listing(folder)
    except ValueError:
        listing = files.listing("")
    return {"available": True, **listing}


# ------------------------------------------------------------------ people & pets


def next_birthday(raw: str, today: date):
    """Pure logic. (the next birthday, days until it, age turning or None)."""
    try:
        born = date.fromisoformat(raw)
    except (TypeError, ValueError):
        return None
    for year in (today.year, today.year + 1):
        try:
            day = date(year, born.month, born.day)
        except ValueError:  # Feb 29 outside a leap year: Mar 1
            day = date(year, 3, 1)
        if day >= today:
            age = year - born.year
            return day, (day - today).days, age if 0 < age < 130 else None
    return None


def people_page(context, today: Optional[date] = None) -> dict:
    from core.more_actions import forms

    today = today or date.today()
    store = getattr(context, "relationships", None)
    if store is None:
        return {"available": False}
    people, pets, upcoming = [], [], []
    for p in sorted(store.all_people(), key=lambda p: p.name.lower()):
        nb = next_birthday(p.birthday, today)
        since = None
        if p.last_contact:
            try:
                since = (today - date.fromisoformat(p.last_contact)).days
            except ValueError:
                since = None
        card = {"id": p.person_id, "name": p.name, "relationship": p.relationship, "email": p.email,
                "birthday": p.birthday, "favorites": p.favorite_things, "gifts": p.gift_ideas, "notes": p.notes,
                "last_contact": p.last_contact, "days_since": since,
                "birthday_in": nb[1] if nb else None, "turning": nb[2] if nb else None,
                "values": {f: getattr(p, f) for f in ("name", "relationship", "birthday", "email", "favorite_things",
                                                       "gift_ideas", "notes")}}
        people.append(card)
        if nb and nb[1] <= 60:
            upcoming.append({"kind": "person", "id": p.person_id, "name": p.name, "date": nb[0].isoformat(),
                             "in": nb[1], "turning": nb[2], "gifts": p.gift_ideas})
    for a in sorted(store.all_pets(), key=lambda a: a.name.lower()):
        nb = next_birthday(a.birthday, today)
        pets.append({"id": a.pet_id, "name": a.name, "species": a.species, "birthday": a.birthday,
                     "medical": a.medical_notes, "notes": a.notes, "birthday_in": nb[1] if nb else None,
                     "turning": nb[2] if nb else None,
                     "values": {f: getattr(a, f) for f in ("name", "species", "birthday", "medical_notes", "notes")}})
        if nb and nb[1] <= 60:
            upcoming.append({"kind": "pet", "id": a.pet_id, "name": a.name, "date": nb[0].isoformat(),
                             "in": nb[1], "turning": nb[2], "gifts": ""})
    upcoming.sort(key=lambda u: u["in"])
    f = forms()
    return {"available": True, "as_of": today.isoformat(), "people": people, "pets": pets, "upcoming": upcoming,
            "counts": {"people": len(people), "pets": len(pets), "birthdays": len(upcoming)},
            "forms": {"person": f["person"], "pet": f["pet"]}}
