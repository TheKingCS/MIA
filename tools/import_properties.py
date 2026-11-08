"""
tools.import_properties
=========================

Import Zac's properties (data/_import/muse_assets.json) into MIA's Real Estate through the real RealEstateManager, so
every write is undoable. Companion to tools/import_life_data.py; run only while MIA is stopped.

    python -m tools.import_properties            # import into data/
    python -m tools.import_properties --dry-run  # say what it would do, write nothing

Idempotent: a property is matched by a normalised name key (an existing record is updated, not duplicated, even if its
street type differs). A shared or unknown loan balance is kept in the notes, never fabricated into a per-property
figure (when one loan covers two properties, neither gets a made-up balance). Source and what's still unknown go in
each property's notes. No real addresses or lenders appear in this file — the portfolio lives only in the private,
git-ignored pack.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
PACK = ROOT / "data" / "_import" / "muse_assets.json"

# muse role -> (property_type, status)
_ROLE = {"home": ("Primary Residence", "Owner Occupied"), "rental": ("Rental", "Rented"),
         "selling": ("Rental", "For Sale")}
# street-type words dropped when deriving a match key, so "12 Oak Rd" and "12 Oak Dr" match
_STREET = {"rd", "road", "dr", "drive", "ln", "lane", "st", "street", "ave", "avenue", "blvd", "ct", "court",
           "way", "pl", "place", "hwy", "cir", "circle", "ct."}


def _key(name: str) -> str:
    """A generic match key for a property name — its first significant word, so the same place matches across a
    re-run and across a street-type difference (Rd vs Dr). No property names are hard-coded here; the real portfolio
    lives only in the private, git-ignored pack."""
    words = [w for w in re.sub(r"[.,]", " ", (name or "").lower()).split()
             if not w.isdigit() and w not in _STREET]
    return words[0] if words else " ".join((name or "").lower().split())


def _notes(p: dict) -> str:
    """Provenance + the loan, electric, tax, rent and sale facts that don't have their own fields."""
    bits = []
    loan = p.get("loan")
    if isinstance(loan, dict):
        bits.append(f"loan: {loan.get('lender')} ${loan.get('monthly_usd')}/mo"
                    + (f" (covers {loan['covers']})" if loan.get("covers") else "") + "; balance TBC")
    elif isinstance(loan, str):
        bits.append(f"loan: {loan}; balance TBC")
    if p.get("mortgage"):
        m = p["mortgage"]
        bits.append(f"mortgage: {m.get('lender')} ${m.get('monthly_usd')}/mo"
                    + (f" — {m['note']}" if m.get("note") else "") + "; balance TBC")
    if p.get("electric"):
        bits.append(f"electric: {p['electric'].get('provider')} acct {p['electric'].get('account')}")
    if p.get("tax_2026"):
        t = p["tax_2026"]
        bits.append(f"2026 tax: ${t.get('discount_usd')} by {t.get('discount_by')} (${t.get('face_usd')} face), "
                    f"parcel {t.get('parcel')}, bill {t.get('bill')}")
    if p.get("buyer"):
        bits.append(f"under contract: {p['buyer']} ${p.get('price_usd'):,} {p.get('terms','')}, "
                    f"P&S {p.get('ps_executed')}, close ~{p.get('closing_outside_date')}")
    bits.append("Source: Muse life-data pack (email + memory), 2026-11-08. Balances/values need refresh before decisions.")
    return " | ".join(b for b in bits if b)


def import_properties(manager, pack: Path = PACK, dry_run: bool = False) -> dict:
    """Upsert the pack's properties into `manager`. Returns a summary."""
    data = json.loads(Path(pack).read_text(encoding="utf-8"))
    by_key = {_key(p.name): p for p in manager.all_properties()}
    summary = {"added": [], "updated": []}

    for p in data.get("properties", []):
        ptype, status = _ROLE.get(p.get("role", ""), ("Rental", ""))
        rent = float(p.get("rent_usd_monthly") or 0) or 0.0
        fields = {"property_type": ptype, "status": status, "monthly_rent": rent,
                  "location": "Murray, KY", "notes": _notes(p)}
        existing = by_key.get(_key(p["name"]))
        if existing is not None:
            if not dry_run:
                manager.update_property(existing.property_id, **fields)
            summary["updated"].append(p["name"])
        else:
            if not dry_run:
                manager.add_property(p["name"], **fields)
            summary["added"].append(p["name"])
    return summary


def main(argv: Optional[list] = None) -> int:
    """Import into data/'s Real Estate. --dry-run writes nothing."""
    args = argv if argv is not None else sys.argv[1:]
    dry = "--dry-run" in args
    from core.app_context import AppContext
    from core.config_manager import ConfigManager
    from core.event_bus import EventBus
    from core.real_estate_manager import RealEstateManager

    context = AppContext(config=ConfigManager(), events=EventBus())
    manager = RealEstateManager(context, data_dir=ROOT / "data")
    summary = import_properties(manager, dry_run=dry)
    print(("DRY RUN — nothing written\n" if dry else "") + json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
