"""
core.hourly_earnings
======================

What his work really makes an hour (Jarvis brainstorm round 7, 2026-11-24; his businesses): "what do I really make
an hour?", "is the workshop worth my time?". The jobs, the ledger and the materials read together.

**How.** Each finished job (Complete) with labor hours logged: the revenue entered against it (a sale or a payment
whose job is that job) less what it used from Materials (core/job_manager.job_material_cost) and the expenses
entered against it, over its hours. The jobs are added up (total kept over total hours, so a short lucky job
doesn't count for more than its hours) and the best and worst per hour named. A finished job with hours and no
revenue against it is counted apart and named, never as zero an hour: its sale may simply not be linked to it. His
own quoting rate (`workshop.labor_rate_per_hour`) is said beside it when he set one. Read-only; nothing is estimated.
"""

from __future__ import annotations

from core.logger import get_logger

log = get_logger(__name__)


def per_job(context) -> tuple[list[dict], list[str]]:
    """The finished jobs with hours: ([{name, hours, revenue, materials, expenses, kept, per_hour}] for those with
    revenue against them, best per hour first], [names of those with none]). ([], []) without jobs or a ledger."""
    from core.job_manager import job_material_cost

    jobs = getattr(context, "jobs", None)
    ledger = getattr(context, "ledger", None)
    if jobs is None or ledger is None:
        return [], []
    materials = getattr(context, "materials", None)
    by_id = {m.material_id: m for m in materials.all_materials()} if materials is not None else {}
    revenue, spent = {}, {}
    for r in ledger.all_revenue():
        if r.job_id:
            revenue[r.job_id] = revenue.get(r.job_id, 0.0) + float(r.amount or 0)
    for e in ledger.all_expenses():
        if e.job_id:
            spent[e.job_id] = spent.get(e.job_id, 0.0) + float(e.amount or 0)
    paid, unlinked = [], []
    for job in jobs.all_jobs():
        if job.status != "Complete" or not job.labor_hours or job.labor_hours <= 0:
            continue
        if not revenue.get(job.job_id):
            unlinked.append(job.name)
            continue
        used = round(job_material_cost(job, by_id), 2)
        kept = round(revenue[job.job_id] - used - spent.get(job.job_id, 0.0), 2)
        paid.append({"name": job.name, "hours": float(job.labor_hours), "revenue": round(revenue[job.job_id], 2),
                     "materials": used, "expenses": round(spent.get(job.job_id, 0.0), 2), "kept": kept,
                     "per_hour": round(kept / job.labor_hours, 2)})
    return sorted(paid, key=lambda j: -j["per_hour"]), unlinked


def say(context) -> str:
    """His work's real hourly in words: all the paid jobs together, the best and worst, his quoting rate beside it,
    and the finished jobs with no revenue linked."""
    from core.region import money

    if getattr(context, "jobs", None) is None or getattr(context, "ledger", None) is None:
        return "The Workshop's jobs and ledger aren't on this MIA, so I can't work out your hourly."
    paid, unlinked = per_job(context)
    if not paid:
        out = "No finished job has both its hours and a sale entered against it yet, so there's no real hourly to say."
        if unlinked:
            out += (f" {len(unlinked)} finished job{'s have' if len(unlinked) != 1 else ' has'} hours but no sale "
                    "linked: " + ", ".join(unlinked[:5]) + ". Link the sale to its job and it counts.")
        return out
    hours = sum(j["hours"] for j in paid)
    kept = sum(j["kept"] for j in paid)
    out = (f"Across {len(paid)} finished job{'s' if len(paid) != 1 else ''} you kept {money(kept)} for {hours:g} hours "
           f"after materials and expenses: about {money(kept / hours)} an hour.")
    if len(paid) > 1:
        best, worst = paid[0], paid[-1]
        out += (f" Best: {best['name']}, {money(best['per_hour'])} an hour; lowest: {worst['name']}, "
                f"{money(worst['per_hour'])} an hour.")
    config = getattr(context, "config", None)
    rate = float(config.get("workshop.labor_rate_per_hour", 0) or 0) if config is not None else 0.0
    if rate:
        out += f" You quote {money(rate)} an hour for your labor."
    if unlinked:
        out += (f" Not counted: {', '.join(unlinked[:5])}" + (f" and {len(unlinked) - 5} more" if len(unlinked) > 5
                                                             else "") + ", finished with hours but no sale linked.")
    return out + " Overhead (tools, the shop's power) isn't in it unless it was entered against a job."
