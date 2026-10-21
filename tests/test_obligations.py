"""Tax and compliance obligations (DEC-0040): deadlines moved off weekends
and holidays, an extension to file never moving the money's date,
reminders once each, unverified never shown as confirmed, repeats."""

from datetime import date

import pytest

from core.obligations import (Obligation, business_day, effective_dates, federal_holidays, next_period,
                              reminder_due, starter_list, state)
from tests.test_crafting import do, shop  # noqa: F401  (the fixture)


def test_holidays_and_business_days():
    h = federal_holidays(2026)
    assert date(2026, 7, 3) in h  # July 4th on a Saturday is observed Friday
    assert date(2026, 11, 26) in h and date(2026, 4, 16) in h  # Thanksgiving; DC Emancipation Day
    assert business_day(date(2026, 4, 15)) == date(2026, 4, 15)
    assert business_day(date(2028, 4, 15)) == date(2028, 4, 18)  # Sat → Mon is Emancipation Day observed → Tue
    assert business_day(date(2027, 1, 15)) == date(2027, 1, 15)
    assert business_day(date(2022, 4, 15)) == date(2022, 4, 18)  # the year the IRS deadline was the 18th
    assert date(2021, 12, 31) in federal_holidays(2021)  # New Year's 2022 on a Saturday


def test_an_extension_to_file_is_not_one_to_pay():
    o = Obligation("x", "Return", kind="tax filing", due_date="2027-04-15", extended_to="2027-10-15")
    d = effective_dates(o)
    assert (d["file"], d["pay"]) == (date(2027, 10, 15), date(2027, 4, 15))
    pay = Obligation("y", "Q3 estimate", kind="tax payment", due_date="2026-09-15")
    assert effective_dates(pay)["pay"] == date(2026, 9, 15) and effective_dates(pay)["file"] is None
    weekend = Obligation("z", "Licence", kind="licence", due_date="2026-08-01", business_days=True)
    assert effective_dates(weekend)["file"] == date(2026, 8, 3) and effective_dates(weekend)["file_moved"]
    as_stated = Obligation("w", "Licence", kind="licence", due_date="2026-08-01", business_days=False)
    assert effective_dates(as_stated)["file"] == date(2026, 8, 1)


def test_where_it_stands_and_reminders_once_each():
    today = date(2026, 10, 21)
    o = Obligation("a", "Q4 estimate", kind="tax payment", due_date="2027-01-15", status="applies",
                   verified_on="2026-10-01")
    s = state(o, today)
    assert (s["where"], s["days"], s["verified"]) == ("later", 86, True)
    assert reminder_due(o, date(2026, 10, 17))[1] == "90 days"
    assert reminder_due(o, date(2026, 10, 18)) is None
    assert reminder_due(o, date(2027, 1, 15))[1] == "today"
    assert reminder_due(o, date(2027, 1, 16))[1] == "overdue" and reminder_due(o, date(2027, 1, 17)) is None
    assert reminder_due(o, date(2027, 1, 23))[1] == "overdue"  # weekly after
    o.status = "paid"
    assert reminder_due(o, date(2027, 1, 15)) is None and state(o, today)["where"] == "closed"
    unchecked = Obligation("b", "Licence", due_date="2026-11-01")
    assert not state(unchecked, today)["verified"]
    stale = Obligation("c", "Permit", due_date="2027-06-01", status="applies", verified_on="2025-01-01")
    assert state(stale, today)["stale"]


def test_repeats_and_starters():
    q = Obligation("q", "Estimate", recurrence="quarterly", due_date="2026-11-30", pay_date="")
    assert next_period(q) == {"due_date": "2027-02-28", "pay_date": ""}
    assert next_period(Obligation("n", "Once")) is None
    every = {s["id"] for s in starter_list("")}
    assert "ky_740" in every and "state_income" in every and "fed_es_q1" in every
    ky = {s["id"] for s in starter_list("ky")}
    assert "ky_740" in ky and "state_income" not in ky
    oh = {s["id"] for s in starter_list("OH")}
    assert "state_income" in oh and "ky_740" not in oh


@pytest.fixture
def book(shop):  # noqa: F811
    from core.obligations import ObligationBook

    shop.obligations = ObligationBook(shop, data_dir=shop.home_dir)
    return shop


def test_the_flow_from_starter_to_paid(book):
    from core.web_compliance import compliance_page

    w = book
    p = do(w, "obligation.starters", s_fed_es_q3="yes", s_ky_home_processor="yes")
    assert p.summary.startswith("Add 2 to check (not confirmed")
    page = compliance_page(w, date(2026, 10, 21))
    assert page["counts"]["unverified"] == 2 and not page["groups"]["later"]  # nothing confirmed by itself
    q3 = next(o for o in w.obligations.obligations if o.starter_id == "fed_es_q3")
    assert q3.due_date == "2027-09-15" or q3.due_date.startswith(str(date.today().year))
    with pytest.raises(Exception, match="already on your list"):
        w.actions.propose(w, "obligation.starters", {"s_fed_es_q3": "yes"})
    p = do(w, "obligation.verify", obligation_id=q3.obligation_id, verified_on="2026-10-20")
    assert "it applies" in p.summary and w.obligations.get(q3.obligation_id).status == "applies"
    w.obligations.update(q3.obligation_id, recurrence="yearly")
    p = do(w, "obligation.status", obligation_id=q3.obligation_id, status="paid", proof="EFTPS 1234")
    assert "then the next one, due" in p.summary
    nxt = [o for o in w.obligations.obligations if o.starter_id == "fed_es_q3" and o.status != "paid"]
    assert len(nxt) == 1 and nxt[0].status == "applies" and nxt[0].proof == ""

    # Not applying is kept with when it was checked; a hand-added one starts unverified.
    home = next(o for o in w.obligations.obligations if o.starter_id == "ky_home_processor")
    do(w, "obligation.verify", obligation_id=home.obligation_id, how="Called the county health department", applies="no")
    assert w.obligations.get(home.obligation_id).status == "not applicable"
    p = w.actions.propose(w, "obligation.add", {"title": "County occupational licence", "kind": "licence",
                                                "due_date": "2027-01-31", "fee": 50})
    w.actions.approve(w, p.proposal_id)
    added = w.obligations.obligations[-1]
    assert added.status == "to verify"
    with pytest.raises(Exception, match="Where did you check it"):
        w.actions.propose(w, "obligation.verify", {"obligation_id": added.obligation_id})


def test_reminders_go_through_the_gate_once_and_the_calendar_shows_deadlines(book):
    from core.calendar_view import calendar_items
    from core.obligations import reminder_notes

    w = book
    w.obligations.add("Sales tax return", kind="tax filing", due_date="2026-11-19", status="applies",
                      verified_on="2026-10-01", fee=0)
    w.obligations.add("Kennel licence", kind="licence", due_date="2026-10-21")
    notes = reminder_notes(w, date(2026, 10, 21))
    titles = [n[0] for n in notes]
    assert titles == ["📌 Due today: Kennel licence"]
    assert "not verified yet" in notes[0][1]
    assert w.obligations.note_given(notes[0][2]) and not w.obligations.note_given(notes[0][2])
    items = calendar_items(w, date(2026, 11, 1), date(2026, 11, 30), date(2026, 10, 21))
    assert [i["title"] for i in items if i["kind"] == "obligation"] == ["Sales tax return"]
