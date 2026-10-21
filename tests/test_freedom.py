"""Freedom (DEC-0038): the fund that covers the gap between a month of
living and what the homestead earns, plus the builds; the estimated day;
progress by period; what a shift buys. Every number from the person's own
records, or their own number, and it says which."""

from datetime import date

import pytest

from core.freedom import Inputs, months_back, plan, shift
from tests.test_crafting import do, shop  # noqa: F401  (the fixture)

TODAY = date(2026, 10, 21)


def test_the_plan_math():
    i = Inputs(needs=3000, homestead=500, saved=10000, pace=1000, cushion_months=6, builds_left=8000)
    p = plan(i, TODAY)
    assert (p["gap"], p["cushion"], p["goal"], p["left"]) == (2500, 15000, 23000, 13000)
    assert p["covered"] == round(500 / 3000, 3) and p["progress"] == round(10000 / 23000, 4)
    assert p["months"] == 13.0 and p["days"] == 396 and p["date"] == "2027-11-21"
    save_more, grow_homestead = p["levers"]
    assert save_more["days_sooner"] == 396 - 360  # 13000 / 1100 a month = 11.8 months
    assert grow_homestead["days_sooner"] > save_more["days_sooner"]  # it's saved and it shrinks the gap

    assert plan(Inputs(needs=0), TODAY)["why_no_date"].startswith("Set what a month")
    flat = plan(Inputs(needs=3000, saved=100, pace=0, pace_source="your income minus spending"), TODAY)
    assert flat["date"] is None and "isn't growing" in flat["why_no_date"]
    done = plan(Inputs(needs=3000, homestead=3500, saved=9000, pace=500, builds_left=8000), TODAY)
    assert done["ready"] and done["goal"] == 8000 and done["covered"] == 1.0


def test_a_shift_and_the_months():
    s = shift(22.5, 10, 3044, 23000)
    assert s == {"pay": 225.0, "days_of_living": 2.2, "of_goal": round(225 / 23000, 4), "per_hour": 22.5, "hours": 10}
    assert shift(0, 10, 3000, 1) is None
    assert months_back(TODAY, 3) == [(date(2026, 7, 1), date(2026, 7, 31)), (date(2026, 8, 1), date(2026, 8, 31)),
                                     (date(2026, 9, 1), date(2026, 9, 30))]


def test_the_page_from_real_records(shop):  # noqa: F811
    from core.freedom import freedom_page

    w = shop
    for month in ("2026-07", "2026-08", "2026-09"):
        w.budget.add_income(amount=4000, category="Wages", description="Paycheck", date=f"{month}-15")
        w.budget.add_expense(amount=3000, category="Groceries", description="Living", date=f"{month}-20")
        w.ledger.add_revenue(amount=300, description="Stand", date=f"{month}-10")
        w.ledger.add_expense(100, "Materials", "Flour", date=f"{month}-09")
    w.budget.add_income(amount=200, category="Wages", description="Overtime", date="2026-10-20")
    w.ledger.add_revenue(amount=40, description="Honey", date="2026-10-21")
    greenhouse = w.projects.add_project("Greenhouse")
    w.projects.update_project(greenhouse.project_id, budget=6000)
    w.budget.add_expense(amount=1000, category="Materials", description="Panels", date="2026-09-05",
                         project_id=greenhouse.project_id)
    do(w, "freedom.plan", saved=12000, hourly=20, shift_hours=10)

    page = freedom_page(w, TODAY)
    p = page["plan"]
    assert page["sources"] == {"needs": "your spending, 3-month average", "homestead": "the business's books, 3-month average",
                               "saved": "your number", "pace": "your income minus spending, 3-month average"}
    # Living: 3000 (the greenhouse panels are the builds line, not living); homestead 200; gap 2800 × 6.
    assert (p["gap"], p["cushion"], p["builds_left"]) == (2800, 16800, 5000)
    assert p["goal"] == 21800 and p["left"] == 9800
    assert p["days"] is not None and p["text"]["saved"] == "$12,000.00"
    assert [b["name"] for b in page["builds"]] == ["Greenhouse"] and page["builds"][0]["left"] == 5000
    week = next(x for x in page["periods"] if x["id"] == "week")
    assert (week["saved"], week["homestead"], week["total_text"]) == (200, 40, "+$240.00")
    assert page["shift"]["pay"] == 200 and page["shift"]["days_of_living"] == round(200 / (3000 / 30.44), 1)
    assert [m["label"] for m in page["history"]][-1] == "Sep" and len(page["history"]) == 6

    # Your own number wins; a build added from the screen counts.
    do(w, "freedom.plan", monthly_needs=2500)
    p = do(w, "freedom.build", name="Chicken coop", budget=1500)
    assert p.summary == "Add the build “Chicken coop” to your freedom plan, about $1,500.00"
    page = freedom_page(w, TODAY)
    assert page["sources"]["needs"] == "your number" and page["plan"]["builds_left"] == 6500
    with pytest.raises(Exception, match="Nothing to change"):
        w.actions.propose(w, "freedom.plan", {"monthly_needs": 2500})


def test_bank_cash_counts_checking_and_savings_only(shop):  # noqa: F811
    from core.freedom import bank_cash

    class Snap:
        def __init__(self, accounts):
            self.data = {"accounts": accounts}

    class Finance:
        def all_latest_snapshots(self):
            return [Snap([{"type": "depository", "balances": {"current": 1200.5}},
                          {"type": "credit", "balances": {"current": 900}},
                          {"type": "depository", "balances": {"current": 3000}}])]

    shop.finance = None
    assert bank_cash(shop) is None
    shop.finance = Finance()
    assert bank_cash(shop) == 4200.5
