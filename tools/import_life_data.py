"""
tools.import_life_data
========================

Import the owner's private life-data pack (data/_import/muse_assets.json, built from their memory, email and
manufacturer schedules) into MIA's Garage — the maintenance assets and their service schedules — through the real
MaintenanceManager so every write is undoable (core/undo_log.py).

Run it only while MIA is NOT running (its live MaintenanceManager would overwrite these on its next save):

    python -m tools.import_life_data            # import into data/ (the real Garage)
    python -m tools.import_life_data --dry-run  # say what it would do, write nothing

It is **idempotent**: assets are matched by name (and any aliases the pack supplies) and updated in place, never
duplicated; a maintenance task is added only when one of that title doesn't already exist for the asset. It never
fabricates a current reading or a service date — hours and odometers stay unknown until the owner logs a real one, which is
exactly why the compound triggers (DEC-0131, hours/miles OR calendar) matter: the annual/7-year side still reminds
him with no reading at all. Provenance (source, confidence, what's still unknown) is written into each asset's notes.

Properties, bills and the person/work model are a separate pass (Real Estate / Budget / User Sync), not this file.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
PACK = ROOT / "data" / "_import" / "muse_assets.json"
YEAR = 365

# muse module -> MaintenanceAsset category
_CATEGORY = {"garage": "Vehicle", "home_appliances": "Appliance", "devices": "Electronics"}


def _amount(text: str, unit_words: tuple[str, ...]) -> Optional[int]:
    """The first integer in `text` that is immediately followed by one of unit_words (e.g. '105,000 mi' -> 105000)."""
    for word in unit_words:
        m = re.search(r"(\d[\d,]*)\s*" + word, text)
        if m:
            return int(m.group(1).replace(",", ""))
    return None


def trigger_for(basis: str, interval: str) -> dict:
    """Pure logic. Map a muse maintenance line (basis + human interval) to add_task kwargs, erring toward a calendar
    reminder + note rather than inventing a precise meter interval. A compound hours/miles-OR-time line becomes one
    meter task with calendar_fallback_days (DEC-0131)."""
    text = interval.lower()
    hours = _amount(text, ("hour", "hr"))
    miles = _amount(text, ("mi", "mile"))
    years = _amount(text, ("year", "yr"))
    annually = "annual" in text or "yearly" in text
    monthly = re.search(r"\bmonth", text) and miles is None
    fallback = (years * YEAR) if years else (YEAR if annually else None)

    if basis in ("hours", "hours_or_time"):
        kw = {"trigger_type": "runtime", "meter_unit": "hours", "meter_interval": hours}
        if basis == "hours_or_time":
            kw["calendar_fallback_days"] = fallback or YEAR
        return kw
    if basis in ("mileage", "mileage_or_time"):
        kw = {"trigger_type": "mileage", "meter_unit": "mi", "meter_interval": miles}
        if basis == "mileage_or_time":
            kw["calendar_fallback_days"] = fallback or YEAR
        return kw
    if basis == "minder":
        if miles:  # a clean mileage figure -> track it by miles
            return {"trigger_type": "mileage", "meter_unit": "mi", "meter_interval": miles,
                    "notes": "Follow the dashboard Maintenance Minder; this mileage is the typical fallback."}
        return {"trigger_type": "calendar", "interval_days": YEAR,
                "notes": "Manufacturer maintenance-minder item — follow the dashboard; yearly as a fallback."}
    if basis in ("time", "time_or_mileage"):
        days = (years * YEAR) if years else (30 if monthly else (YEAR if annually else None))
        kw = {"trigger_type": "calendar", "interval_days": days}
        if basis == "time_or_mileage" and miles:
            kw["notes"] = f"or {miles:,} mi, whichever comes first"
        return kw
    # inspection / practice / season and anything else -> a calendar reminder, carrying the interval words as a note
    days = 30 if (monthly or "month" in text) else YEAR
    return {"trigger_type": "calendar", "interval_days": days, "notes": interval}


def _norm(name: str) -> str:
    """A name flattened for matching."""
    return " ".join((name or "").lower().split())


def _asset_notes(a: dict) -> str:
    """Human-readable provenance + what's still unknown, for the asset's notes field."""
    bits = []
    for k in ("engine", "engine_note", "color", "nickname", "known_issue", "schedule_note", "purchased_note"):
        if a.get(k):
            bits.append(f"{k.replace('_', ' ')}: {a[k]}")
    if a.get("last_service"):
        s = a["last_service"]
        bits.append(f"last service: {s.get('task')} on {s.get('date')} at {s.get('where')} (${s.get('cost_usd')})")
    if a.get("warranty"):
        bits.append(f"warranty: {a['warranty'].get('months')}mo/{a['warranty'].get('hours','-')}h to {a['warranty'].get('until')}")
    unknown = [k for k in ("odometer_mi", "hour_meter", "serial", "watts", "psu_watts", "ram") if k in a and a[k] is None]
    if unknown:
        bits.append("UNKNOWN (ask, don't invent): " + ", ".join(unknown))
    bits.append("Source: Muse life-data pack (email + memory + manufacturer), 2026-11-08.")
    return " | ".join(bits)


def import_life_data(manager, pack: Path = PACK, dry_run: bool = False, owner_profile_id: Optional[str] = None) -> dict:
    """Upsert the pack's assets and their maintenance into `manager`. Returns a summary of what changed."""
    data = json.loads(Path(pack).read_text(encoding="utf-8"))
    # Aliases (a pack asset's name -> an existing record's name) come from the pack, so no real names live in this file.
    aliases = {_norm(k): _norm(v) for k, v in (data.get("aliases") or {}).items()}
    by_name = {_norm(a.name): a for a in manager.all_assets()}
    summary = {"assets_added": [], "assets_updated": [], "tasks_added": [], "skipped_tasks": 0}

    for a in data.get("assets", []):
        target_name = aliases.get(_norm(a["name"]), _norm(a["name"]))
        # Match an existing record by the alias target OR by the pack's own name — so a re-run finds the asset this
        # import itself created last time and updates it, never a duplicate.
        existing = by_name.get(target_name) or by_name.get(_norm(a["name"]))
        category = a.get("category") or _CATEGORY.get(a.get("module", ""), "Other")
        fields = {
            "manufacturer": a.get("make", "") or "",
            "model": a.get("model", "") or "",
            "serial_number": a.get("serial") or "",
            "purchase_price": float(a.get("total_usd") or (a.get("purchased", {}) or {}).get("price_usd") or 0) or 0.0,
            "warranty_until": (a.get("warranty") or {}).get("until", "") or "",
            "notes": _asset_notes(a),
        }
        purchase_date = (a.get("purchased") or {}).get("date") or a.get("purchased_date") or a.get("delivered")
        if purchase_date:
            fields["purchase_date"] = purchase_date
        owner = owner_profile_id if a.get("owner") == "self" else None

        if existing is not None:
            if not dry_run:
                manager.update_asset(existing.asset_id, category=category, owner_profile_id=owner, **fields)
            asset_id = existing.asset_id
            summary["assets_updated"].append(a["name"])
        else:
            if not dry_run:
                created = manager.add_asset(a["name"], category=category, owner_profile_id=owner, **fields)
                asset_id = created.asset_id
            else:
                asset_id = None
            summary["assets_added"].append(a["name"])

        have = {_norm(t.title) for t in (manager.tasks_for_asset(asset_id) if asset_id else [])}
        for m in a.get("maintenance", []):
            title = m["task"]
            if _norm(title) in have or any(_norm(title).startswith(h) or h.startswith(_norm(title)) for h in have):
                summary["skipped_tasks"] += 1
                continue
            kw = trigger_for(m.get("basis", ""), m.get("interval", ""))
            note = " · ".join(x for x in (m.get("interval"), m.get("note"), kw.pop("notes", None)) if x)
            # a timing belt is the standout risk on an old vehicle — flag it high and say to verify, never fabricate a baseline
            priority = "high" if "timing belt" in _norm(title) else "normal"
            if not dry_run and asset_id:
                manager.add_task(asset_id, title, notes=note, priority=priority, **kw)
            summary["tasks_added"].append(f"{a['name']}: {title}")
            have.add(_norm(title))
    return summary


def main(argv: Optional[list] = None) -> int:
    """Import into the real Garage (data/). Refuses nothing, but does nothing destructive; --dry-run writes nothing."""
    args = argv if argv is not None else sys.argv[1:]
    dry = "--dry-run" in args
    from core.app_context import AppContext
    from core.config_manager import ConfigManager
    from core.event_bus import EventBus
    from core.maintenance_manager import MaintenanceManager

    context = AppContext(config=ConfigManager(), events=EventBus())
    manager = MaintenanceManager(context, data_dir=ROOT / "data")
    owner = next((p.name for p in (ROOT / "data" / "profiles").glob("*") if p.is_dir()), None)
    summary = import_life_data(manager, dry_run=dry, owner_profile_id=owner)
    print(("DRY RUN — nothing written\n" if dry else "") + json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
