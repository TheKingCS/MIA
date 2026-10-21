"""
core.web_grow
===============

The Greenhouse's growing side (DEC-0030 phase D, folded into the
Greenhouse by Zac 2026-10-17): every **place** (each tank or bed is a
Greenhouse asset; older places are names typed before that) with what's
growing there, its latest readings against your ranges (only ever a
warning), and what it has yielded; plus experiments and harvest totals.
From core/grow_lab.py, the Data Logger and Maintenance; the web only
formats. Money (a batch's cost) is never shown to a child.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

GREENHOUSE_CATEGORIES = ("Garden/Plant",)


def grow_page(context, today: Optional[date] = None) -> dict:
    from core.child_accounts import is_child
    from core.grow_actions import BATCH, EXPERIMENT
    from core.grow_lab import MEASURES, batch_figures, check_range, series_id
    from core.record_actions import record_form
    from core.region import money

    lab = getattr(context, "grow_lab", None)
    if lab is None:
        return {"available": False}
    today = today or date.today()
    child = is_child(context)
    logger = getattr(context, "data_logger", None)
    maintenance = getattr(context, "maintenance", None)

    # The places: Greenhouse assets first, then names typed before places were assets.
    assets = [a for a in maintenance.all_assets() if a.category in GREENHOUSE_CATEGORIES] if maintenance is not None else []
    places = [{"id": a.asset_id, "name": a.name, "asset": True} for a in sorted(assets, key=lambda a: a.name.lower())]
    taken = {p["name"].lower() for p in places}
    places += [{"id": s, "name": s, "asset": False} for s in lab.systems if s.lower() not in taken]
    by_name = {p["name"].lower(): p["id"] for p in places}

    def place_of(b) -> str:
        return b.asset_id or by_name.get((b.system or "").lower(), b.system)

    def batch_card(b) -> dict:
        f = batch_figures(b, today)
        values = {fld.name: getattr(b, fld.name) for fld in BATCH.fields if not (child and fld.name == "cost")}
        values["asset_id"] = place_of(b)
        return {"id": b.batch_id, "crop": b.crop, "variety": b.variety, "place": place_of(b),
                "system": lab.place_name(b.asset_id or b.system), "method": b.method, "planted": b.planted,
                "count": b.count, "status": b.status, "lost": b.lost, "loss_note": b.loss_note,
                "cost": "" if child or not b.cost else money(b.cost), "harvests": list(reversed(b.harvests))[:5],
                "figures": f, "notes": b.notes, "values": values}

    batches = [batch_card(b) for b in sorted(lab.batches, key=lambda b: (b.status != "Growing", b.planted or ""))]

    systems, alerts, summary = [], [], {}
    typed = {s.lower() for s in lab.systems}
    for place in places:
        key, name = place["id"], place["name"]
        # A tank typed by name before it was an asset keeps its readings and range.
        keys = [key] + ([name] if place["asset"] and name.lower() in typed else [])
        rows = []
        for measure, (label, unit) in MEASURES.items():
            readings = sorted((r for k in keys for r in (logger.readings_for(series_id(k, measure)) if logger is not None else [])),
                              key=lambda r: r.timestamp)
            low, high, mine = lab.range_for(key, measure)
            if not mine and len(keys) > 1:
                low, high, mine = lab.range_for(keys[1], measure)
            last = readings[-1] if readings else None
            side = check_range(last.value, low, high) if last is not None else ""
            if last is None and not mine:
                continue
            rows.append({"measure": measure, "label": label, "unit": unit, "low": low, "high": high, "mine": mine,
                         "value": last.value if last is not None else None, "when": last.timestamp[:10] if last is not None else "",
                         "side": side, "trend": [r.value for r in readings[-12:]]})
            if side:
                alerts.append({"place": key, "system": name, "label": label, "value": last.value, "unit": unit,
                               "side": side, "low": low, "high": high, "mine": mine, "when": last.timestamp[:10]})
        here = [b for b in batches if b["place"] == key]
        yields: dict[str, float] = {}
        for b in here:
            for unit, amount in b["figures"]["yield"].items():
                yields[unit] = round(yields.get(unit, 0.0) + amount, 3)
        card = {"id": key, "name": name, "asset": place["asset"], "readings": rows,
                "growing": sum(1 for b in here if b["status"] == "Growing"),
                "batches": [b["id"] for b in here], "out_of_range": sum(1 for r in rows if r["side"]),
                "yield": [{"amount": a, "unit": u} for u, a in sorted(yields.items(), key=lambda kv: -kv[1])]}
        systems.append(card)
        summary[key] = card

    experiments = []
    for e in lab.experiments:
        rows = [batch_card(b) for i in e.batch_ids if (b := lab.get_batch(i)) is not None]
        experiments.append({"id": e.experiment_id, "question": e.question, "status": e.status, "conclusion": e.conclusion,
                            "batches": rows, "values": {f.name: getattr(e, f.name) for f in EXPERIMENT.fields}})

    totals: dict[tuple[str, str], float] = {}
    for b in lab.batches:
        for h in b.harvests:
            k = (b.crop, h.get("unit") or "")
            totals[k] = round(totals.get(k, 0.0) + float(h.get("amount") or 0), 3)
    harvests = [{"crop": c, "unit": u, "amount": a} for (c, u), a in sorted(totals.items(), key=lambda kv: -kv[1])]

    batch_form = record_form(BATCH)
    if child:
        batch_form["fields"] = [f for f in batch_form["fields"] if f["name"] != "cost"]
    return {"available": True, "as_of": today.isoformat(), "batches": batches, "systems": systems, "places": summary,
            "alerts": alerts, "experiments": experiments, "harvests": harvests,
            "measures": [{"id": k, "label": v[0], "unit": v[1]} for k, v in MEASURES.items()],
            "counts": {"growing": sum(1 for b in batches if b["status"] == "Growing"), "alerts": len(alerts),
                       "experiments": sum(1 for e in experiments if e["status"] == "Running"), "places": len(places)},
            # DEC-0037: a harvest can go into goods on hand (never offered to a child: it's selling).
            "goods": [] if child or getattr(context, "craft_recipes", None) is None else
            [{"id": r.recipe_id, "name": r.name + (f" ({r.makes_unit})" if r.makes_unit else "")}
             for r in context.craft_recipes.all_recipes()],
            "picks": {"places": [{"id": p["id"], "name": p["name"]} for p in places],
                      "batches": [{"id": b["id"], "name": b["crop"] + (" (" + b["variety"] + ")" if b["variety"] else "")
                                   + (" · " + b["system"] if b["system"] else "")} for b in batches]},
            "forms": {"batch": batch_form, "experiment": record_form(EXPERIMENT)}}
