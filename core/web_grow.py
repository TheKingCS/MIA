"""
core.web_grow
===============

The Grow Lab screen (DEC-0030 phase D): what's growing, each place's
latest readings against your ranges (only ever a warning), experiments
side by side, and harvest totals by crop. From core/grow_lab.py and the
Data Logger; the web only formats. Money (a batch's cost) is never shown
to a child.
"""

from __future__ import annotations

from datetime import date
from typing import Optional


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

    def batch_card(b) -> dict:
        f = batch_figures(b, today)
        return {"id": b.batch_id, "crop": b.crop, "variety": b.variety, "system": b.system, "method": b.method,
                "planted": b.planted, "count": b.count, "status": b.status, "lost": b.lost, "loss_note": b.loss_note,
                "cost": "" if child or not b.cost else money(b.cost), "harvests": list(reversed(b.harvests))[:5],
                "figures": f, "notes": b.notes,
                "values": {fld.name: getattr(b, fld.name) for fld in BATCH.fields if not (child and fld.name == "cost")}}

    batches = [batch_card(b) for b in sorted(lab.batches, key=lambda b: (b.status != "Growing", b.planted or ""), reverse=False)]

    systems, alerts = [], []
    for name in lab.systems:
        rows = []
        for measure, (label, unit) in MEASURES.items():
            readings = logger.readings_for(series_id(name, measure)) if logger is not None else []
            low, high, mine = lab.range_for(name, measure)
            last = readings[-1] if readings else None
            side = check_range(last.value, low, high) if last is not None else ""
            if last is None and not mine:
                continue
            row = {"measure": measure, "label": label, "unit": unit, "low": low, "high": high, "mine": mine,
                   "value": last.value if last is not None else None, "when": last.timestamp[:10] if last is not None else "",
                   "side": side, "trend": [r.value for r in readings[-12:]]}
            rows.append(row)
            if side:
                alerts.append({"system": name, "label": label, "value": last.value, "unit": unit, "side": side,
                               "low": low, "high": high, "mine": mine})
        systems.append({"name": name, "readings": rows,
                        "growing": sum(1 for b in lab.batches if b.system.lower() == name.lower() and b.status == "Growing")})

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
    return {"available": True, "as_of": today.isoformat(), "batches": batches, "systems": systems, "alerts": alerts,
            "experiments": experiments, "harvests": harvests,
            "measures": [{"id": k, "label": v[0], "unit": v[1]} for k, v in MEASURES.items()],
            "counts": {"growing": sum(1 for b in batches if b["status"] == "Growing"), "alerts": len(alerts),
                       "experiments": sum(1 for e in experiments if e["status"] == "Running")},
            "picks": {"batches": [{"id": b["id"], "name": b["crop"] + (" (" + b["variety"] + ")" if b["variety"] else "")
                                   + (" · " + b["system"] if b["system"] else "")} for b in batches]},
            "forms": {"batch": batch_form, "experiment": record_form(EXPERIMENT)}}
