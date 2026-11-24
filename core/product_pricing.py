"""
core.product_pricing
======================

Which products are priced below what they take (Jarvis brainstorm round 8, 2026-11-24; his businesses): "which
products should I raise prices on?", "am I charging enough?". The products, the jobs that made them and his own
quoting rate read together.

**How.** For each product with a price: every finished job that produced it, its materials (core/job_manager.
job_material_cost) and labor hours, shared over what the job produced (a job that made two products shares by the
count of each); added up across those jobs and divided by all the pieces made, so a piece's materials and hours are
the average of what they really took. At his quoting rate (`workshop.labor_rate_per_hour`) that's the least a piece
should sell for; a product whose price is under it is named, with the gap and what the price would be at his rate.
Without a rate, the materials and hours a piece are said and he's asked for one. A product no finished job made, or
made with no hours logged, is said as not worked out, never guessed. Read-only.
"""

from __future__ import annotations

from core.logger import get_logger

log = get_logger(__name__)


def per_piece(context) -> dict:
    """{product_id: {pieces, materials, hours, timed}} per piece, from the finished jobs that made each product (a
    job's materials and hours shared by the value of each product it made, price times count, else by count; hours
    averaged over the jobs that logged them). {} without jobs."""
    from core.job_manager import job_material_cost

    jobs = getattr(context, "jobs", None)
    if jobs is None:
        return {}
    materials = getattr(context, "materials", None)
    by_id = {m.material_id: m for m in materials.all_materials()} if materials is not None else {}
    products = getattr(context, "products", None)
    prices = {p.product_id: float(p.base_price or 0) for p in (products.all_products() if products is not None else [])}
    totals: dict = {}
    for job in jobs.all_jobs():
        made = [p for p in (job.products_produced or []) if float(p.quantity_produced or 0) > 0]
        if job.status != "Complete" or not made:
            continue
        # a job that made several products shares by value (price times how many), else by count: a table and ten
        # coasters from one job don't take the same share each
        weight = {p.product_id: float(p.quantity_produced) * max(prices.get(p.product_id, 0.0), 0.0) for p in made}
        if not all(weight.values()):
            weight = {p.product_id: float(p.quantity_produced) for p in made}
        whole = sum(weight.values())
        cost = job_material_cost(job, by_id)
        for p in made:
            share = weight[p.product_id] / whole
            row = totals.setdefault(p.product_id, {"pieces": 0.0, "materials": 0.0, "hours": 0.0, "timed_pieces": 0.0})
            row["pieces"] += float(p.quantity_produced)
            row["materials"] += cost * share
            if job.labor_hours:  # hours averaged over the jobs that logged them
                row["hours"] += float(job.labor_hours) * share
                row["timed_pieces"] += float(p.quantity_produced)
    return {pid: {"pieces": r["pieces"], "materials": round(r["materials"] / r["pieces"], 2),
                  "hours": round(r["hours"] / r["timed_pieces"], 3) if r["timed_pieces"] else 0.0,
                  "timed": bool(r["timed_pieces"])} for pid, r in totals.items()}


def checked(context) -> list[dict]:
    """Each priced product: {name, price, materials, hours, floor (None without a rate), gap, known}, most underpriced
    first; `known` False when no finished, timed job made it."""
    products = getattr(context, "products", None)
    if products is None:
        return []
    config = getattr(context, "config", None)
    rate = float(config.get("workshop.labor_rate_per_hour", 0) or 0) if config is not None else 0.0
    pieces = per_piece(context)
    out = []
    for product in products.all_products():
        if not product.base_price:
            continue
        p = pieces.get(product.product_id)
        known = bool(p and p["timed"])
        floor = round(p["materials"] + p["hours"] * rate, 2) if known and rate else None
        out.append({"name": product.name, "price": float(product.base_price), "known": known,
                    "materials": p["materials"] if p else None, "hours": p["hours"] if p else None, "floor": floor,
                    "gap": round(floor - product.base_price, 2) if floor is not None else None})
    return sorted(out, key=lambda r: -(r["gap"] or -1e9))


def say(context) -> str:
    """The products priced under what they take at his rate, with what they'd be at it; those not worked out."""
    from core.region import money

    if getattr(context, "products", None) is None:
        return "The Workshop's products aren't on this MIA, so I can't check your prices."
    rows = checked(context)
    if not rows:
        return "No product has a price yet, so there's nothing to check."
    config = getattr(context, "config", None)
    rate = float(config.get("workshop.labor_rate_per_hour", 0) or 0) if config is not None else 0.0
    known = [r for r in rows if r["known"]]
    unknown = [r["name"] for r in rows if not r["known"]]
    parts = []
    if not rate:
        parts.append("You haven't set the hourly rate you quote, so I can't say what each should sell for. Set it in "
                     "the Workshop's quotes; meanwhile, a piece takes: " + "; ".join(
                         f"{r['name']} {money(r['materials'])} of materials and {r['hours'] * 60:.0f} minutes"
                         for r in known[:5]) + "." if known else
                     "You haven't set the hourly rate you quote, and no finished job with hours logged made a "
                     "product yet, so there's nothing to work out.")
    else:
        under = [r for r in known if r["gap"] and r["gap"] > 0]
        if under:
            parts.append(f"At your {money(rate)} an hour, these sell for less than their materials and time: " + "; ".join(
                f"{r['name']} at {money(r['price'])}, about {money(r['floor'])} at your rate ({money(r['materials'])} "
                f"materials, {r['hours'] * 60:.0f} minutes)" for r in under[:5]) + ".")
        elif known:
            parts.append(f"Every product with its time logged sells for at least its materials and your "
                         f"{money(rate)} an hour.")
        else:
            parts.append("No finished job with hours logged made a product yet, so there's nothing to compare.")
    if unknown:
        parts.append("Not worked out (no finished job with hours made it): " + ", ".join(unknown[:5])
                     + (f" and {len(unknown) - 5} more" if len(unknown) > 5 else "") + ".")
    return " ".join(parts) + " Your margin and overhead aren't in these: they're the least, not the price."
