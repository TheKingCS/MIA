"""
core.hourly_earnings
======================

What his work really makes an hour (Jarvis brainstorm round 7, 2026-11-24; his businesses): "what do I really make
an hour?", "is the workshop worth my time?". The jobs, the ledger and the materials read together.

**How.** Each finished job (Complete) with labor hours logged: the revenue entered against it (a sale or a payment
whose job is that job, and a later sale of what it made, by product, when no other job made that product) less what
it used from Materials (core/job_manager.job_material_cost, at the price each was used at, else today's) and the
expenses entered against it (leaving out its "Materials" expenses when it used Materials, so wood isn't counted
twice), over its hours. A job whose product other jobs also made is counted apart: its sales can't be split by job. The jobs are added up (total kept over total hours, so a short lucky job
doesn't count for more than its hours) and the best and worst per hour named. A finished job with hours and no
revenue against it is counted apart and named, never as zero an hour: its sale may simply not be linked to it. His
own quoting rate (`workshop.labor_rate_per_hour`) is said beside it when he set one. A question about his day job's
pay (`DAY_JOB`) is told this is the workshop's, not answered as if it were. Read-only.
"""

from __future__ import annotations

import re

from core.logger import get_logger

log = get_logger(__name__)


# A question about his day job's pay, not the workshop's

DAY_JOB = re.compile(r"\b(at (my|the) job|at work|my job|wages?|paycheck|salary|after tax(es)?|shift)\b", re.I)


def per_job(context) -> tuple[list[dict], list[str]]:
    """The finished jobs with hours: ([{name, hours, revenue, materials, expenses, kept, per_hour}] for those with
    revenue against them, best per hour first], [names of those with none, or whose product other jobs made too]).
    ([], []) without jobs or a ledger."""
    from core.job_manager import job_material_cost

    jobs = getattr(context, "jobs", None)
    ledger = getattr(context, "ledger", None)
    if jobs is None or ledger is None:
        return [], []
    materials = getattr(context, "materials", None)
    by_id = {m.material_id: m for m in materials.all_materials()} if materials is not None else {}
    all_jobs = jobs.all_jobs()
    makers: dict = {}  # product: the jobs that made it
    for job in all_jobs:
        for made in job.products_produced or []:
            makers.setdefault(made.product_id, set()).add(job.job_id)
    revenue, mixed = {}, set()
    for r in ledger.all_revenue():
        if r.job_id:
            revenue[r.job_id] = revenue.get(r.job_id, 0.0) + float(r.amount or 0)
        elif r.product_id and r.product_id in makers:  # sold later from stock: the job that made it
            if len(makers[r.product_id]) == 1:
                (one,) = makers[r.product_id]
                revenue[one] = revenue.get(one, 0.0) + float(r.amount or 0)
            else:
                mixed |= makers[r.product_id]
    paid, unlinked = [], []
    for job in all_jobs:
        if job.status != "Complete" or not job.labor_hours or job.labor_hours <= 0:
            continue
        if job.job_id in mixed or not revenue.get(job.job_id):
            unlinked.append(job.name)
            continue
        used = round(job_material_cost(job, by_id), 2)
        costs = sum(float(e.amount or 0) for e in ledger.all_expenses() if e.job_id == job.job_id
                    and not (job.material_consumption and str(e.category).lower() == "materials"))
        kept = round(revenue[job.job_id] - used - costs, 2)
        paid.append({"name": job.name, "hours": float(job.labor_hours), "revenue": round(revenue[job.job_id], 2),
                     "materials": used, "expenses": round(costs, 2), "kept": kept,
                     "per_hour": round(kept / job.labor_hours, 2)})
    return sorted(paid, key=lambda j: -j["per_hour"]), unlinked


def say(context, question: str = "") -> str:
    """His work's real hourly in words: all the paid jobs together, the best and worst, his quoting rate beside it,
    and the finished jobs with no revenue linked; a day-job pay question (`DAY_JOB`) told this is the workshop's."""
    from core.region import money

    if DAY_JOB.search(question or ""):
        return ("I work out the hourly of your workshop and business jobs, not your day job's pay: your job's hours "
                "and pay are on the Dungeon page. Ask \"what do my builds make an hour?\" for the workshop's.")
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
                                                             else "") + ", finished with hours but no sale linked "
                "(or a product other jobs made too).")
    return out + " Overhead (tools, the shop's power) isn't in it unless it was entered against a job."
